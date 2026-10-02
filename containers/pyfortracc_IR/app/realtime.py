"""
Real-time tracking and forecasting of GOES-19 infrared clusters.

Every cycle downloads the new GOES-19 images with goesgcp, tracks them with
pyfortracc (persist_uid keeps the uids between cycles), exports the GeoJSON
layers of the new time steps and runs the persistence forecast for each new
time stamp. Only the tracking table and the GeoJSON files are kept.

Usage:
    python realtime.py [--config /app/namelist.yaml] [--once]
"""
import argparse
import json
import logging
import os
import pathlib
import shutil
import signal
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import xarray as xr
import yaml

import pyfortracc
from pyfortracc.spatial_conversions import boundaries, trajectories, vectorfield

LOG = logging.getLogger('pyfortracc_ir')
STAMP_FMT = '%Y%m%d_%H%M'
GOES_FMT = '%Y-%m-%d %H:%M:%S'
GEOJSON_LAYERS = {'boundary': boundaries,
                  'trajectory': trajectories,
                  'vector_field': vectorfield}
# Consecutive failed tracking cycles before the pending input files are dropped
MAX_TRACK_FAILURES = 3
# Time stamps of the cycle in progress: left behind when the cycle is
# interrupted (stuck process, docker stop, power loss) and read by recover()
PENDING_FILE = 'track/pending.json'
# Exit code of the watchdog; any exit makes Docker restart the container
EXIT_STUCK = 70


def read_function(path):
    """ Brightness temperature (K) of the goesgcp NetCDF, north at the top. """
    with xr.open_dataset(path) as ds:
        return ds['CMI'].data[::-1]


class RealTime:

    def __init__(self, config_file):
        with open(config_file) as file:
            self.cfg = yaml.safe_load(file)
        self.input_path = _dir(self.cfg['paths']['input'])
        self.output_path = _dir(self.cfg['paths']['output'])
        self.work_path = str(pathlib.Path(self.output_path).parent / 'tmp') + '/'
        for path in (self.input_path, self.output_path, self.work_path):
            pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        dwn = self.cfg['download']
        # File name prefix of the goesgcp files, e.g.
        # OR_ABI-L2-CMIPF-M6C13_G19_s20252711200208_e..._c....nc
        self.prefix = 'OR_{}-{}C{:02d}_G{}_s'.format(dwn['product'],
                                                     dwn['op_mode'],
                                                     int(dwn['channel']),
                                                     dwn['satellite'][-2:])
        self.track_failures = 0
        # Images dropped after repeated tracking failures are not retried
        self.skip_until = None
        # Set by recover(): the next tracking continues the interrupted one
        self.resume_next = False

    # ------------------------------------------------------------------ time
    def file_stamp(self, file):
        name = pathlib.Path(file).name
        if not name.startswith(self.prefix):
            return None
        stamp = name[len(self.prefix):len(self.prefix) + 11]
        try:
            return datetime.strptime(stamp, '%Y%j%H%M')
        except ValueError:
            return None

    def input_files(self):
        files = [(self.file_stamp(f), f)
                 for f in pathlib.Path(self.input_path).glob('*.nc')]
        return sorted((stamp, str(f)) for stamp, f in files if stamp)

    def last_tracked(self):
        """ Last tracked time stamp saved by persist_uid, or None. """
        state_file = self.output_path + 'track/state/state.json'
        if not os.path.isfile(state_file):
            return None
        with open(state_file) as file:
            return pd.Timestamp(json.load(file)['last_stamp']).to_pydatetime()

    def last_processed(self):
        """ Last tracked or dropped time stamp. """
        stamps = [s for s in (self.last_tracked(), self.skip_until) if s]
        return max(stamps) if stamps else None

    # -------------------------------------------------------------- download
    def download(self, last_stamp):
        dwn = self.cfg['download']
        cmd = ['goesgcp',
               '--satellite', dwn['satellite'],
               '--product', dwn['product'],
               '--channel', str(dwn['channel']),
               '--op_mode', dwn['op_mode'],
               '--resolution', str(dwn['resolution']),
               '--lat_min', str(dwn['lat_min']),
               '--lat_max', str(dwn['lat_max']),
               '--lon_min', str(dwn['lon_min']),
               '--lon_max', str(dwn['lon_max']),
               '--processes', str(dwn.get('processes', 4)),
               '--output', self.input_path]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if last_stamp is None:
            cmd += ['--recent', str(dwn.get('bootstrap_files', 6))]
            LOG.info('Download: %s most recent images (no tracking state)',
                     dwn.get('bootstrap_files', 6))
        else:
            start = last_stamp + timedelta(minutes=1)
            oldest = now - timedelta(hours=dwn.get('max_backfill_hours', 3))
            start = max(start, oldest)
            # goesgcp lists the bucket hour folders stepping 1 h from --start
            # while <= --end: with start 13:51 and end 14:18 the 14 h folder is
            # never listed. One more hour at the end covers it; the files are
            # still filtered by their scan time.
            cmd += ['--start', start.strftime(GOES_FMT),
                    '--end', (now + timedelta(hours=1)).strftime(GOES_FMT)]
            LOG.info('Download: images between %s and %s', start, now)
        # goesgcp writes tmp/ and fail.log in the working directory
        result = subprocess.run(cmd, cwd=self.work_path, capture_output=True,
                                text=True)
        if result.returncode != 0:
            # Also returned when no new image is in the bucket yet
            output = (result.stdout + result.stderr).strip().splitlines()
            LOG.info('goesgcp: %s', output[-1] if output else
                     'exit code {}'.format(result.returncode))

    # -------------------------------------------------------------- tracking
    def name_list(self, sample_file):
        """ pyfortracc name_list from the namelist.yaml and the grid. """
        name_list = dict(self.cfg['tracking'])
        # Read by recover(); pyfortracc takes it as an argument of track()
        name_list.pop('resume', None)
        with xr.open_dataset(sample_file) as ds:
            name_list['lon_min'] = float(ds['lon'].min())
            name_list['lon_max'] = float(ds['lon'].max())
            name_list['lat_min'] = float(ds['lat'].min())
            name_list['lat_max'] = float(ds['lat'].max())
            name_list['y_dim'], name_list['x_dim'] = ds['CMI'].shape
        name_list['input_path'] = self.input_path
        name_list['output_path'] = self.output_path
        name_list['timestamp_pattern'] = self.prefix + '%Y%j%H%M'
        name_list['pattern_position'] = [0, len(self.prefix) + 11]
        # Real time: continue uids, lifetimes and events between cycles
        name_list['persist_uid'] = True
        # The forecast moves the cluster pixels saved in the tracking table
        name_list['save_arrays'] = True
        name_list['temp_folder'] = self.work_path
        return name_list

    def track(self, name_list):
        resume, self.resume_next = self.resume_next, False
        if resume:
            # Each stage skips the files already written by the interrupted
            # cycle and the linking continues from its last linked frame
            LOG.info('Resuming the interrupted tracking (resume=True)')
        else:
            # Intermediate files of the previous cycle; the state is kept apart
            shutil.rmtree(self.output_path + 'track/processing/',
                          ignore_errors=True)
        _call(pyfortracc.track, name_list, read_function, resume=resume)

    # -------------------------------------------------------------- recovery
    def pending(self):
        """ Time stamps of the interrupted cycle, or an empty list. """
        try:
            with open(self.output_path + PENDING_FILE) as file:
                return sorted(datetime.strptime(stamp, STAMP_FMT)
                              for stamp in json.load(file)['stamps'])
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def set_pending(self, stamps):
        path = pathlib.Path(self.output_path + PENDING_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(
            {'stamps': [stamp.strftime(STAMP_FMT) for stamp in stamps]}))
        tmp.replace(path)

    def clear_pending(self):
        pathlib.Path(self.output_path + PENDING_FILE).unlink(missing_ok=True)

    def table(self, stamp):
        return (self.output_path + 'track/trackingtable/' +
                stamp.strftime(STAMP_FMT) + '.parquet')

    def recover(self):
        """
        Continue the cycle that was interrupted before the restart
        (tracking.resume). Stopped before the linking saved its state: the
        next tracking runs with resume=True over the files already written.
        Stopped after it: only the concatenation, the GeoJSON and the
        forecasts of those time stamps are missing and are done here.
        """
        stamps = self.pending()
        if not stamps:
            return
        if not self.cfg['tracking'].get('resume', True):
            self.clear_pending()
            return
        last = self.last_tracked()
        if last is None or last < max(stamps):
            LOG.info('Interrupted cycle (%s to %s): the tracking resumes '
                     'after %s', stamps[0], stamps[-1], last)
            self.resume_next = True
            return
        files = self.input_files()
        if not files:
            LOG.warning('Interrupted cycle: no input file left to finish it')
            self.clear_pending()
            return
        LOG.info('Interrupted cycle (%s to %s): already tracked, finishing '
                 'the outputs', stamps[0], stamps[-1])
        name_list = self.name_list(files[-1][1])
        linked = pathlib.Path(self.output_path + 'track/processing/linked/')
        if (not all(os.path.isfile(self.table(stamp)) for stamp in stamps)
                and any(linked.glob('*.parquet'))):
            _call(pyfortracc.track, dict(name_list), read_function,
                  feat_ext=False, spat_ope=False, clst_lnk=False, resume=True)
        self.finish(name_list, stamps)
        self.clear_pending()

    def finish(self, name_list, stamps):
        """ GeoJSON and forecast of the tracked time stamps. """
        stamps = [stamp for stamp in stamps if os.path.isfile(self.table(stamp))]
        if stamps:
            self.export_geojson(name_list, stamps)
            if self.cfg.get('forecast', {}).get('enabled', True):
                for stamp in stamps:
                    self.forecast(name_list, stamp)

    def export_geojson(self, name_list, stamps):
        start, end = min(stamps), max(stamps)
        for layer in self.cfg['output'].get('geojson_layers', ['boundary']):
            if layer not in GEOJSON_LAYERS:
                LOG.warning('Unknown GeoJSON layer %s (use %s)', layer,
                            ', '.join(GEOJSON_LAYERS))
                continue
            try:
                _call(GEOJSON_LAYERS[layer], dict(name_list), start, end,
                      driver='GeoJSON', parallel=False)
            except Exception:
                LOG.exception('GeoJSON %s export failed', layer)

    # -------------------------------------------------------------- forecast
    def forecast(self, name_list, stamp):
        fct = self.cfg.get('forecast', {})
        out_dir = self.output_path + 'forecast/' + stamp.strftime(STAMP_FMT) + '/'
        keep = {'geometry'}
        if fct.get('keep_forecast_table', False):
            keep.add('forecasttable')
        if os.path.isdir(out_dir + 'geometry/'):
            # The working folders are removed at the end: while they exist the
            # forecast was interrupted and is done again
            if all(item.name in keep for item in pathlib.Path(out_dir).iterdir()):
                return
            shutil.rmtree(out_dir, ignore_errors=True)
        fct_list = dict(name_list)
        fct_list['forecast_time'] = stamp.strftime(GOES_FMT)
        fct_list['forecast_mode'] = fct.get('forecast_mode', 'persistence')
        # pyfortracc forecasts at the tracking interval (each frame is built
        # from the previous one): run every interval up to the last lead time
        # and keep only the frames of the forecast steps
        steps, every = forecast_steps(self.cfg)
        delta_time = timedelta(minutes=fct_list['delta_time'])
        fct_list['lead_time'] = steps * every
        fct_list['observation_window'] = int(fct.get('observation_window', 3))
        LOG.info('Forecast %s: %s x %g min', stamp, steps,
                 every * fct_list['delta_time'])
        try:
            _call(pyfortracc.forecast, fct_list, read_function)
        except Exception:
            # E.g. the first frames of a tracking have no displacement yet
            LOG.exception('Forecast %s failed', stamp)
        # Keep only the GeoJSON (and optionally the forecast table)
        if os.path.isdir(out_dir):
            for item in pathlib.Path(out_dir).iterdir():
                if item.name not in keep:
                    shutil.rmtree(item, ignore_errors=True)
            for item in pathlib.Path(out_dir).glob('geometry/*/*'):
                try:
                    lead = datetime.strptime(item.stem, STAMP_FMT) - stamp
                except ValueError:
                    continue
                if lead % (every * delta_time):
                    item.unlink(missing_ok=True)

    # --------------------------------------------------------------- cleanup
    def apply_retention(self):
        """ Remove the inputs and outputs older than the retention hours. """
        ret = self.cfg.get('retention', {})
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        in_hours = float(ret.get('input_hours', 2) or 0)
        if in_hours > 0:
            limit = now - timedelta(hours=in_hours)
            # Images not tracked yet are never removed
            last_stamp = self.last_processed()
            for stamp, file in self.input_files():
                if stamp < limit and last_stamp and stamp <= last_stamp:
                    pathlib.Path(file).unlink(missing_ok=True)
        out_hours = float(ret.get('output_hours', 48) or 0)
        if out_hours > 0:
            limit = now - timedelta(hours=out_hours)
            patterns = ['track/trackingtable/*.parquet', 'track/geometry/*/*',
                        'forecast/*']
            for pattern in patterns:
                for item in pathlib.Path(self.output_path).glob(pattern):
                    try:
                        stamp = datetime.strptime(item.name.split('.')[0],
                                                  STAMP_FMT)
                    except ValueError:
                        continue
                    if stamp < limit:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink(missing_ok=True)

    # ----------------------------------------------------------------- cycle
    def cycle(self):
        """ Run one cycle. Returns True if new time steps were tracked. """
        last_stamp = self.last_processed()
        self.download(last_stamp)
        files = self.input_files()
        new = [(stamp, file) for stamp, file in files
               if last_stamp is None or stamp > last_stamp]
        if not new:
            LOG.info('No new images after %s', last_stamp)
            return False
        LOG.info('Tracking %d new image(s): %s to %s', len(new), new[0][0],
                 new[-1][0])
        name_list = self.name_list(new[-1][1])
        self.set_pending([stamp for stamp, _ in new])
        try:
            self.track(name_list)
        except Exception:
            self.clear_pending()
            self.track_failures += 1
            LOG.exception('Tracking failed (%d/%d)', self.track_failures,
                          MAX_TRACK_FAILURES)
            if self.track_failures >= MAX_TRACK_FAILURES:
                LOG.error('Dropping the pending images after %d failures',
                          self.track_failures)
                for _, file in new:
                    pathlib.Path(file).unlink(missing_ok=True)
                self.skip_until = new[-1][0]
                self.track_failures = 0
            return False
        self.track_failures = 0
        self.finish(name_list, [stamp for stamp, _ in new])
        self.clear_pending()
        LOG.info('Cycle done: last tracked time stamp %s', self.last_tracked())
        return True

    def run(self, once=False):
        sch = self.cfg.get('schedule', {})
        interval = timedelta(minutes=sch.get('interval_minutes', 10))
        offset = timedelta(minutes=sch.get('offset_minutes', 8))
        retry = sch.get('retry_seconds', 120)
        watchdog = Watchdog(float(sch.get('max_cycle_minutes', 45) or 0))
        watchdog.begin()
        try:
            self.recover()
        except Exception:
            LOG.exception('Recovery of the interrupted cycle failed')
            self.resume_next = False
            self.clear_pending()
        while True:
            watchdog.begin()
            try:
                updated = self.cycle()
            except Exception:
                LOG.exception('Cycle failed')
                updated = False
            try:
                self.apply_retention()
            except Exception:
                LOG.exception('Retention cleanup failed')
            watchdog.end()
            if once:
                return
            # Next acquisition slot (e.g. 12:18, 12:28, ...)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            epoch = datetime(1970, 1, 1) + offset
            next_slot = epoch + ((now - epoch) // interval + 1) * interval
            wait = (next_slot - now).total_seconds()
            if not updated:
                wait = min(wait, retry)
            LOG.info('Next cycle in %.0f s', wait)
            time.sleep(wait)


class Watchdog(threading.Thread):
    """
    Ends the process when a cycle takes longer than schedule.max_cycle_minutes
    (0 disables it). A stuck cycle never fails by itself, and Docker only
    restarts a container that exits: the restart policy of the compose file
    brings it back and recover() continues from the last tracked frame.
    """

    def __init__(self, minutes):
        super().__init__(daemon=True)
        self.limit = minutes * 60
        self.started = None
        if self.limit > 0:
            self.start()

    def begin(self):
        self.started = time.monotonic()

    def end(self):
        self.started = None

    def run(self):
        while True:
            time.sleep(15)
            started = self.started
            if started is not None and time.monotonic() - started > self.limit:
                LOG.error('Cycle stuck for more than %g min: exiting, Docker '
                          'restarts the container', self.limit / 60)
                logging.shutdown()
                os._exit(EXIT_STUCK)


def forecast_steps(cfg):
    """
    (forecast steps, tracking intervals in each step) of the namelist: e.g.
    lead_time 6 and step_minutes 30 with delta_time 10 is (6, 3).
    """
    fct = cfg.get('forecast', {})
    delta_time = float(cfg['tracking']['delta_time'])
    step_minutes = float(fct.get('step_minutes') or delta_time)
    every = int(round(step_minutes / delta_time))
    if every < 1 or abs(every * delta_time - step_minutes) > 1e-6:
        raise ValueError('forecast.step_minutes ({:g}) must be a multiple of '
                         'tracking.delta_time ({:g})'.format(step_minutes,
                                                             delta_time))
    return int(fct.get('lead_time', 6)), every


def _stop(main_pid):
    """
    SIGTERM handler. docker stop sends SIGTERM: the main process stops like a
    Ctrl+C. The pool workers of pyfortracc inherit the handler and are ended
    with SIGTERM when each stage finishes: they have to die as usual, a
    KeyboardInterrupt there can leave the queue lock held and the pool waiting
    for ever.
    """
    def handler(signum, frame):
        if os.getpid() != main_pid:
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
            return
        raise KeyboardInterrupt
    return handler


def _call(function, *args, **kwargs):
    """ pyfortracc exits the process on some errors (e.g. empty inputs). """
    try:
        return function(*args, **kwargs)
    except SystemExit as error:
        raise RuntimeError('{} exited ({})'.format(function.__name__,
                                                   error.code)) from None


def _dir(path):
    return str(path).rstrip('/') + '/'


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config',
                        default=os.environ.get('NAMELIST', '/app/namelist.yaml'))
    parser.add_argument('--once', action='store_true',
                        help='Run a single cycle and exit')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    signal.signal(signal.SIGTERM, _stop(os.getpid()))
    try:
        RealTime(args.config).run(once=args.once)
    except KeyboardInterrupt:
        LOG.info('Stopped')


if __name__ == '__main__':
    main()

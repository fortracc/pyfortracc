# pyFortraCC IR — GOES-19 real-time tracking

Container that, every 10 minutes, downloads the GOES-19 channel 13 (IR,
10.3 µm) images with [goesgcp](https://github.com/helvecioneto/goesgcp), tracks
the clusters with [pyfortracc](https://github.com/fortracc/pyfortracc) and
forecasts (persistence) their displacement for each new time stamp.

Default configuration:

| Parameter | Value |
|---|---|
| Thresholds | 235 K and 210 K |
| Minimum cluster size | 100 and 50 pixels |
| Interval | 10 min |
| Domain | lat -35 to 5, lon -80 to -30, 0.045° (~5 km) |
| Forecast | 6 steps of 30 min (3 h), window of 3 images |
| Retention | inputs: 2 h, outputs: 48 h |

## Usage

```bash
cd containers/pyfortracc_IR
docker compose up -d --build     # build and start
docker compose logs -f           # follow the cycles
docker compose down              # stop (the data stays in ./data)
```

By default, the input and output files are kept in the container folder:

```
containers/pyfortracc_IR/data/
├── input/    # NetCDFs downloaded by goesgcp (last 2 h)
├── output/   # tracking table + GeoJSON (last 48 h)
└── tmp/      # goesgcp temporary files
```

Without compose:

```bash
docker build -t pyfortracc_ir .
docker run -d --name pyfortracc_ir --restart unless-stopped -v "$PWD/data":/data pyfortracc_ir
```

## Configuration (`namelist.yaml`)

All the settings are in `namelist.yaml`, which is copied into the image
(`/app/namelist.yaml`). After editing it, rebuild:

```bash
docker compose up -d --build
```

Sections:

- `schedule`: interval, delay after each acquisition slot, retry time,
  maximum cycle duration (`max_cycle_minutes`, see [Recovery](#recovery)) and
  maximum age of the last tracked time stamp for the healthcheck
  (`max_age_minutes`).
- `download`: satellite, product, channel, crop and resolution (goesgcp
  arguments), number of images downloaded on the first run and maximum hours
  recovered after a stop.
- `tracking`: keys passed to the pyfortracc `name_list` (thresholds, minimum
  sizes, vector corrections...). The paths, lat/lon limits,
  `timestamp_pattern` and `pattern_position` are set automatically.
  `resume` is read by the container (see [Recovery](#recovery)).
- `forecast`: enables the forecast, `lead_time` (number of steps),
  `step_minutes` (minutes between the steps, a multiple of
  `tracking.delta_time`: the tracking stays at 10 min) and
  `observation_window`.
- `output`: tracking GeoJSON layers (`boundary`, `trajectory`,
  `vector_field`).
- `retention`: hours of input (`input_hours`, default 2) and output
  (`output_hours`, default 48) data kept. Older files are removed at every
  cycle; `0` keeps them forever.

To use another file without rebuilding, mount it over the default one:
`-v $PWD/namelist.yaml:/app/namelist.yaml:ro`.

> When changing the thresholds, remove the tracking state (see below), since
> pyfortracc does not continue a tracking with different thresholds.

## How it works

Each cycle (`app/realtime.py`):

1. Downloads the images after the last tracked time stamp (on the first run,
   the `bootstrap_files` most recent ones).
2. Tracks only the new images with `persist_uid=True`: `uid`, `iuid`,
   `lifetime` and events continue between cycles.
3. Exports the GeoJSON of the new time stamps.
4. Runs the forecast for each new time stamp.
5. Removes the intermediate forecast files and the inputs/outputs older than
   the `retention` periods. Images not tracked yet are never removed.

If no new image is available, it tries again after `retry_seconds`.

## Recovery

- **Stuck cycle**: a watchdog ends the process when a cycle takes longer than
  `schedule.max_cycle_minutes` (45). The `restart: unless-stopped` policy
  brings the container back.
- **Interrupted cycle** (stuck cycle, `docker stop`, power loss): the time
  stamps of the cycle in progress are kept in `track/pending.json`. On the
  next start, with `tracking.resume: true`, the tracking continues from the
  files already written (`resume=True`) or, when it was already tracked, only
  the GeoJSON and the forecasts are done. An interrupted forecast is done
  again.
- **`docker stop`**: the main process stops like a Ctrl+C and the pyfortracc
  pool workers end with the default SIGTERM, so the pool never waits for a
  worker that holds the queue lock.
- **Health**: `docker ps` shows the container as `healthy` while the last
  tracked time stamp is at most `schedule.max_age_minutes` (60) old
  (`app/health.py`).

## Outputs (`./data/output/`)

```
track/
├── trackingtable/YYYYMMDD_HHMM.parquet       # tracking table
├── geometry/boundary/YYYYMMDD_HHMM.GeoJSON   # cluster boundaries
├── geometry/trajectory/YYYYMMDD_HHMM.GeoJSON # trajectories
└── state/                                    # real-time tracking state
forecast/
└── YYYYMMDD_HHMM/                            # forecast origin time stamp
    └── geometry/boundary/YYYYMMDD_HHMM.GeoJSON  # one file per lead time (30 min)
```

Restart the tracking from scratch:

```bash
docker compose down
rm -rf data/output/track/state
docker compose up -d
```

Run a single cycle (test):

```bash
docker compose run --rm pyfortracc_ir python /app/realtime.py --once
```

## Versions

pyfortracc and goesgcp are installed from their git repositories (`main`
branch) when the image is built. The container does not update itself: to
get a new pyfortracc release, rebuild it. Every build checks the latest commit
of each ref and reinstalls only when it changed:

```bash
docker compose up -d --build
```

To pin a version:

```bash
docker compose build --build-arg PYFORTRACC_REF=<tag|commit> --build-arg GOESGCP_REF=<tag|commit>
```

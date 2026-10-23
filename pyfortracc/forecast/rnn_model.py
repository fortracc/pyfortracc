"""
Recurrent neural network forecast (name_list['forecast_mode'] 'lstm' or 'gru').

The model is object based: it does not draw pixels. For each system of the last
frame it reads the history of the system (one step per frame: vector, size,
intensity, status, lifetime and the auxiliary columns of name_list['rnn_aux'])
and predicts four numbers for the next time step, as corrections of the baselines
of the persistence forecast (TARGETS):
    - u_correction, v_correction: correction of the mean vector of the window
      (pixels per step);
    - size_trend_correction: correction of the area trend (log of the area ratio
      per step);
    - mean_trend_correction: correction of the trend of the mean value (in the
      direction of the operator, so the same model works for '>' and '<' fields).
The inputs (FEATURES) are not columns of the tracking table themselves: they are
computed from its columns (u_, v_, size, mean, min, max, std, lifetime, status,
board, threshold_level), see FEATURES for each one.
The output layer starts at zero, so a model without training (or one that learned
nothing) forecasts the persistence with the trends of the window; as in
morph_trend, the trends fade with the lead time (morphology.DAMPING). The image is
drawn like the persistence one: each system is dilated/eroded with its inner
thresholds kept nested (morphology.morph_clusters), its values shifted and kept in
their threshold levels, and moved by its vector (persistence.render). The image
then enters the tracking cycle again (features extraction, spatial operations,
linking), and the next lead time reads the forecast frame as one more step of the
history of each system.

The networks (LSTMForecaster, GRUForecaster) differ only by their recurrent cell;
the sequences, the training (optionally tuned with optuna), the checkpoints and the
forecast function called by pyfortracc.forecast at every lead time are shared.
Only the variables of the tracking table are used, so the model is independent of
the variable and of the grid. The training settings below are fixed on purpose;
the architecture is set by name_list['rnn_arch'].

Usage: set name_list['forecast_mode'] = 'lstm' (or 'gru') and call
pyfortracc.forecast. The model is trained on the whole tracking up to
forecast_time, or on name_list['rnn_train_period'] = [start, end], and saved in
output_path/forecast/models/ (the file name tells the training period, the
thresholds, delta_time, the window and the architecture, see model_name); the
next calls with the same settings reuse it. Or it is loaded from
name_list['rnn_weights'] (inference only). train_model() trains it without
forecasting, e.g. once on a long tracking, for inference later.
"""
import hashlib
import json
import os
import pathlib
import random
import re

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from pyfortracc._version import __version__
from pyfortracc.default_parameters import default_parameters
from pyfortracc.forecast.morphology import DAMPING, MAX_RATE, morph_clusters
from pyfortracc.forecast.persistence import moved_clusters, read_window, render, to_pixels
from pyfortracc.utilities.utils import get_feature_files

# Training settings
EPOCHS = 300           # maximum number of epochs
PATIENCE = 25          # epochs without improvement of the validation loss before stopping
BATCH = 256            # samples per batch
SEED = 0               # seed of torch, numpy and random
VAL_FRAC = 0.2         # fraction of the last time steps used for validation
MIN_VAL = 20           # minimum validation samples of the split by time (else split by system)
MIN_SAMPLES = 20       # below this number of samples the model is not trained (persistence + trends)
# optuna search (rnn_arch = 'optuna')
N_TRIALS = 25          # maximum number of trials
TUNE_TIMEOUT = 300     # maximum duration of the search (seconds)
MAX_SEQ_LEN = 12       # longest history searched
# Default architecture, overridden by the dict of name_list['rnn_arch']
DEFAULT_ARCH = dict(hidden=32, layers=1, dropout=0.1, seq_len=6, lr=3e-3, weight_decay=1e-4, device='auto')

# Inputs of the network at each time step of a system (one row of the tracking
# table per cluster and frame), computed from the columns of the tracking table by
# step_table. "Signed": multiplied by +1 for the '>' operators and by -1 for the '<'
# ones, so that "more intense" is always positive (e.g. colder for brightness
# temperature). The auxiliary columns of name_list['rnn_aux'] are added after them.
FEATURES = {
    'u_': "column u_, the zonal vector, in pixels per time step",
    'v_': "column v_, the meridional vector, in pixels per time step",
    'u_v_valid': "1 where u_ and v_ exist, 0 where they are NaN (e.g. a NEW cluster)",
    'size_log': "log of the column size (pixels)",
    'size_log_change': "change of size_log since the previous time step (log of the area ratio)",
    'mean_from_threshold': "column mean minus the threshold of the cluster level, signed",
    'peak_from_threshold': "column max (min for the '<' operators) minus the threshold, signed",
    'std': "column std",
    'mean_change': "change of the column mean since the previous time step, signed",
    'lifetime_steps': "column lifetime divided by delta_time",
    'status_NEW': "1 when the column status contains NEW",
    'status_MRG': "1 when the column status contains MRG (merge)",
    'status_SPL': "1 when the column status contains SPL (split)",
    'board': "1 when the cluster touches the border of the domain (column board)",
    'threshold_level_norm': "column threshold_level divided by the number of thresholds - 1",
    # Baselines of the persistence forecast, over the last observation_window frames
    'window_u_mean': "mean of u_ over the window: the vector the persistence moves the system by",
    'window_v_mean': "mean of v_ over the window",
    'window_size_trend': "mean size_log_change of the CON steps of the window (area trend of morph_trend)",
    'window_mean_trend': "mean mean_change of the CON steps of the window (intensity trend of morph_trend)",
}
# Outputs of the network: corrections of the baselines for the next time step. The
# forecast moves the system by window_u_mean + u_correction (and v), and grows it by
# window_size_trend + size_trend_correction (and the mean value likewise)
TARGETS = {
    'u_correction': "u_ of the next time step minus window_u_mean",
    'v_correction': "v_ of the next time step minus window_v_mean",
    'size_trend_correction': "size_log_change of the next time step minus window_size_trend",
    'mean_trend_correction': "mean_change of the next time step minus window_mean_trend",
}
FORMAT = 2


def import_torch():
    """PyTorch, which is only needed by the recurrent forecast modes."""
    # The OpenMP runtime of torch and the one of numpy/opencv may both be loaded
    os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
    try:
        import torch
    except ImportError:
        raise ImportError("The forecast modes 'lstm' and 'gru' need PyTorch: pip install torch "
                          "(see https://pytorch.org for the GPU builds).") from None
    return torch


torch = import_torch()
nn = torch.nn


def pick_device(torch, choice='auto'):
    """The device of the model: the given one, or the best available (CUDA, TPU, Apple MPS, CPU)."""
    choice = os.environ.get('PYFORTRACC_DEVICE', choice or 'auto')
    if choice != 'auto':
        return torch.device(choice)
    if torch.cuda.is_available():
        return torch.device('cuda')
    try:
        import torch_xla.core.xla_model as xm
        return xm.xla_device()
    except Exception:
        pass
    if getattr(torch.backends, 'mps', None) is not None and torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def operator_sign(operator):
    """+1 when larger values are more intense ('>', '>=', '==', '!='), -1 for '<' and '<='."""
    return -1.0 if str(operator).startswith('<') else 1.0


def is_categorical(name_list):
    """Categorical thresholds have no ordering to grow, shrink or intensify."""
    return name_list['operator'] in ('==', '!=')


def aux_column(values):
    """Numeric values of an auxiliary column: scalars as they are, arrays by their mean."""
    if values.dtype != object:
        return pd.to_numeric(values, errors='coerce').astype(float)

    def mean(a):
        if a is None or (np.isscalar(a) and pd.isna(a)):
            return np.nan
        a = np.asarray(a, dtype=float).ravel()
        return float(np.nanmean(a)) if a.size and np.isfinite(a).any() else np.nan
    return values.map(mean).astype(float)


def validate_aux(files, aux):
    """The auxiliary columns must exist in the tracking table."""
    if not aux:
        return
    names = pq.read_schema(files[-1]).names
    missing = [c for c in aux if c not in names]
    if missing:
        raise ValueError(f"name_list['rnn_aux'] columns {missing} are not in the tracking table "
                         f"({files[-1]}). Available columns: {names}")


def step_table(df, name_list, aux, window):
    """
    One row per cluster and time step, sorted by cluster (threshold_level, uid) and
    time, with the input features (FEATURES + aux, including the baselines of the
    persistence window_*: mean vector and trends over the last `window` frames) and
    the targets of the next step (TARGETS, corrections of the baselines; NaN where
    the next step is not a clean continuation).

    Only the steps where the cluster continues (status CON, one delta_time apart,
    not touching the border) are targets or enter the trends, as in
    morphology.system_trends: in a merge or a split the area jumps without the
    system growing.
    """
    dt = pd.to_timedelta(name_list['delta_time'], unit='m')
    sign = operator_sign(name_list['operator'])
    thresholds = np.asarray(name_list['thresholds'], dtype=float)
    max_log = np.log1p(MAX_RATE)

    df = df.dropna(subset=['uid']).sort_values(['threshold_level', 'uid', 'timestamp']).reset_index(drop=True)
    keys = [df['threshold_level'], df['uid']]
    status = df['status'].fillna('').astype(str)
    board = (df['board'].fillna(False).astype(bool) if 'board' in df.columns
             else pd.Series(False, index=df.index))
    level = df['threshold_level'].astype(int).clip(0, len(thresholds) - 1)
    thr = thresholds[level.to_numpy()]
    peak = df['max'] if sign > 0 else df['min']

    def prev(s):
        return s.groupby(keys).shift()

    def rolling(s, n, how='mean'):
        # Over the last n frames (not rows), like the window of the persistence:
        # a cluster missing in a frame has fewer steps in its window
        span = pd.Timedelta(dt * max(int(n), 1))
        series = pd.Series(s.to_numpy(dtype=float), index=df['timestamp'])
        groups = series.groupby([df['threshold_level'].to_numpy(), df['uid'].to_numpy()], sort=True)
        return pd.Series(groups.rolling(span, min_periods=1).agg(how).to_numpy(), index=df.index)

    gap = (df['timestamp'] - prev(df['timestamp'])) == dt
    clean = gap & (status == 'CON') & ~board & ~prev(board).fillna(True).astype(bool)
    log_size = np.log(df['size'].astype(float).clip(lower=1))
    s_mean = sign * df['mean'].astype(float)
    d_log = (log_size - prev(log_size)).where(gap)
    d_mean = (s_mean - prev(s_mean)).where(gap)

    out = pd.DataFrame({'timestamp': df['timestamp'], 'threshold_level': df['threshold_level'],
                        'uid': df['uid']})
    out['u_'], out['v_'] = df['u_'].astype(float), df['v_'].astype(float)
    out['u_v_valid'] = out['u_'].notna().astype(float)
    out['size_log'] = log_size
    out['size_log_change'] = d_log.fillna(0)
    out['mean_from_threshold'] = sign * (df['mean'].astype(float) - thr)
    out['peak_from_threshold'] = sign * (peak.astype(float) - thr)
    out['std'] = df['std'].astype(float) if 'std' in df.columns else 0.0
    out['mean_change'] = d_mean.fillna(0)
    out['lifetime_steps'] = (df['lifetime'].astype(float) / name_list['delta_time']
                             if 'lifetime' in df.columns else 0.0)
    out['status_NEW'] = status.str.contains('NEW').astype(float)
    out['status_MRG'] = status.str.contains('MRG').astype(float)
    out['status_SPL'] = status.str.contains('SPL').astype(float)
    out['board'] = board.astype(float)
    out['threshold_level_norm'] = level / max(len(thresholds) - 1, 1)
    # Baselines: what the persistence (mean vector) and morph_trend (trends) use
    out['window_u_mean'] = rolling(out['u_'], window)
    out['window_v_mean'] = rolling(out['v_'], window)
    out['window_size_trend'] = rolling(d_log.where(clean), window - 1).fillna(0).clip(-max_log, max_log)
    out['window_mean_trend'] = rolling(d_mean.where(clean), window - 1).fillna(0)
    for col in aux:
        values = aux_column(df[col]) if col in df.columns else pd.Series(np.nan, index=df.index)
        # The forecast frames have no auxiliary data: the last observed value is kept
        out[col] = values.groupby(keys).ffill()
    # Extremes of the values over the window (bounds of the intensity at the last level)
    out['value_min'] = rolling(df['min'], window, 'min')
    out['value_max'] = rolling(df['max'], window, 'max')

    # Targets: the next step of the same cluster
    def nxt(s):
        return s.groupby(keys).shift(-1)
    target_time = nxt(df['timestamp'])
    ok = ((target_time - df['timestamp']) == dt) & (nxt(status) == 'CON') & ~board & \
        ~nxt(board).fillna(True).astype(bool) & nxt(out['u_']).notna() & out['window_u_mean'].notna()
    out['target_time'] = target_time.where(ok)
    out['u_correction'] = (nxt(out['u_']) - out['window_u_mean']).where(ok)
    out['v_correction'] = (nxt(out['v_']) - out['window_v_mean']).where(ok)
    out['size_trend_correction'] = ((nxt(log_size) - log_size).clip(-max_log, max_log) -
                                    out['window_size_trend']).where(ok)
    out['mean_trend_correction'] = (nxt(s_mean) - s_mean - out['window_mean_trend']).where(ok)
    out['pos'] = out.groupby(['threshold_level', 'uid']).cumcount()
    return out


def sequences(feats, pos, rows, seq_len):
    """
    Input sequences (n, seq_len, n_features + 1) ending at the given rows of the
    step table: the last seq_len steps of each cluster, left padded with zeros. The
    last channel is 1 on the real steps.
    """
    n, f = len(rows), feats.shape[1]
    x = np.zeros((n, seq_len, f + 1), dtype=np.float32)
    for j in range(seq_len):
        valid = pos[rows] >= j
        x[valid, seq_len - 1 - j, :f] = feats[rows[valid] - j]
        x[valid, seq_len - 1 - j, f] = 1.0
    return x


def normalized(table, columns, mean, std):
    """The features z-scored with the statistics of the training, NaN set to the mean (0)."""
    x = (table[columns].to_numpy(dtype=float) - np.asarray(mean)) / np.asarray(std)
    return np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)


def seed_everything(torch):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def build_model(model_cls, n_in, arch):
    return model_cls(n_in, len(TARGETS), hidden=int(arch['hidden']), layers=int(arch['layers']),
                     dropout=float(arch['dropout']))


def fit(torch, model_cls, data, arch, device, report=None):
    """
    Train a model on data (x, y, mask of the train and validation sets) with AdamW,
    Huber loss on the normalized targets and early stopping on the validation loss.
    Returns the model with its best weights and its validation loss.
    """
    seed_everything(torch)
    seq_len = int(arch['seq_len'])

    def tensors(name):
        x = torch.as_tensor(data[f'x_{name}'][:, -seq_len:], device=device)
        return x, torch.as_tensor(data[f'y_{name}'], device=device), torch.as_tensor(data[f'm_{name}'], device=device)
    x_tr, y_tr, m_tr = tensors('train')
    x_va, y_va, m_va = tensors('val')
    model = build_model(model_cls, x_tr.shape[-1], arch).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=float(arch['lr']), weight_decay=float(arch['weight_decay']))
    gen = torch.Generator().manual_seed(SEED)

    def loss_fn(pred, y, m):
        loss = torch.nn.functional.smooth_l1_loss(pred, y, reduction='none') * m
        return loss.sum() / m.sum().clamp(min=1)

    best, best_state, wait = np.inf, None, 0
    for epoch in range(EPOCHS):
        model.train()
        for idx in torch.randperm(len(x_tr), generator=gen).split(BATCH):
            idx = idx.to(device)
            optim.zero_grad()
            loss = loss_fn(model(x_tr[idx]), y_tr[idx], m_tr[idx])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
        model.eval()
        with torch.no_grad():
            val = float(loss_fn(model(x_va), y_va, m_va))
        if report is not None:
            report(epoch, val)
        if val < best - 1e-6:
            best, wait = val, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= PATIENCE:
                break
    model.load_state_dict(best_state)
    return model, best


def tune(torch, model_cls, data, device):
    """Architecture searched with optuna (TPE sampler, median pruner, N_TRIALS or TUNE_TIMEOUT)."""
    try:
        import optuna
    except ImportError:
        raise ImportError("name_list['rnn_arch'] = 'optuna' needs optuna: pip install optuna") from None
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        arch = dict(DEFAULT_ARCH,
                    hidden=trial.suggest_categorical('hidden', [16, 32, 64, 128]),
                    layers=trial.suggest_int('layers', 1, 2),
                    dropout=trial.suggest_float('dropout', 0.0, 0.3),
                    seq_len=trial.suggest_int('seq_len', 2, MAX_SEQ_LEN),
                    lr=trial.suggest_float('lr', 1e-4, 1e-2, log=True),
                    weight_decay=trial.suggest_float('weight_decay', 1e-6, 1e-3, log=True))

        def report(epoch, val):
            trial.report(val, epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()
        return fit(torch, model_cls, data, arch, device, report)[1]

    study = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=SEED),
                                pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10))
    study.optimize(objective, n_trials=N_TRIALS, timeout=TUNE_TIMEOUT)
    print(f"  * optuna: {len(study.trials)} trials, best validation loss {study.best_value:.4f} "
          f"with {study.best_params}")
    return dict(DEFAULT_ARCH, **study.best_params)


def split(samples):
    """Train/validation split: the last VAL_FRAC of the target times, else by system."""
    times = np.sort(samples['target_time'].unique())
    cut = times[int(np.floor(len(times) * (1 - VAL_FRAC)))] if len(times) > 1 else times[-1]
    val = (samples['target_time'] >= cut).to_numpy()
    if val.sum() < MIN_VAL or (~val).sum() < MIN_VAL:
        rng = np.random.default_rng(SEED)
        clusters = samples[['threshold_level', 'uid']].drop_duplicates()
        chosen = clusters.sample(frac=VAL_FRAC, random_state=rng.integers(1 << 31))
        val = samples.set_index(['threshold_level', 'uid']).index.isin(
            pd.MultiIndex.from_frame(chosen)) if len(chosen) else np.zeros(len(samples), bool)
    return ~val, val


def frame_time(path):
    """Timestamp of a tracking table frame (its file name)."""
    return pd.to_datetime(pathlib.Path(path).stem, format='%Y%m%d_%H%M')


def training_files(name_list):
    """
    The frames of the tracking table the model is trained on: those of
    name_list['rnn_train_period'] = [start, end], or else the whole tracking up to
    forecast_time (all of it when forecast_time is None), so that the model never
    learns from the future of the forecast.
    """
    files = get_feature_files(name_list['output_path'] + 'track/trackingtable/')
    period = name_list.get('rnn_train_period')
    if period:
        start, end = pd.to_datetime(period[0]), pd.to_datetime(period[1])
        if name_list.get('forecast_time') and end > pd.to_datetime(name_list['forecast_time']):
            print(f"  * Warning: rnn_train_period ends at {end}, after forecast_time "
                  f"{name_list['forecast_time']}: the model learns from frames after the forecast start.")
    else:
        start = None
        end = pd.to_datetime(name_list['forecast_time']) if name_list.get('forecast_time') else None
    files = [f for f in files if (start is None or frame_time(f) >= start) and (end is None or frame_time(f) <= end)]
    if not files:
        raise FileNotFoundError(f"No tracking table frames to train on in {name_list['output_path']}"
                                f"track/trackingtable/ (rnn_train_period {period}, forecast_time "
                                f"{name_list.get('forecast_time')}).")
    return files


OPERATOR_NAMES = {'>': 'gt', '>=': 'ge', '<': 'lt', '<=': 'le', '==': 'eq', '!=': 'ne'}


def model_name(name_list, mode, files, aux, window):
    """
    File name of a trained model, e.g.
    lstm_202511050000-202511051200_le235-220-210_dt10min_win3_h32l1seq6_1a2b3c4d.pt:
    mode, training period (first and last frames), operator and thresholds of the
    tracking, delta_time, observation_window (frames of the persistence baselines),
    architecture (hidden units, layers and seq_len, the time steps of history read
    by the network; 'optuna' when searched), the auxiliary columns (aux-...) and a
    hash of all the settings, which tells apart the models of other settings.
    """
    arch = name_list.get('rnn_arch')
    if arch == 'optuna':
        arch_tag = 'optuna'
    else:
        a = dict(DEFAULT_ARCH, **(arch or {}))
        arch_tag = f"h{a['hidden']}l{a['layers']}seq{a['seq_len']}"
    thresholds = '-'.join(f'{float(t):g}' for t in name_list['thresholds'])
    parts = [mode, f"{frame_time(files[0]):%Y%m%d%H%M}-{frame_time(files[-1]):%Y%m%d%H%M}",
             f"{OPERATOR_NAMES.get(name_list['operator'], 'op')}{thresholds}",
             f"dt{float(name_list['delta_time']):g}min", f"win{window}", arch_tag]
    if aux:
        parts.append('aux-' + '-'.join(re.sub(r'[^A-Za-z0-9.]+', '', c) for c in aux))
    return '_'.join(parts) + f"_{settings_key(name_list, mode, files, aux, window)}.pt"


def settings_key(name_list, mode, files, aux, window):
    """Hash of everything that changes the trained model, which names its checkpoint."""
    settings = dict(mode=mode, arch=name_list.get('rnn_arch'), aux=aux, window=window,
                    thresholds=list(map(float, name_list['thresholds'])), operator=name_list['operator'],
                    delta_time=name_list['delta_time'], x_res=name_list.get('x_res'),
                    y_res=name_list.get('y_res'),
                    files=[pathlib.Path(files[0]).name, pathlib.Path(files[-1]).name, len(files),
                           os.path.getmtime(files[-1])],
                    training=[EPOCHS, PATIENCE, BATCH, SEED, VAL_FRAC, N_TRIALS, TUNE_TIMEOUT, FORMAT])
    return hashlib.sha1(json.dumps(settings, sort_keys=True, default=str).encode()).hexdigest()[:8]


def train(torch, name_list, model_cls, mode):
    """
    Train the model on the frames of training_files (the whole tracking up to
    forecast_time, or name_list['rnn_train_period']), or reuse the checkpoint of a
    previous run with the same settings, saved in output_path/forecast/models/
    (see model_name). Returns the checkpoint.
    """
    files = training_files(name_list)
    aux = list(name_list.get('rnn_aux') or [])
    validate_aux(files, aux)
    window = int(name_list.get('observation_window') or 3)
    train_start, train_until = frame_time(files[0]), frame_time(files[-1])
    path = pathlib.Path(name_list['output_path']) / 'forecast' / 'models' / \
        model_name(name_list, mode, files, aux, window)
    if path.exists():
        print(f"  * {mode.upper()}: reusing the model trained with the same settings: {path}")
        return dict(load_checkpoint(torch, path, name_list, mode), path=str(path))

    table = step_table(to_pixels(read_window(files), name_list), name_list, aux, window)
    columns = list(FEATURES) + aux
    inputs = table[table['timestamp'] <= train_until]
    mean = inputs[columns].mean().fillna(0).to_numpy(dtype=float)
    std = inputs[columns].std().fillna(1).replace(0, 1).to_numpy(dtype=float)
    feats = normalized(table, columns, mean, std)
    samples = table[table['target_time'].notna() & (table['target_time'] <= train_until)]
    mask = np.ones(len(TARGETS), dtype=np.float32)
    if is_categorical(name_list):
        mask[2:] = 0  # no size or mean trend (the last two TARGETS) for categorical thresholds
    arch_cfg = name_list.get('rnn_arch')
    arch = dict(DEFAULT_ARCH, **(arch_cfg if isinstance(arch_cfg, dict) else {}))
    device = pick_device(torch, arch['device'])
    ckpt = dict(format=FORMAT, mode=mode, pyfortracc_version=__version__.strip().strip('"'),
                torch_version=str(torch.__version__), features=columns, aux=aux, targets=list(TARGETS), window=window,
                operator=name_list['operator'], thresholds=list(map(float, name_list['thresholds'])),
                delta_time=float(name_list['delta_time']), x_res=float(name_list['x_res']),
                y_res=float(name_list['y_res']), train_start=str(train_start), train_until=str(train_until),
                n_frames=len(files), x_mean=mean.tolist(), x_std=std.tolist())

    if len(samples) < MIN_SAMPLES:
        print(f"  * {mode.upper()}: only {len(samples)} training samples up to {train_until}; the model "
              f"is not trained and forecasts the persistence with the trends of the window.")
        model = build_model(model_cls, len(columns) + 1, arch)
        ckpt.update(arch=arch, y_std=[1.0] * len(TARGETS), n_train=len(samples), n_val=0,
                    val_loss=None, baseline_loss=None)
    else:
        y_std = samples[list(TARGETS)].std().fillna(1).replace(0, 1).to_numpy(dtype=float)
        y = np.nan_to_num(samples[list(TARGETS)].to_numpy(dtype=float) / y_std).astype(np.float32)
        tr, va = split(samples)
        if not va.any():
            va = tr.copy()
        rows = samples.index.to_numpy()
        max_len = MAX_SEQ_LEN if arch_cfg == 'optuna' else int(arch['seq_len'])
        x = sequences(feats, table['pos'].to_numpy(), rows, max_len)
        m = np.broadcast_to(mask, y.shape).astype(np.float32)
        data = dict(x_train=x[tr], y_train=y[tr], m_train=m[tr], x_val=x[va], y_val=y[va], m_val=m[va])
        print(f"  * {mode.upper()}: training on {tr.sum()} samples (validation {va.sum()}) of the "
              f"{len(files)} frames from {train_start} to {train_until}, device {device}")
        if arch_cfg == 'optuna':
            arch = tune(torch, model_cls, data, device)
            arch['device'] = str(DEFAULT_ARCH['device'])
        model, val_loss = fit(torch, model_cls, data, arch, device)
        # Loss of the zero correction: the persistence with the trends of the window
        zero = torch.nn.functional.smooth_l1_loss(torch.zeros(va.sum(), len(TARGETS)),
                                                  torch.as_tensor(y[va]), reduction='none') * torch.as_tensor(m[va])
        baseline = float(zero.sum() / torch.as_tensor(m[va]).sum().clamp(min=1))
        print(f"  * {mode.upper()}: validation loss {val_loss:.4f} (persistence + trends: {baseline:.4f})")
        ckpt.update(arch=arch, y_std=y_std.tolist(), n_train=int(tr.sum()), n_val=int(va.sum()),
                    val_loss=val_loss, baseline_loss=baseline)
    # Plain python values, which torch.load(weights_only=True) accepts
    ckpt['arch'] = {k: (str(v) if k == 'device' else int(v) if k in ('hidden', 'layers', 'seq_len') else float(v))
                    for k, v in ckpt['arch'].items()}
    ckpt['state_dict'] = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    ckpt['path'] = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(ckpt, path)
    print(f"  * {mode.upper()}: weights saved in {path} (name_list['rnn_weights'] to reuse them)")
    return ckpt


def load_checkpoint(torch, path, name_list, mode):
    """A checkpoint written by train(), checked against the name_list."""
    if not pathlib.Path(path).exists():
        raise FileNotFoundError(f"name_list['rnn_weights']: {path} not found.")
    ckpt = torch.load(path, map_location='cpu', weights_only=True)
    if ckpt.get('format') != FORMAT or ckpt.get('mode') != mode:
        raise ValueError(f"{path} is not a pyfortracc '{mode}' model (mode {ckpt.get('mode')!r}).")
    for key, value in (('operator', name_list['operator']),
                       ('thresholds', list(map(float, name_list['thresholds']))),
                       ('delta_time', float(name_list['delta_time']))):
        if ckpt[key] != value:
            raise ValueError(f"The model {path} was trained with {key} = {ckpt[key]}, "
                             f"but the name_list has {value}.")
    if not np.isclose(ckpt['x_res'], name_list['x_res']) or not np.isclose(ckpt['y_res'], name_list['y_res']):
        print(f"  * Warning: the model {path} was trained on a grid of another resolution; its vectors "
              f"are in pixels per time step.")
    aux = list(name_list.get('rnn_aux') or [])
    if aux and aux != ckpt['aux']:
        print(f"  * Warning: name_list['rnn_aux'] = {aux}, but the model uses {ckpt['aux']}.")
    return ckpt


def build_forecaster(name_list, model_cls, mode):
    """
    The forecast function of a recurrent model, with the forecast.persistence
    signature: forecast_function(tracked_files, name_list, lead, history_files).

    The model is loaded from name_list['rnn_weights'] or trained (see train) once,
    before the lead times. Its input at the first lead time is the history of the
    systems in the tracking table up to forecast_time (the last seq_len +
    observation_window frames); at the next lead times the forecast frames are
    added to it.
    """
    torch = import_torch()
    # The observed frames: the tracking table up to forecast_time
    observed_files = get_feature_files(name_list['output_path'] + 'track/trackingtable/')
    if name_list.get('forecast_time'):
        start = pd.to_datetime(name_list['forecast_time'])
        observed_files = [f for f in observed_files if frame_time(f) <= start]
    if name_list.get('rnn_weights'):
        ckpt = load_checkpoint(torch, name_list['rnn_weights'], name_list, mode)
        validate_aux(observed_files, ckpt['aux'])
        print(f"  * {mode.upper()}: weights loaded from {name_list['rnn_weights']} (trained on "
              f"{ckpt['train_start']} to {ckpt['train_until']})")
    else:
        ckpt = train(torch, name_list, model_cls, mode)
    arch, aux, window = ckpt['arch'], ckpt['aux'], ckpt['window']
    seq_len = int(arch['seq_len'])
    device = pick_device(torch, arch.get('device', 'auto'))
    model = build_model(model_cls, len(ckpt['features']) + 1, arch)
    model.load_state_dict(ckpt['state_dict'])
    model = model.to(device).eval()
    y_std = np.asarray(ckpt['y_std'])
    sign = operator_sign(name_list['operator'])
    max_log = np.log1p(MAX_RATE)
    # Observed history read by the model: enough steps for its sequences and baselines
    observed = set(map(str, observed_files))
    history = to_pixels(read_window(observed_files[-(seq_len + window):]), name_list)
    # Forecast frames of the previous lead times; kept here because forecast()
    # drops the oldest frames of tracked_files as the lead time grows
    forecast_frames = {}

    def forecast_function(tracked_files, name_list, lead=0, history_files=None):
        current = to_pixels(read_window(tracked_files), name_list)
        moved = moved_clusters(current, name_list)
        # History of each system: the observed frames, then the forecast frames
        # (re-extracted and re-linked by the tracking at the previous lead times)
        for f in tracked_files:
            if str(f) not in observed and str(f) not in forecast_frames:
                forecast_frames[str(f)] = to_pixels(read_window([f]), name_list)
        if moved.empty:
            return render(moved, name_list)
        table = step_table(pd.concat([history] + list(forecast_frames.values()), ignore_index=True),
                           name_list, aux, window)
        feats = normalized(table, ckpt['features'], ckpt['x_mean'], ckpt['x_std'])
        last = table[table['timestamp'] == current['timestamp'].max()]
        x = sequences(feats, table['pos'].to_numpy(), last.index.to_numpy(), seq_len)
        with torch.no_grad():
            pred = model(torch.as_tensor(x, device=device)).cpu().numpy() * y_std
        last = last[['threshold_level', 'uid', 'window_u_mean', 'window_v_mean', 'window_size_trend',
                     'window_mean_trend',
                     'value_min', 'value_max']].copy()
        last[list(TARGETS)] = pred
        moved = moved.merge(last, on=['threshold_level', 'uid'], how='left')
        # Vector of each system: the persistence one plus the correction of the network
        has = moved['window_u_mean'].notna()
        moved.loc[has, 'u_mean'] = moved.loc[has, 'window_u_mean'] + moved.loc[has, 'u_correction']
        moved.loc[has, 'v_mean'] = moved.loc[has, 'window_v_mean'] + moved.loc[has, 'v_correction']
        if is_categorical(name_list):
            return render(moved, name_list)
        # The trends fade with the lead time, as in morph_trend: the forecast frames
        # carry the growth forecast at the previous lead times, which would
        # otherwise compound
        damping = DAMPING ** lead
        # Area rate and value change of each system (inputs of morph_clusters): the
        # trends of the window plus the corrections of the network
        size_trend = moved['window_size_trend'] + moved['size_trend_correction']
        mean_trend = moved['window_mean_trend'] + moved['mean_trend_correction']
        moved['log_rate'] = (damping * size_trend).fillna(0).clip(-max_log, max_log)
        moved['value_delta'] = (damping * sign * mean_trend).fillna(0)
        return render(morph_clusters(moved, name_list), name_list)

    return forecast_function


class RecurrentForecaster(nn.Module):
    """
    Recurrent network over the steps of a system, then a small dense head on its
    last state. The subclasses set the recurrent cell (CELL).

    Parameters
    ----------
    n_in : int
        Features per time step (FEATURES, the auxiliary columns and the mask of
        the padded steps).
    n_out : int
        Outputs (TARGETS).
    hidden, layers, dropout :
        Architecture (name_list['rnn_arch']).
    """
    CELL = None

    def __init__(self, n_in, n_out, hidden=32, layers=1, dropout=0.1):
        super().__init__()
        self.rnn = self.CELL(n_in, hidden, num_layers=layers, batch_first=True,
                             dropout=dropout if layers > 1 else 0.0)
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(hidden, hidden), nn.ReLU(),
                                  nn.Linear(hidden, n_out))
        # Zero output at the start: the persistence with the trends of the window
        nn.init.zeros_(self.head[-1].weight)
        nn.init.zeros_(self.head[-1].bias)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.head(out[:, -1])


class LSTMForecaster(RecurrentForecaster):
    """Long Short-Term Memory network (forecast_mode 'lstm')."""
    CELL = nn.LSTM


class GRUForecaster(RecurrentForecaster):
    """Gated Recurrent Unit network (forecast_mode 'gru'): fewer parameters than the LSTM, which may suit
    short tracking tables."""
    CELL = nn.GRU


MODELS = {'lstm': LSTMForecaster, 'gru': GRUForecaster}


def forecaster(name_list):
    """
    Forecast function of name_list['forecast_mode'] ('lstm' or 'gru'), called by
    pyfortracc.forecast at every lead time. The model is trained or loaded here,
    once.
    """
    mode = name_list['forecast_mode']
    return build_forecaster(name_list, MODELS[mode], mode)


def train_model(name_list, read_function):
    """
    Train the model of name_list['forecast_mode'] ('lstm' or 'gru') on the tracking
    table in name_list['output_path'], without forecasting: on the frames of
    name_list['rnn_train_period'] = [start, end], or else on the whole tracking (up
    to name_list['forecast_time'] when it is set).

    Returns
    -------
    str
        Path of the weights (in output_path/forecast/models/), to be set in
        name_list['rnn_weights'] for inference.
    """
    name_list = default_parameters(name_lst=dict(name_list), read_function=read_function)
    mode = name_list['forecast_mode']
    if mode not in MODELS:
        raise ValueError(f"name_list['forecast_mode'] must be one of {list(MODELS)} to train a model.")
    return train(torch, name_list, MODELS[mode], mode)['path']

This release fixes the **persistence forecast**, which moved the clusters along the wrong axes, and adds **pyfortracc_IR**, a Docker container for real-time tracking and forecasting of GOES-19 infrared clusters.

## 🐛 Bug fixes

### Persistence forecast moved the clusters along the wrong axes
`u_` is the zonal component (x, columns) and `v_` the meridional one (y, rows), as in the rest of pyfortracc. The persistence forecast added `u_` to the rows and `v_` to the columns, so a system moving east was forecast moving north (or south). With lat/lon grids the conversion from degrees to pixels was also swapped (`u_ / y_res`, `v_ / x_res`).

Now:
- `u_` moves `array_x` and `v_` moves `array_y`;
- the conversion is `u_ / x_res` and `v_ / y_res`.

> Forecasts made with earlier versions have the displacement on the wrong axes. Run them again with this version.

### Forecast crash with clusters without a mean vector
A cluster at the forecast time without a mean vector (e.g. a `NaN` uid, dropped by the grouping) made the forecast fail with:

```
ValueError: cannot convert float NaN to integer
```

These clusters are now left out of the forecast image.

## ✨ New features

### pyfortracc_IR: real-time container (`containers/pyfortracc_IR`)
A Docker container that, every 10 minutes, downloads the GOES-19 channel 13 images with [goesgcp](https://github.com/helvecioneto/goesgcp), tracks the clusters with `persist_uid=True` (uids continue between cycles), exports the GeoJSON layers and runs the persistence forecast for each new time stamp.

```bash
cd containers/pyfortracc_IR
docker compose up -d --build
```

Everything is set in `namelist.yaml`. Main features:

- **Forecast steps** (`forecast.step_minutes`): the forecast runs every 30 min up to 3 h by default, while the tracking stays at 10 min.
- **Recovery**: a watchdog ends a cycle stuck longer than `schedule.max_cycle_minutes` and Docker restarts the container. An interrupted cycle (stuck, `docker stop`, power loss) continues from the files already written (`resume=True`).
- **Clean stop**: on `docker stop`, the multiprocessing pool workers end with SIGTERM, so the pool never waits for ever on a worker holding the queue lock.
- **Healthcheck**: `docker ps` shows the container as `healthy` while the last tracked time stamp is recent (`schedule.max_age_minutes`).
- **Retention**: inputs and outputs older than `retention` are removed at every cycle. Logs are rotated.
- **Always up to date**: every `docker compose up -d --build` installs the latest commit of pyfortracc and goesgcp, and reuses the cache while there is no new commit. To pin a version:

```bash
docker compose build --build-arg PYFORTRACC_REF=v1.4.2
```

See `containers/pyfortracc_IR/README.md` for the details.

## 🧪 Tests

`tests/forecast.py` now checks the forecast on the real tracking data:

- `check_uv_axes`: on the observed tracking, the displacement of each cluster follows `u_` along the columns and `v_` along the rows (median error of 1.4 pixels, against 5.2 pixels with the axes swapped);
- `check_persistence`: the first lead time image written by `pyfortracc.forecast` is equal, pixel by pixel, to the anchor clusters moved by their mean vector.

## ⬆️ Upgrade

```bash
pip install -U pyfortracc
```

**Full Changelog**: https://github.com/fortracc/pyfortracc/compare/v1.4.1...v1.4.2

# pyFortraCC IR - real-time tracking and forecasting of GOES-19 clusters

# ---------------------------------------------------------------- build stage
# Some dependencies (e.g. fiona on arm64) have no wheels and are compiled
# against the system GDAL
FROM python:3.12-slim AS builder

# Versions installed from the git repositories
ARG PYFORTRACC_REF=main
ARG GOESGCP_REF=main

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Commit of each ref (branch, tag or sha): the content only changes with a new
# commit, so a build reuses the cached install below until the ref moves and
# `docker compose up -d --build` always gets the latest commit of main
ADD https://api.github.com/repos/fortracc/pyfortracc/commits/${PYFORTRACC_REF} /tmp/pyfortracc.json
ADD https://api.github.com/repos/helvecioneto/goesgcp/commits/${GOESGCP_REF} /tmp/goesgcp.json

RUN pip install "git+https://github.com/fortracc/pyfortracc@${PYFORTRACC_REF}" \
    && pip install "git+https://github.com/helvecioneto/goesgcp@${GOESGCP_REF}" \
    && pip install pyyaml

# -------------------------------------------------------------- runtime stage
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PATH=/opt/venv/bin:$PATH \
    NAMELIST=/app/namelist.yaml

# GDAL runtime library used by the compiled dependencies and libxcb used by
# opencv on arm64
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin libxcb1 tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app/ /app/
COPY namelist.yaml /app/namelist.yaml

RUN mkdir -p /data/input /data/output
VOLUME ["/data"]

# First cycle (bootstrap + forecasts) takes a few minutes
HEALTHCHECK --interval=2m --timeout=30s --start-period=20m --retries=3 \
    CMD ["python", "/app/health.py"]

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "/app/realtime.py"]

"""
Docker healthcheck: healthy while the newest tracked time stamp is recent.

GOES-19 publishes a Full Disk every 10 min; a last tracked time stamp older
than schedule.max_age_minutes means that the download or the tracking is
stuck (or that NOAA stopped publishing).
"""
import json
import os
import sys
from datetime import datetime, timezone

import yaml


def main():
    with open(os.environ.get('NAMELIST', '/app/namelist.yaml')) as file:
        cfg = yaml.safe_load(file)
    limit = float(cfg['schedule'].get('max_age_minutes', 60) or 0)
    if limit <= 0:
        return 0
    state_file = cfg['paths']['output'] + 'track/state/state.json'
    try:
        with open(state_file) as file:
            last = datetime.fromisoformat(str(json.load(file)['last_stamp']))
    except (OSError, ValueError, KeyError, TypeError):
        print('no tracked time stamp yet')
        return 1
    # The time stamps are the scan times in UTC, without time zone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    age = (now - last.replace(tzinfo=None)).total_seconds() / 60
    print('last tracked time stamp {:.0f} min ago'.format(age))
    return 0 if age <= limit else 1


if __name__ == '__main__':
    sys.exit(main())

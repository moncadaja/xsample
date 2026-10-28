"""Minimal EPICS Archiver Appliance client.

Replaces databroker v0's ``ArchiverEventSource`` (``Broker.named('iss-archiver')``),
keeping the two things the sample-environment GUI used: the ``pvs`` registry
(alias -> PV name) and ``tables_given_times(since, until)``.
"""
from datetime import datetime, timezone

import pandas as pd
import requests


class ArchiverClient:
    def __init__(self, url, tz='US/Eastern', pvs=None, timeout=10, verify_ssl=False):
        """``url`` is the retrieval root, e.g. ``https://host:17668/retrieval``."""
        self.url = url.rstrip('/')
        self.tz = tz
        self.pvs = dict(pvs or {})
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    @staticmethod
    def _iso(t):
        return datetime.fromtimestamp(float(t), tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def get_data(self, pv, since, until):
        """Samples of ``pv`` between two POSIX timestamps as a DataFrame with ``time`` and ``data``."""
        response = requests.get(f'{self.url}/data/getData.json',
                                params={'pv': pv, 'from': self._iso(since), 'to': self._iso(until)},
                                timeout=self.timeout, verify=self.verify_ssl)
        response.raise_for_status()
        payload = response.json()
        samples = payload[0]['data'] if payload else []
        seconds = [s['secs'] + s.get('nanos', 0) * 1e-9 for s in samples]
        time = pd.to_datetime(seconds, unit='s', utc=True).tz_convert(self.tz)
        return pd.DataFrame({'time': time, 'data': [s['val'] for s in samples]})

    def tables_given_times(self, since, until):
        """{alias: DataFrame} for every registered PV; a PV that fails returns an empty frame."""
        tables = {}
        for alias, pv in self.pvs.items():
            try:
                tables[alias] = self.get_data(pv, since, until)
            except Exception as exc:
                print(f'[Archiver] {alias} ({pv}): {exc}')
                tables[alias] = pd.DataFrame({'time': pd.to_datetime([], utc=True).tz_convert(self.tz), 'data': []})
        return tables

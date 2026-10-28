import pandas as pd

from iss_xsample.archiver import ArchiverClient


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_tables_given_times_builds_time_series(monkeypatch):
    calls = []

    def fake_get(url, params, timeout, verify):
        calls.append((url, params))
        return _Response([{'meta': {'name': params['pv']},
                           'data': [{'secs': 1_700_000_000, 'nanos': 0, 'val': 1.5},
                                    {'secs': 1_700_000_010, 'nanos': 500_000_000, 'val': 2.5}]}])

    monkeypatch.setattr('iss_xsample.archiver.requests.get', fake_get)
    client = ArchiverClient('https://archiver.example:17668/retrieval/', pvs={'temp2': 'XF:08IDB-CT{T}Data-I'})
    tables = client.tables_given_times(1_700_000_000, 1_700_000_100)

    assert calls[0][0] == 'https://archiver.example:17668/retrieval/data/getData.json'
    assert calls[0][1]['pv'] == 'XF:08IDB-CT{T}Data-I'
    assert calls[0][1]['from'] == '2023-11-14T22:13:20.000000Z'
    df = tables['temp2']
    assert list(df.columns) == ['time', 'data'] and list(df['data']) == [1.5, 2.5]
    assert str(df['time'].dt.tz) == 'US/Eastern'
    assert (df['time'].iloc[1] - df['time'].iloc[0]).total_seconds() == 10.5


def test_failed_pv_gives_empty_frame(monkeypatch):
    def failing_get(*args, **kwargs):
        raise ConnectionError('no route')

    monkeypatch.setattr('iss_xsample.archiver.requests.get', failing_get)
    client = ArchiverClient('https://archiver.example/retrieval', pvs={'a': 'PV:A'})
    df = client.tables_given_times(0, 1)['a']
    assert df.empty and list(df.columns) == ['time', 'data']

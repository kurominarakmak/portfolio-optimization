"""Strict offline USD accounting and attributed daily total returns."""
import csv
import json
from pathlib import Path
import numpy as np
import pandas as pd


def utc(value):
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return stamp.tz_convert('UTC')


def read_portfolio(path, as_of, max_age_days=4):
    frame = pd.read_csv(path, keep_default_na=False)
    required = {'symbol','quantity','price','currency','valuation_timestamp','nav'}
    if not required <= set(frame) or set(frame)-required-{'cost_basis'}:
        raise ValueError('Unexpected holdings schema')
    if frame.empty or frame.symbol.duplicated().any() or (frame.symbol.str.strip()!=frame.symbol).any() or (frame.symbol=='').any():
        raise ValueError('Empty or duplicate symbols')
    for col in ['quantity','price','nav'] + (['cost_basis'] if 'cost_basis' in frame else []):
        frame[col] = pd.to_numeric(frame[col], errors='raise')
        if not np.isfinite(frame[col]).all() or (frame[col]<0).any():
            raise ValueError('Nonfinite or negative holdings')
    if (frame.currency!='USD').any() or (frame.price<=0).any() or (frame.symbol=='CASH').sum()!=1:
        raise ValueError('Require USD, positive prices and one CASH row')
    if frame.loc[frame.symbol=='CASH','price'].iloc[0] != 1:
        raise ValueError('Cash price must be one USD')
    stamps = [utc(x) for x in frame.valuation_timestamp]
    if len(set(stamps))!=1 or not pd.Timedelta(0)<=utc(as_of)-stamps[0]<=pd.Timedelta(days=max_age_days):
        raise ValueError('Inconsistent, future or stale snapshot')
    value=frame.quantity.to_numpy()*frame.price.to_numpy()
    nav=float(value.sum())
    if nav<=0 or not np.allclose(frame.nav,nav,atol=.01,rtol=0):
        raise ValueError('Declared NAV does not reconcile')
    frame=frame.assign(value=value).set_index('symbol')
    order=[x for x in frame.index if x!='CASH']+['CASH']
    frame=frame.loc[order]
    return {'positions':frame,'nav':nav,'timestamp':stamps[0].isoformat(),'weights':frame.value.to_numpy()/nav,'symbols':order}


def validate_returns(frame, metadata, symbols=None):
    required={'provider','permitted_usage','adjustment','currency','frequency','units','retrieved_at','kind','coverage_start','coverage_end'}
    if not required<=metadata.keys() or any(not metadata[k] for k in required):
        raise ValueError('Missing market-data provenance')
    utc(metadata['retrieved_at'])
    if metadata['adjustment']!='total_return' or metadata['currency']!='USD' or metadata['frequency']!='daily' or metadata['units']!='decimal' or metadata['kind'] not in {'observed','synthetic'}:
        raise ValueError('Require attributed daily USD decimal total returns')
    frame=frame.copy()
    frame.index=pd.to_datetime(frame.index,errors='raise')
    if frame.index.tz is not None: frame.index=frame.index.tz_convert('UTC').tz_localize(None)
    if not frame.index.equals(frame.index.normalize()): raise ValueError('Daily returns require date-only observations')
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing or frame.columns.duplicated().any():
        raise ValueError('Unsorted or duplicate dates/symbols')
    if symbols is not None and set(frame.columns)!=set(symbols):
        raise ValueError('Universe mismatch')
    if len(frame)<max(60,5*len(frame.columns)) or frame.empty or not len(frame.columns):
        raise ValueError('Insufficient observations')
    if 'expected_sessions' in metadata:
        expected=pd.DatetimeIndex(pd.to_datetime(metadata['expected_sessions'],errors='raise'))
        if expected.has_duplicates or not expected.is_monotonic_increasing or not expected.equals(frame.index):
            raise ValueError('Expected sessions do not exactly match return dates')
    else:
        gaps=frame.index.to_series().diff().dt.days.dropna()
        # shortcut: conservative sparse-data screen, replace with an attributed session grid for action.
        if gaps.max()>7 or (gaps>3).mean()>.2:
            raise ValueError('Sparse dates cannot support claimed daily returns')
    frame=frame.astype(float)
    if not np.isfinite(frame).all().all() or (frame < -1).any().any():
        raise ValueError('Missing, nonfinite or impossible simple returns')
    if (frame.std()==0).any() or (frame.eq(0).rolling(6).sum()==6).any().any():
        raise ValueError('Constant or stale return series')
    if pd.Timestamp(metadata['coverage_start'])!=frame.index[0] or pd.Timestamp(metadata['coverage_end'])!=frame.index[-1]:
        raise ValueError('Provenance coverage mismatch')
    return frame if symbols is None else frame.loc[:,symbols]


def read_returns(path, metadata_path, symbols=None):
    with open(path,newline='') as stream:
        header=next(csv.reader(stream),[])
    if len(header)!=len(set(header)):
        raise ValueError('Raw return CSV has duplicate columns')
    frame=pd.read_csv(path,index_col=0)
    return validate_returns(frame,json.loads(Path(metadata_path).read_text()),symbols)

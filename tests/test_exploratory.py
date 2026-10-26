import numpy as np
import pandas as pd
import pytest
from portfolio_engine.exploratory import make_portfolios,replay_account,price_returns,read_price_series


def training():
    rng=np.random.default_rng(8)
    return pd.DataFrame(rng.normal(0,.01,(530,23)),index=pd.bdate_range('2020-01-01',periods=530),columns=[f'A{i}' for i in range(23)])


def test_sampling_exact_matched_and_training_only():
    frame=training();a=make_portfolios(frame.iloc[:504]);b=make_portfolios(frame.iloc[:504])
    assert a==b and len(a['portfolios'])==250
    assert a['scenario_seed']!=42
    assert all(sum(x['group']==g for x in a['portfolios'])==50 for g in a['groups'])
    for p in a['portfolios']:
        assert 5<=len(p['symbols'])<=10
        assert 0<=p['weights'][-1]<=.1 and min(p['weights'])>=0 and max(p['weights'][:-1])<=.6
        assert sum(p['weights'])==pytest.approx(1)
    changed=frame.copy();changed.iloc[504:]=100
    assert make_portfolios(changed.iloc[:504])==a
    with pytest.raises(ValueError): make_portfolios(frame.iloc[:503])


def test_price_unit_and_no_missing_zero(tmp_path):
    dates=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-06'])
    frame=pd.DataFrame({'A':[100,110,99]},index=dates)
    assert price_returns(frame)['A'].tolist()==pytest.approx([.1,-.1])
    with pytest.raises(ValueError): price_returns(frame.assign(A=[100,np.nan,99]))
    path=tmp_path/'A.jsonl';path.write_text('\n'.join('{"session_date":"'+str(d.date())+'","source":"alpaca","feed":"iex","price_basis":"RAW","adjustment":"raw","close":100,"vendor_adjusted_close":100,"div_cash":0,"split_factor":1}' for d in dates[:2]))
    with pytest.raises(ValueError,match='session'): read_price_series(path,dates,'alpaca')


def test_replay_chronology_cost_drift_and_failures(monkeypatch):
    import portfolio_engine.exploratory as ex
    frame=training();definition=make_portfolios(frame.iloc[:504])['portfolios'][0]
    original=ex.optimize; calls=[]
    def capture(R,mean,current,*args,**kwargs):
        calls.append(current.copy());return original(R,mean,current,*args,**kwargs)
    monkeypatch.setattr(ex,'optimize',capture)
    result=replay_account(frame,definition,scenario_seed=123,max_folds=1,scenario_count=400)
    assert result['status']=='HISTORICAL_RETURN_REPLAY' and result['decision']=='NO_TRADE'
    assert len(result['strategies'])==7
    assert result['folds'][0]['train_end']<result['folds'][0]['test_start']
    initial=np.array(definition['weights']);selected=frame[definition['symbols']].iloc[504:].to_numpy()
    expected=100000*np.r_[np.cumprod(1+selected,axis=0)[-1],1.]@initial
    assert result['strategies']['buy_hold']['daily']['nav_usd'][-1]==pytest.approx(expected)
    eq=result['strategies']['equal_weight'];assert eq['folds'][0]['cost_usd']>0
    assert eq['daily']['cost_fraction'][0]>0 and sum(eq['daily']['cost_fraction'][1:])==0
    assert all(s['initial_nav_usd']==100000 for s in result['strategies'].values())
    def fail(*args,**kwargs): raise ValueError('test solver failure')
    monkeypatch.setattr(ex,'optimize',fail)
    broken=replay_account(frame,definition,scenario_seed=123,max_folds=1,scenario_count=400)
    assert broken['strategies']['bl_cvar']['failures']
    assert len(broken['strategies']['bl_cvar']['daily']['net_return'])==26


def test_action_and_identity_screen(tmp_path):
    import json
    dates=pd.to_datetime(['2020-01-02','2020-01-03'])
    rows=[{'session_date':str(d.date()),'source':'tiingo','symbol':'A','vendor_adjusted_close':100,'div_cash':0,'split_factor':1} for d in dates]
    path=tmp_path/'A.jsonl'
    def save(): path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    save(); assert len(read_price_series(path,dates,'tiingo','A'))==2
    rows[0]['split_factor']=2;save()
    with pytest.raises(ValueError,match='corporate action'): read_price_series(path,dates,'tiingo','A')
    rows[0]['split_factor']=1;rows[1]['symbol']='B';save()
    with pytest.raises(ValueError,match='symbol'): read_price_series(path,dates,'tiingo','A')


def test_future_test_changes_never_change_first_allocation_and_risk_reference():
    from portfolio_engine.models import empirical_es
    frame=training();definition=make_portfolios(frame.iloc[:504])['portfolios'][0]; cache={}
    a=replay_account(frame,definition,scenario_seed=123,fit_cache=cache,max_folds=1,scenario_count=400)
    changed=frame.copy();changed.iloc[504:]*=2
    b=replay_account(changed,definition,scenario_seed=123,fit_cache=cache,max_folds=1,scenario_count=400)
    assert len(cache)==1
    for name in a['strategies']:
        assert a['strategies'][name]['folds'][0]['pre_nav_fractions']==b['strategies'][name]['folds'][0]['pre_nav_fractions']
    fit=next(iter(cache.values())); strategy=a['strategies']['bl_cvar']; f=strategy['folds'][0];x=np.array(f['pre_nav_fractions']); cost=f['cost_usd']/100000
    assert strategy['daily']['forecast_daily_es'][0]==pytest.approx(empirical_es(cost-fit['scenarios']@x))
    realized=frame[definition['symbols']].iloc[504].to_numpy()
    assert strategy['daily']['net_return'][0]==pytest.approx(realized@x[:-1]-cost)
    assert strategy['daily']['nav_usd'][0]==pytest.approx(100000*(1+strategy['daily']['net_return'][0]))

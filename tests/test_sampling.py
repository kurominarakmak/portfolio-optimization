import copy
import numpy as np
from portfolio_engine.sampling import sample_portfolios

def universe():
    return {'provider':'TEST external attestation fixture','permitted_usage':'unit tests only','source_hashes':{'fixture':'a'*64},'verification':{'available_at':'2020-01-01T00:00:00Z','source':'test verifier','identity':True,'tradability':True,'point_in_time':True,'corporate_actions':True,'delistings':True,'session_calendar':True,'adjustment_policy':True,'usage_rights':True,'daily_usd_total_returns':True},'assets':[{'symbol':f'A{i}','permanent_id':f'ID{i}','currency':'USD','market':'US','eligible_from':'2010-01-01','known_at':'2010-01-01T00:00:00Z','history_observations_asof':504,'history_asof':'2020-01-01T00:00:00Z','sector':'one' if i<5 else 'two','asset_type':'ETF' if i%2 else 'STOCK'} for i in range(12)]}

def test_250_deterministic_and_constraints():
    u=universe(); original=copy.deepcopy(u)
    a=sample_portfolios(u,'2020-01-02T00:00:00Z'); b=sample_portfolios(u,'2020-01-02T00:00:00Z')
    assert a==b
    assert u==original
    assert a['status']=='READY'
    assert len(a['portfolios'])==250
    assert a['scenario_seed']!=a['holdings_seed']
    for p in a['portfolios']:
        assert len(p['symbols'])>=5
        assert np.isclose(sum(p['weights'])+p['cash_weight'],1)
        assert min(p['weights'])>=0 and max(p['weights'])<=.6
        assert 0<=p['cash_weight']<=.1
    assert all(sum(p['group']==g for p in a['portfolios'])==50 for g in a['groups'])

def test_eligibility_blocked_and_fallbacks():
    u=universe();u['verification']['corporate_actions']=False
    assert sample_portfolios(u,'2020-01-02T00:00:00Z')['status']=='BLOCKED'
    u=universe();u['assets']=u['assets'][:2]
    for a in u['assets']: a.pop('sector');a.pop('asset_type')
    result=sample_portfolios(u,'2020-01-02T00:00:00Z')
    assert len(result['portfolios'])==250
    assert len(result['fallbacks'])==2
    u['assets'][0]['known_at']='2021-01-01T00:00:00Z'
    assert sample_portfolios(u,'2020-01-02T00:00:00Z')['status']=='BLOCKED'

def test_sampler_never_accepts_future_history_or_future_verification():
    for field in ('known_at','history_asof'):
        u=universe()
        for a in u['assets']: a[field]='2021-01-01T00:00:00Z'
        assert sample_portfolios(u,'2020-01-02T00:00:00Z')['status']=='BLOCKED'
    u=universe();u['verification']['available_at']='2021-01-01T00:00:00Z'
    assert sample_portfolios(u,'2020-01-02T00:00:00Z')['status']=='BLOCKED'


def test_save_definitions_is_exclusive_and_attempt_limit_blocks(tmp_path):
    import json
    import pytest
    from portfolio_engine.sampling import save_definitions
    result=sample_portfolios(universe(),'2020-01-02T00:00:00Z')
    path=tmp_path/'definitions.json';save_definitions(result,path)
    assert json.loads(path.read_text())['definitions_sha256']==result['definitions_sha256']
    with pytest.raises(FileExistsError): save_definitions(result,path)
    u=universe();u['assets']=u['assets'][:2]
    blocked=sample_portfolios(u,'2020-01-02T00:00:00Z',max_attempts=1)
    assert blocked['status']=='BLOCKED' and blocked['portfolios']==[]


def test_future_outcomes_do_not_affect_definitions_and_invalid_assets_excluded():
    u=universe(); a=sample_portfolios(u,'2020-01-02T00:00:00Z')
    u['unused_future_returns']={'A0':[100,-1]}
    b=sample_portfolios(u,'2020-01-02T00:00:00Z')
    assert a['portfolios']==b['portfolios']
    assert a['definitions_sha256']==b['definitions_sha256']
    u['assets'][0]['currency']='EUR'
    u['assets'][1]['asset_type']='OPTION'
    c=sample_portfolios(u,'2020-01-02T00:00:00Z')
    assert 'A0' not in c['eligible_symbols'] and 'A1' not in c['eligible_symbols']
    assert len(c['exclusions'])==2

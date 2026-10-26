import numpy as np
import pytest
from portfolio_engine.optimize import Constraints, optimize, preview_shares, decide

def test_self_finance_and_infeasible():
    rng=np.random.default_rng(2); r=np.c_[rng.normal(.002,.01,(500,2)),np.zeros(500)]
    w=np.array([0.,0.,1.]); c=Constraints(max_weight=1.,min_cash=.1,cost_rate=.01)
    got=optimize(r,np.array([.002,.002,0]),w,np.diag([.0001,.0001,0]),c)
    assert abs(got['pre_nav_fractions'].sum()+got['cost']-1)<1e-6
    assert got['weights'][-1]>=.1-1e-6
    assert got['cost']==pytest.approx(.01*np.abs(got['pre_nav_fractions'][:-1]-w[:-1]).sum(),abs=1e-7)
    with pytest.raises(ValueError): optimize(r,np.zeros(3),w,np.eye(3),Constraints(max_weight=.1,min_weight=.1,min_cash=.9))

def test_no_trade():
    assert decide(1,True,500,500,None)['decision']=='NO_TRADE'
    assert decide(0,True,500,500,{'independent':True,'lower_bound':-.1,'sensitivity_stable':True,'source':'held out'})['decision']=='HOLD'
    assert decide(.1,True,500,500,{'independent':True,'lower_bound':.01,'sensitivity_stable':True,'source':'held out'})['decision']=='REBALANCE'

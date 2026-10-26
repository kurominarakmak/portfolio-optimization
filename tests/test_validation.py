import io
import numpy as np
import pandas as pd
import pytest
from scipy.optimize import linprog
from portfolio_engine.models import psd, scenarios, black_litterman, covariance
from portfolio_engine.optimize import Constraints, optimize, preview_shares, decide
from portfolio_engine.data import read_portfolio,validate_returns
from portfolio_engine.cli import analyze, demo_inputs, write_report

def test_cvar_independent_linear_program():
    rng=np.random.default_rng(12); r=rng.normal([.001,.002],[.01,.02],(100,2)); alpha=.9
    # Independent scipy RU LP in weights, z and excess variables.
    objective=np.r_[0.,0.,1.,np.full(len(r),1/(len(r)*(1-alpha)))]
    A=np.c_[-r,-np.ones(len(r)),-np.eye(len(r))]
    reference=linprog(objective,A_ub=A,b_ub=np.zeros(len(r)),A_eq=[np.r_[1.,1.,0.,np.zeros(len(r))]],b_eq=[1.],bounds=[(0,None),(0,None),(None,None)]+[(0,None)]*len(r),method='highs')
    assert reference.success
    got=optimize(np.c_[r,np.zeros(len(r))],np.zeros(3),np.array([.5,.5,0]),np.diag([.001,.001,0]),Constraints(max_weight=1,max_cash=0,cost_rate=0),alpha,1,'min_cvar')
    assert got['daily_es_net']==pytest.approx(reference.fun,abs=1e-7)

@pytest.mark.parametrize('seed',range(6))
def test_optimizer_residuals_across_inputs(seed):
    rng=np.random.default_rng(seed); r=np.c_[rng.normal(0,.01,(400,3)),np.zeros(400)]
    got=optimize(r,np.zeros(4),np.array([.3,.3,.3,.1]),np.diag([.0001]*3+[0]),Constraints(max_cash=.2,min_cash=.05,max_weight=.5))
    assert got['max_residual']<1e-6
    assert got['weights'].sum()==pytest.approx(1,abs=1e-6)
    assert got['weights'][-1]<=.2+1e-6


def test_reject_materially_non_psd_and_bad_omega():
    with pytest.raises(ValueError): psd([[1,2],[2,1]])
    with pytest.raises(ValueError): black_litterman(np.eye(2),[0,0],P=[[1,0]],Q=[0],omega=[[0]],evidence={'source':'x','as_of':'2020-01-01'},as_of='2020-01-02')
    with pytest.raises(ValueError): scenarios(np.ones((60,2)),[-5,0],np.eye(2),10)


def test_rounding_cash_and_constraint_failure(tmp_path):
    frame,m=demo_inputs(tmp_path)
    portfolio=read_portfolio(tmp_path/'holdings.csv','2026-10-24T00:00:00Z')
    cand={'pre_nav_fractions':np.array([.25,.25,.25,.25])}
    preview=preview_shares(cand,portfolio,Constraints(max_cash=1))
    assert sum(preview['quantity']*100)+preview['cash_usd']+preview['cost_usd']==pytest.approx(10000)
    with pytest.raises(ValueError): preview_shares(cand,portfolio,Constraints(max_cash=.1))


def test_utc_dates_units_and_nav(tmp_path):
    frame,m=demo_inputs(tmp_path)
    with pytest.raises(ValueError): read_portfolio(tmp_path/'holdings.csv','2026-10-24')
    bad=m|{'units':'percent'}
    with pytest.raises(ValueError): validate_returns(frame,bad)
    with pytest.raises(ValueError): validate_returns(frame.iloc[::-1],m)
    text=(tmp_path/'holdings.csv').read_text().replace(',10000',',10001')
    with pytest.raises(ValueError): read_portfolio(io.StringIO(text),'2026-10-24T00:00:00Z')
    with pytest.raises(ValueError): read_portfolio(tmp_path/'holdings.csv','2026-11-24T00:00:00Z')


def test_demo_is_deterministic_and_never_actionable_without_evidence(tmp_path):
    frame,m=demo_inputs(tmp_path); p=read_portfolio(tmp_path/'holdings.csv','2026-10-24T00:00:00Z')
    a=analyze(p,frame,m,scenario_count=400,as_of='2026-10-24T00:00:00Z')
    b=analyze(p,frame,m,scenario_count=400,as_of='2026-10-24T00:00:00Z')
    assert a['decision']=='NO_TRADE'
    assert np.array_equal(a['candidate']['weights'],b['candidate']['weights'])
    assert a['data_kind']=='synthetic'
    write_report(a,tmp_path/'result')
    assert (tmp_path/'result.html').exists()


def test_tail_insufficiency_and_current_violations_cannot_hold():
    e={'independent':True,'source':'heldout','lower_bound':1,'sensitivity_stable':True}
    assert decide(1,True,100,1000,e)['decision']=='NO_TRADE'
    assert decide(0,False,500,1000,e)['decision']!='HOLD'

def test_solver_boundary_noise_never_poison_next_rebalance():
    rng=np.random.default_rng(1); r=np.c_[rng.normal(0,.01,(400,2)),np.zeros(400)]
    w=np.array([.45,.45,.1]); c=Constraints(max_cash=.1,max_weight=1)
    for _ in range(4):
        fit=optimize(r,np.array([-.01,0,0]),w,np.diag([.0001,.0001,0]),c)
        w=fit['weights']
        assert np.all(w>=0)
        w=w*np.array([1.01,.99,1]); w/=w.sum()

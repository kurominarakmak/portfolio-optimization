import pandas as pd
import pytest
from portfolio_engine.data import read_portfolio, validate_returns

def test_cash_reconciliation(tmp_path):
    p=tmp_path/'p.csv'
    p.write_text('symbol,quantity,price,currency,valuation_timestamp,nav\nAAA,2,10,USD,2026-10-23T20:00:00Z,25\nCASH,5,1,USD,2026-10-23T20:00:00Z,25\n')
    got=read_portfolio(p, '2026-10-24T00:00:00Z')
    assert got['weights'].tolist()==[.8,.2]
    p.write_text(p.read_text().replace('CASH,5','CASH,-5'))
    with pytest.raises(ValueError): read_portfolio(p,'2026-10-24T00:00:00Z')

def test_returns_missing_metadata():
    with pytest.raises(ValueError): validate_returns(pd.DataFrame({'AAA':[.01]*80}),{})

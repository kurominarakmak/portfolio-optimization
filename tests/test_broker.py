import pytest
from portfolio_engine.broker import read_webull, BrokerError
class Response:
    status_code=200
    headers={}
    def __init__(self,data): self.data=data
    def json(self): return self.data
class ReadOnly:
    def get_account_list(self): return Response([{'account_id':'a','account_type':'CASH'}])
    def get_account_balance(self,a): return Response({'total_asset_currency':'USD','total_cash_balance':'5','total_net_liquidation_value':'25','total_market_value':'20','account_currency_assets':[{'currency':'USD'}]})
    def get_account_position(self,a): return Response([{'instrument_type':'EQUITY','currency':'USD','symbol':'AAA','quantity':'2','last_price':'10','cost_price':'9'}])

def test_broker_normalizes_without_order_surface():
    x=read_webull('a','2026-10-24T00:00:00Z','2026-10-23T20:00:00Z',True,ReadOnly())
    assert x['nav']==25
    assert x['weights'].tolist()==[.8,.2]

def test_broken_broker_sanitized():
    class Broken(ReadOnly):
        def get_account_list(self): raise RuntimeError('SECRET')
    with pytest.raises(BrokerError,match='connectivity') as exc: read_webull('a','2026-10-24T00:00:00Z','2026-10-23T20:00:00Z',True,Broken())
    assert 'SECRET' not in str(exc.value)

def test_pagination_rejected():
    class Pages(ReadOnly):
        def get_account_position(self,a): return Response({'data':[],'pagination_key':'more'})
    with pytest.raises(BrokerError): read_webull('a','2026-10-24T00:00:00Z','2026-10-23T20:00:00Z',True,Pages())

def test_eligibility_required():
    with pytest.raises(BrokerError): read_webull('a','2026-10-24T00:00:00Z','2026-10-23T20:00:00Z')

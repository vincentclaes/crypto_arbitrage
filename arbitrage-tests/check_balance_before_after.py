import unittest

from mock import MagicMock

from engines.triangular_arbitrage import CryptoEngineTriArbitrage



class TestCheckBidAskRoute(unittest.TestCase):
    def test_check_balance_before_and_after(self):

        config = {
            "exchange": "bitfinex",
            "keyFile": "keys/bitfinex.key_sample",
            "tickerPairA": "ETH-BTC",
            "tickerPairB": "NEO-ETH",
            "tickerPairC": "NEO-BTC",
            "tickerA": "BTC",
            "tickerB": "ETH",
            "tickerC": "NEO",
            "minimum_amount": [0.02, 0.2, 0.2]

        }

        orderbook_object = {'status': 2, 'orderInfo':
            [{'tickerPair': u'ETH-BTC', 'action': 'ask', 'price': 0.10741, 'amount': '0.02953368539195560735'},
             {'tickerPair': u'NEO-ETH', 'action': 'ask', 'price': 0.12714, 'amount': '0.27508471802000000750'},
             {'tickerPair': u'NEO-BTC', 'action': 'bid', 'price': 0.013629, 'amount': '2.16792079405602855502'},
             ]}

        balance = {u'NEO': 2.20618882, u'ETH': 0.27563599, u'BTC': 0.05124354}
        prices = [9281.0, 987.98, 128.31]
        orderbook = orderbook_object.get('orderInfo')

        engine = CryptoEngineTriArbitrage(config, True)
        engine.getMaxAmount()

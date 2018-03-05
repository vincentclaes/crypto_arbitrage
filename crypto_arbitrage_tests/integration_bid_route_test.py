import unittest

import mock
from mock import MagicMock

from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class IntegrationBidRouteTest(unittest.TestCase):
    """
    this tests has open orders and calculates arbitrage possibilities.
    """
    @classmethod
    def setUpClass(cls):

        eth_btc = {
            "ask": {
                "amount": 0.1731355,
                "price": 0.089075
            },
            "bid": {
                "amount": 0.7781,
                "price": 0.099018
            }
        }

        neo_eth = {
            "ask": {
                "amount": 1.71827652,
                "price": 0.104482
            },
            "bid": {
                "amount": 0.05,
                "price": 0.10434
            }
        }

        neo_btc = {
            "ask": {
                "amount": 34.7,
                "price": 0.010307
            },
            "bid": {
                "amount": 8.3993176,
                "price": 0.010301
            }
        }

        m1 = MagicMock()
        m1.parsed = eth_btc
        m2 = MagicMock()
        m2.parsed = neo_eth
        m3 = MagicMock()
        m3.parsed = neo_btc

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

        cls.exception = None

        try:
            engine = CryptoEngineTriArbitrage(config, True)
            engine.hasOpenOrder = False
            with mock.patch.object(CryptoEngineTriArbitrage, 'check_balance') as m_balance:
                with mock.patch.object(CryptoEngineTriArbitrage, 'get_last_prices') as m_last_price:
                    with mock.patch.object(CryptoEngineTriArbitrage, 'get_orderbook') as m_orderbook:
                        with mock.patch.object(CryptoEngineTriArbitrage, 'check_openOrder') as m_open_order:
                            with mock.patch.object(CryptoEngineTriArbitrage, 'place_order') as m_place_order:
                                m_balance.return_value = {u'NEO': 10, u'ETH': 1, u'BTC': 1}
                                m_last_price.return_value = {'BTC': 10000, 'ETH': 1000, 'NEO': 100}
                                engine.engine.last_prices = {'BTC': 10000, 'ETH': 1000, 'NEO': 100}
                                m_orderbook.return_value = [m1, m2, m3]
                                engine._run()
        except Exception as e:
            cls.exception = e

    def test_did_not_throw_exception(self):
        self.assertIsNone(self.exception)

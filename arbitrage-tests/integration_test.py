import unittest
import sys
from mock import MagicMock
import mock
from engines.triangular_arbitrage import CryptoEngineTriArbitrage
from engines.exchanges.bitfinex import ExchangeEngine


def nearly_equal(a, b, sig_fig=5):
    return (a == b or
            int(a * 10 ** sig_fig) == int(b * 10 ** sig_fig)
            )


class IntegrationTestMakingProfit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        neo_eth = {
            "ask": {
                "amount": 1.71827652,
                "price": 0.104482
            },
            "bid": {
                "amount": 5.43e-05,
                "price": 0.10434
            }
        }

        eth_btc = {
            "ask": {
                "amount": 0.04731355,
                "price": 0.099075
            },
            "bid": {
                "amount": 0.7781,
                "price": 0.099018
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

        prices = [13838.0, 1307.5, 188.3]
        m1 = MagicMock()
        m1.parsed = eth_btc
        m2 = MagicMock()
        m2.parsed = neo_eth
        m3 = MagicMock()
        m3.parsed = neo_btc

        #from engines.triangular_arbitrage import CryptoEngineTriArbitrage

        #engine = CryptoEngineTriArbitrage(config['triangular'], isMockMode)

        bid_result = CryptoEngineTriArbitrage.bid_route([m1, m2, m3])
        ask_result = CryptoEngineTriArbitrage.ask_route([m1, m2, m3])

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

        engine = CryptoEngineTriArbitrage(config, True)
        engine.hasOpenOrder = False
        with mock.patch.object(CryptoEngineTriArbitrage, 'check_balance') as m_balance:
            with mock.patch.object(CryptoEngineTriArbitrage, 'get_last_prices') as m_last_price:
                with mock.patch.object(CryptoEngineTriArbitrage, 'get_orderbook') as m_orderbook:
                    with mock.patch.object(CryptoEngineTriArbitrage, 'check_openOrder') as m_open_order:

                        m_balance.return_value = {u'NEO': 20.99679953, u'ETH': 0.00737089, u'BTC': 0.01813783}
                        m_last_price.return_value = [11845.0, 1228.3, 150.0]
                        m_orderbook.return_value = [m1, m2, m3]
                        engine._run()

    def test_did_not_throw_exception(self):
        pass


class IntegrationTestWithRealValues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        neo_eth = {"ask": {"price": 0.13454, "amount": 20.0}, "bid": {"price": 0.13429, "amount": 0.4309342}}

        eth_btc = {"ask": {"price": 0.014224, "amount": 20.0}, "bid": {"price": 0.014215, "amount": 3.3902}}

        neo_btc = {"ask": {"price": 0.10564, "amount": 0.774645}, "bid": {"price": 0.10557, "amount": 0.14249272}}


        prices = [13838.0, 1307.5, 188.3]
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

        engine = CryptoEngineTriArbitrage(config, True)
        engine.hasOpenOrder = False
        setattr(engine.engine, 'last_prices', {u'NEO': 114.72, u'ETH': 888.5, u'BTC': 8630.0})
        with mock.patch.object(CryptoEngineTriArbitrage, 'check_balance') as m_balance:
            with mock.patch.object(CryptoEngineTriArbitrage, 'get_last_prices') as m_last_price:
                with mock.patch.object(CryptoEngineTriArbitrage, 'get_orderbook') as m_orderbook:
                    with mock.patch.object(CryptoEngineTriArbitrage, 'check_openOrder') as m_open_order:

                        m_balance.return_value = {u'NEO': 20.99679953, u'ETH': 0.00737089, u'BTC': 0.01813783}
                        m_last_price.return_value = [11845.0, 1228.3, 150.0]
                        m_orderbook.return_value = [m1, m2, m3]
                        engine._run()

                        engine.calculate_wallet_difference()

    def test_did_not_throw_exception(self):
        pass
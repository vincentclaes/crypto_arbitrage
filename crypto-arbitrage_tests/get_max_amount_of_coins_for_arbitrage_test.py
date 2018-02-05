import unittest

from mock import MagicMock

from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class TestGetMaxAmountOfCoinsForArbitrage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

        orderbooks = [
            {'ask': {'price': 0.10575, 'amount': 3.5}, 'bid': {'price': 0.10566, 'amount': 6.6259513}},
            {'ask': {'price': 0.13072, 'amount': 0.17325513}, 'bid': {'price': 0.1303, 'amount': 1.6159}},
            {'ask': {'price': 0.013831, 'amount': 35.98939827}, 'bid': {'price': 0.013824, 'amount': 40.29722331}}
        ]
        order_book_list = []
        for i, obj_ in enumerate(orderbooks):
            class orderbook_object: pass

            setattr(orderbook_object, 'parsed', obj_)
            order_book_list.append(orderbook_object)

        current_balance = {u'NEO': 2.20618882, u'ETH': 0.27563599, u'BTC': 0.05124354}
        prices = [9333.2, 986.66, 129.3]
        last_prices = {'BTC': 9333.2, 'ETH': 986.66, 'NEO': 129.3}
        engine = CryptoEngineTriArbitrage(config, True)
        engine.engine.last_prices = last_prices
        engine.engine.balance = current_balance
        engine.engine.exchange = config
        cls.max_amounts_result = engine.getMaxAmount(prices, order_book_list, 1)

    def test_verify_max_amounts(self):
        self.assertListEqual(self.max_amounts_result,
                             [0.01827904885276951, 0.17290861974000002, 1.3194278325805755])

import unittest

from mock import MagicMock

from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class PickRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = {
            "exchange": "bitfinex",
            "keyFile": "../keys/bitfinex.key_sample",
            "tickerPairA": "ETH-BTC",
            "tickerPairB": "NEO-ETH",
            "tickerPairC": "NEO-BTC",
            "tickerA": "BTC",
            "tickerB": "ETH",
            "tickerC": "NEO",
            "minimum_amount": [0.02, 0.2, 0.2]

        }

        cls.engine = CryptoEngineTriArbitrage(config, True)



    def test_verify_picked_route(self):
        picked_route = self.engine.pick_route(1.01, 1.02, 9800)
        self.assertEqual(picked_route, 2)
        picked_route = self.engine.pick_route(1.02, 1.01, 9800)
        self.assertEqual(picked_route, 1)
        picked_route = self.engine.pick_route(1.01, 0.01, 9800)
        self.assertEqual(picked_route, 1)
        picked_route = self.engine.pick_route(0.01, 0.01, 9800)
        self.assertEqual(picked_route, 0)
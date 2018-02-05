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

        cls.engine = CryptoEngineTriArbitrage(config, True)



    def test_verify_picked_route(self):
        picked_route = self.engine.pick_route(1.01,1.02)
        self.assertListEqual(self.max_amounts_result,
                             [0.01827904885276951, 0.17290861974000002, 1.3194278325805755])

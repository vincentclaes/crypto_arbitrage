import unittest
from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class CalculateProfitTest(unittest.TestCase):
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
            "minimum_amount": {"ETH-BTC": 0.02, "NEO-ETH": 0.2, "NEO-BTC": 0.2},

        }

        cls.engine = CryptoEngineTriArbitrage(config, True)

    def test_verify_calculate_fee_we_make_loss(self):
        self.assertEqual(self.engine._calculate_profit(1, 0.002),  -0.005988007999999989)

    def test_verify_calculate_fee_we_make_profit(self):
        self.assertEqual(self.engine._calculate_profit(1.1, 0.002), 0.09341319120000002)

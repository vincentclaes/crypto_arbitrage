import unittest
from engines.triangular_arbitrage import CryptoEngineTriArbitrage

def nearly_equal(a, b, sig_fig=5):
    return (a == b or
            int(a * 10 ** sig_fig) == int(b * 10 ** sig_fig)
            )


class CalculateFeeTest(unittest.TestCase):
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
        cls.maxAmounts = [0.083825189648, 0.8382518964799999, 8.3825189648]
        cls.last_prices = {'NEO': 100, 'ETH': 1000, 'BTC': 10000}
        cls.main_currency_price = 10000

    def test_verify_calculate_fee(self):
        fee_result = self.engine._calculate_fee(self.maxAmounts, self.last_prices, self.main_currency_price)
        self.assertTrue(nearly_equal(fee_result, 0.000502951137888))
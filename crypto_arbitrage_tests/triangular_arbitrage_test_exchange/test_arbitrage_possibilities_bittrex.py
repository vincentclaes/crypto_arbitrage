import unittest

from crypto_arbitrage_tests.triangular_arbitrage_test_exchange.base_arbitrage_for_exchange import \
    BaseArbitragePossibilitiesForExchange


class ArbitragePossibilitiesForCoinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        cls.exception = None

        try:
            BaseArbitragePossibilitiesForExchange.run_for_coin_on_exchange("AVT", "bitfinex")
        except Exception as e:
            cls.exception = e

    def test_did_not_throw_exception(self):
        self.assertIsNone(self.exception)

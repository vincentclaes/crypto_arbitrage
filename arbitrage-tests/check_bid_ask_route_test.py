import unittest

from mock import MagicMock

from engines.triangular_arbitrage import CryptoEngineTriArbitrage


def nearly_equal(a, b, sig_fig=5):
    return (a == b or
            int(a * 10 ** sig_fig) == int(b * 10 ** sig_fig)
            )


class TestCheckBidAskRoute(unittest.TestCase):
    def test_something(self):
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
        bid_result = CryptoEngineTriArbitrage.bid_route([m1, m2, m3])
        ask_result = CryptoEngineTriArbitrage.ask_route([m1, m2, m3])

        self.assertTrue(nearly_equal(bid_result, 0.9951162744))
        self.assertTrue(nearly_equal(ask_result, 1.00238072378))

        picked_ask_route = CryptoEngineTriArbitrage.pick_route(bid_result, ask_result, prices)
        self.assertEqual(picked_ask_route, 2)

        picked_bid_route = CryptoEngineTriArbitrage.pick_route(1.2, 0.8, prices)
        self.assertEqual(picked_bid_route, 1)

        picked_no_route_route = CryptoEngineTriArbitrage.pick_route(1, 1, prices)
        self.assertEqual(picked_no_route_route, 0)

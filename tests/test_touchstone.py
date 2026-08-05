import tempfile
import unittest
from pathlib import Path

from hfss_automation.touchstone import read_touchstone


class TouchstoneTests(unittest.TestCase):
    def test_reads_two_port_ma_in_standard_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.s2p"
            path.write_text(
                "# GHz S MA R 50\n"
                "1.0  1 0  0.5 0  0.25 180  0.1 0\n",
                encoding="utf-8",
            )
            data = read_touchstone(path)

            self.assertEqual(data.ports, 2)
            self.assertEqual(data.frequency_hz, (1e9,))
            self.assertAlmostEqual(abs(data.s(1, 1)[0]), 1.0)
            self.assertAlmostEqual(abs(data.s(2, 1)[0]), 0.5)
            self.assertAlmostEqual(data.s(1, 2)[0].real, -0.25)
            self.assertAlmostEqual(abs(data.s(2, 2)[0]), 0.1)

    def test_reads_wrapped_three_port_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.s3p"
            path.write_text(
                "# MHz S RI R 75\n"
                "100  1 0  2 0  3 0\n"
                "     4 0  5 0  6 0\n"
                "     7 0  8 0  9 0\n",
                encoding="utf-8",
            )
            data = read_touchstone(path)

            self.assertEqual(data.reference_ohm, 75.0)
            self.assertEqual(data.frequency_hz, (100e6,))
            self.assertEqual(data.s(3, 1)[0], 3 + 0j)
            self.assertEqual(data.s(1, 2)[0], 4 + 0j)
            self.assertEqual(data.s(3, 3)[0], 9 + 0j)

    def test_rejects_incomplete_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.s2p"
            path.write_text("# GHz S MA R 50\n1.0 1 0\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_touchstone(path)


if __name__ == "__main__":
    unittest.main()

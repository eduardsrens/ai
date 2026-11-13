import importlib.machinery
import importlib.util
import unittest
from pathlib import Path


_script = Path(__file__).with_name("23_10_py")
_loader = importlib.machinery.SourceFileLoader("intervalu_programma", str(_script))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
_modulis = importlib.util.module_from_spec(_spec)
_loader.exec_module(_modulis)


class IntervaluTesti(unittest.TestCase):
    def test_apvieno_parklajosos_un_ieklautus_intervalus(self):
        self.assertEqual(
            _modulis.apvienot_intervalus([[1, 10], [2, 3], [8, 12]]),
            [[1, 12]],
        )

    def test_apvieno_intervalus_kas_saskaras(self):
        self.assertEqual(
            _modulis.apvienot_intervalus([[1, 3], [3, 5], [7, 8]]),
            [[1, 5], [7, 8]],
        )

    def test_atstaj_neparklajosos_intervalus_atseviski(self):
        self.assertEqual(
            _modulis.apvienot_intervalus([[8, 10], [1, 2], [4, 6]]),
            [[1, 2], [4, 6], [8, 10]],
        )

    def test_atbalsta_negativus_skaitlus_un_apgrieztas_robezas(self):
        self.assertEqual(
            _modulis.apvienot_intervalus([[5, 1], [-4, -2], [-2, 0]]),
            [[-4, 0], [1, 5]],
        )

    def test_nolasa_un_apstrada_excel_tabulu(self):
        rezultats = _modulis.apstradat_tabulu(
            [
                "Nr.\tAnce\tZane",
                "# 1. Non-overlapping\t[1, 4] [5, 9] [12, 13]\t[1,6] [8,10] [14,17]",
                "# 2. Touching edges\t[1, 4] [4, 9]\t[-2, -5] [-2, 6] [6, 10]",
                "# 10. Empty set\t[]\t[]",
            ]
        )
        self.assertEqual(
            rezultats,
            [
                ["Nr.", "Ance", "Zane"],
                ["# 1. Non-overlapping", "[1, 4] [5, 9] [12, 13]", "[1, 6] [8, 10] [14, 17]"],
                ["# 2. Touching edges", "[1, 9]", "[-5, 10]"],
                ["# 10. Empty set", "[]", "[]"],
            ],
        )

    def test_nolasa_negativus_un_apgrieztus_intervalus(self):
        self.assertEqual(
            _modulis.nolasit_intervalus("[-1, -4] [5, 9] [-2, 3]"),
            [[-4, -1], [5, 9], [-2, 3]],
        )

    def test_noraida_nederigu_intervalu(self):
        with self.assertRaisesRegex(ValueError, "invalid text"):
            _modulis.nolasit_intervalus("[1, 4] error")

    def test_noraida_nevienadu_kolonnu_skaitu(self):
        with self.assertRaisesRegex(ValueError, "columns"):
            _modulis.apstradat_tabulu(["Nr.\tAnce\tZane", "1\t[1, 2]"])

    def test_atbalsta_divu_kolonnu_intervalu_tabulu(self):
        rezultats = _modulis.apstradat_tabulu(
            ["Start\tEnd", "1\t3", "2\t6", "8\t10"]
        )
        self.assertEqual(
            rezultats,
            [["Start", "End"], ["1", "6"], ["8", "10"]],
        )


if __name__ == "__main__":
    unittest.main()

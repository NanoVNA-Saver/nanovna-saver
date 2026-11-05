import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from NanoVNASaver.Settings.Bands import BandsModel


class TestBandsModelSetData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication([])

    def setUp(self):
        self.model = BandsModel()
        # Isolate the test from the host's persisted band settings.
        self.model.bands = [["Existing", "100", "200"]]
        self.model.saveSettings = lambda: None

    def _edit(self, row, col, value):
        index = self.model.index(row, col)
        return self.model.setData(
            index, value, QtCore.Qt.ItemDataRole.EditRole
        )

    def _value(self, row, col):
        return self.model.data(
            self.model.index(row, col), QtCore.Qt.ItemDataRole.DisplayRole
        )

    def test_add_row_and_edit_each_column(self):
        # Gherkin steps from issue #856: add a row, type "GMRS" in the
        # Band column, then enter the start frequency.
        self.model.addRow()
        row = self.model.rowCount(None) - 1
        self.assertTrue(self._edit(row, 0, "GMRS"))
        self.assertEqual(self._value(row, 0), "GMRS")
        self.assertTrue(self._edit(row, 1, "468000000"))
        self.assertEqual(self._value(row, 1), "468000000")
        # Entering the start frequency must not overwrite the Band column.
        self.assertEqual(self._value(row, 0), "GMRS")
        self.assertTrue(self._edit(row, 2, "469000000"))
        self.assertEqual(self._value(row, 2), "469000000")
        self.assertEqual(
            list(self.model.bands[row]),
            ["GMRS", "468000000", "469000000"],
        )

    def test_edit_existing_row_columns(self):
        self.assertTrue(self._edit(0, 0, "GMRS"))
        self.assertTrue(self._edit(0, 1, "462562500"))
        self.assertTrue(self._edit(0, 2, "467562500"))
        self.assertEqual(
            list(self.model.bands[0]),
            ["GMRS", "462562500", "467562500"],
        )


if __name__ == "__main__":
    unittest.main()

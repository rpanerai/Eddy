# import re

from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLineEdit, QCheckBox, QSpinBox
)


class ACCapWidget(QWidget):
    def __init__(self, parent=None):
        super(ACCapWidget, self).__init__(parent)

        self._check = QCheckBox()
        self._check.setText("AC ≤")
        # self._check.setStyleSheet(
        #     "QCheckBox:checked{color: black;} QCheckBox:unchecked{color: grey;}"
        # )

        self._spin = QSpinBox()
        self._spin.setRange(1, 99)
        self._spin.setValue(10)
        self._spin.setEnabled(False)
        self._check.toggled.connect(self._spin.setEnabled)

        layout = QHBoxLayout()
        layout.addWidget(self._check)
        layout.addWidget(self._spin)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def SetChecked(self, bool_):
        self._check.setChecked(bool_)

    def IsChecked(self):
        return self._check.isChecked()

    def Value(self):
        return self._spin.value()


class SearchBar(QWidget):
    SearchRequested = Signal(dict)
    StopPressed = Signal()

    def __init__(self, parent=None):
        super(SearchBar, self).__init__(parent)

        self._source = "INSPIRE"

        self._query_edit = QLineEdit()
        self._query_edit.setClearButtonEnabled(True)
        self._query_edit.setPlaceholderText("Type you query here")
        self._query_edit.returnPressed.connect(self._HandleReturnPressed)

        self._kill_button = QPushButton(QIcon.fromTheme("process-stop"), "")
        self._kill_button.setFlat(True)
        self._kill_button.setMaximumSize(31, 31)
        self._kill_button.setEnabled(False)
        self._kill_button.clicked.connect(self.StopPressed)

        self._ac_cap = ACCapWidget()

        layout = QHBoxLayout()
        layout.addWidget(self._kill_button)
        layout.addWidget(self._query_edit)
        layout.addWidget(self._ac_cap)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.setFocusProxy(self._query_edit)

    def SetStopEnabled(self, bool_):
        self._kill_button.setEnabled(bool_)

    def RunSearch(self, search):
        self._source = search["source"]
        self._query_edit.setText(search["query"])
        self._HandleReturnPressed()

    def _HandleSourceChange(self, source):
        if source == self._source:
            return
        self._source = source

        self._ac_cap.SetChecked(False)

        if source == "INSPIRE":
            self._ac_cap.setVisible(True)
        elif source == "arXiv":
            self._ac_cap.setVisible(False)

    def _HandleReturnPressed(self):
        query = " ".join(self._query_edit.text().split())

        if query == "":
            return

        if self._ac_cap.IsChecked():
            query = query + " and ac <= " + str(self._ac_cap.Value())

        self.SearchRequested.emit({"source": self._source, "query": query})


class FilterBar(QLineEdit):
    TextChanged = Signal(list)

    def __init__(self, parent=None):
        super(FilterBar, self).__init__(parent)

        self.setClearButtonEnabled(True)
        self.setPlaceholderText("Filter authors and titles")
        self.textChanged.connect(self._HandleTextChanged)

    def _HandleTextChanged(self, text):
        filter_strings = text.split()
        # The above implements search at the level of individual (space-separated) words.
        # Search with strings enclosed between braces can be introduced with
        #filter_strings = [s.strip('"') for s in re.findall(r'[^\s"]+|"[^"]*"', text)]

        self.TextChanged.emit(filter_strings)

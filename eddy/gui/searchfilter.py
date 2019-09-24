from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit, QCheckBox, QSpinBox


class ACCapWidget(QWidget):
    def __init__(self, parent=None):
        super(ACCapWidget, self).__init__(parent)

        self._check = QCheckBox()
        self._check.setText("AC ≤")
        # self._check.setStyleSheet("QCheckBox:checked{color: black;} QCheckBox:unchecked{color: grey;}")

        self._spin = QSpinBox()
        self._spin.setRange(1, 99)
        self._spin.setValue(10)
        self._check.toggled.connect(self._spin.setEnabled)

        self.SetEnabled(False)

        layout = QHBoxLayout()
        layout.addWidget(self._check)
        layout.addWidget(self._spin)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def SetEnabled(self, bool_):
        self._check.setChecked(bool_)
        self._spin.setEnabled(bool_)

    def IsChecked(self):
        return self._check.isChecked()

    def Value(self):
        return self._spin.value()


class SearchBar(QWidget):
    SearchRequested = Signal(str)
    StopPressed = Signal()

    def __init__(self, parent=None):
        super(SearchBar, self).__init__(parent)

        self._query_edit = QLineEdit()
        self._query_edit.setClearButtonEnabled(True)
        self._query_edit.setPlaceholderText("Type you query here")
        self._query_edit.returnPressed.connect(self._HandleReturnPressed)

        self._kill_button = QPushButton(QIcon.fromTheme("process-stop"), "")
        self._kill_button.setFlat(True)
        self._kill_button.setMaximumSize(31, 31)
        self._kill_button.setEnabled(False)
        self._kill_button.clicked.connect(self._HandleStopPressed)

        self._ac_cap = ACCapWidget()

        layout = QHBoxLayout()
        layout.addWidget(self._kill_button)
        layout.addWidget(self._query_edit)
        layout.addWidget(self._ac_cap)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def EnableStopButton(self):
        self._kill_button.setEnabled(True)

    def DisableStopButton(self):
        self._kill_button.setEnabled(False)

    def _HandleReturnPressed(self):
        search_string = " ".join(self._query_edit.text().split())
        if self._ac_cap.IsChecked():
            search_string = search_string + " and ac <= " + str(self._ac_cap.Value())
        self.SearchRequested.emit(search_string)

    def _HandleStopPressed(self):
        self.StopPressed.emit()


class FilterBar(QLineEdit):
    TextChanged = Signal(str)

    def __init__(self, parent=None):
        super(FilterBar, self).__init__(parent)

        self.setClearButtonEnabled(True)
        self.setPlaceholderText("Filter titles")
        self.textChanged.connect(self.TextChanged)

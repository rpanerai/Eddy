from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit


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

        layout = QHBoxLayout()
        layout.addWidget(self._kill_button)
        layout.addWidget(self._query_edit)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def EnableStopButton(self):
        self._kill_button.setEnabled(True)

    def DisableStopButton(self):
        self._kill_button.setEnabled(False)

    def _HandleReturnPressed(self):
        search_string = " ".join(self._query_edit.text().split())
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

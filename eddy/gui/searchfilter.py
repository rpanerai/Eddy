# import re

from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QWidget, QHBoxLayout, QToolButton, QLineEdit

from eddy.icons import icons

class SearchBar(QWidget):
    QueryLaunched = Signal(str)
    StopPressed = Signal()

    def __init__(self, parent=None):
        super(SearchBar, self).__init__(parent)

        self._query_edit = QLineEdit()
        self._query_edit.setClearButtonEnabled(True)
        self._query_edit.setPlaceholderText("Type you query here")
        self._query_edit.returnPressed.connect(self._HandleReturnPressed)
        self._query_edit.addAction(QIcon(icons.SEARCH), QLineEdit.LeadingPosition)

        self._kill_button = QToolButton()
        self._kill_button.setIcon(QIcon(icons.STOP))
        self._kill_button.setAutoRaise(True)
        self._kill_button.setMinimumSize(31, 31)
        self._kill_button.setEnabled(False)
        self._kill_button.clicked.connect(self.StopPressed)

        layout = QHBoxLayout()
        layout.addWidget(self._kill_button)
        layout.addWidget(self._query_edit)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.setFocusProxy(self._query_edit)

    def Clear(self):
        self._query_edit.clear()

    def SetStopEnabled(self, bool_):
        self._kill_button.setEnabled(bool_)

    def SetQueryEditEnabled(self, bool_):
        self._query_edit.setEnabled(bool_)

    def SetQuery(self, query):
        self._query_edit.setText(query)

    def LaunchQuery(self, query):
        self._query_edit.setText(query)
        self._HandleReturnPressed()

    def _HandleReturnPressed(self):
        query = " ".join(self._query_edit.text().split())

        if query == "":
            return

        self.QueryLaunched.emit(query)


class FilterBar(QLineEdit):
    TextChanged = Signal(list)

    def __init__(self, parent=None):
        super(FilterBar, self).__init__(parent)

        self.setClearButtonEnabled(True)
        self.setPlaceholderText("Filter authors and titles")
        self.textChanged.connect(self._HandleTextChanged)
        self.addAction(QIcon(icons.FILTER), QLineEdit.LeadingPosition)

    def _HandleTextChanged(self, text):
        filter_strings = text.split()
        # The above implements search at the level of individual (space-separated) words.
        # Search with strings enclosed between braces can be introduced with
        #filter_strings = [s.strip('"') for s in re.findall(r'[^\s"]+|"[^"]*"', text)]

        self.TextChanged.emit(filter_strings)

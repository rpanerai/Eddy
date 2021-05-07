from PySide2.QtCore import Qt
from PySide2.QtGui import QIcon, QFont
from PySide2.QtWidgets import QWidget, QPlainTextEdit, QToolButton, QHBoxLayout, QVBoxLayout

from eddy.icons import icons
from eddy.network.fetcher import Fetcher
from eddy.network.inspire import InspireBibTeXPlugin
from eddy.network.doi import DOIBibTeXPlugin


class BibTeXWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._source = None
        self._table = None
        self._id = -1
        self._inspire_id = None
        self._doi = None
        self._bibtex_string = ""

        self._fetcher = Fetcher()
        self._fetcher.BatchReady.connect(self._HandleBatchReady)
        self._fetcher.FetchingFinished.connect(self._HandleFetchingCompleted)

        self._text_edit = QPlainTextEdit()
        font = QFont("Monospace")
        self._text_edit.setFont(font)
        self._text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard |
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._text_edit.setEnabled(False)

        self._dowload_inspire = QToolButton()
        self._dowload_inspire.setIcon(QIcon(icons.INSPIRE))
        self._dowload_inspire.clicked.connect(self._FetchINSPIRE)
        self._dowload_inspire.setEnabled(False)

        self._dowload_doi = QToolButton()
        self._dowload_doi.setIcon(QIcon(icons.DOI))
        self._dowload_doi.clicked.connect(self._FetchDOI)
        self._dowload_doi.setEnabled(False)

        self._SetupUI()

    def _SetupUI(self):
        tool_widget = QWidget()
        tool_layout = QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.addWidget(self._dowload_inspire)
        tool_layout.addWidget(self._dowload_doi)
        tool_layout.addStretch(1)
        tool_widget.setLayout(tool_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text_edit)
        layout.addWidget(tool_widget)
        self.setLayout(layout)

    def SetTable(self, database_table):
        if self._table == database_table:
            return

        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)

    def Clear(self):
        self._text_edit.clear()
        self._text_edit.setEnabled(False)
        self._dowload_inspire.setEnabled(False)
        self._dowload_doi.setEnabled(False)

    def DisplayItem(self, id_):
        # NOTE: What if the item gets updated?

        if self._id == id_:
            return

        self._id = id_
        self._fetcher.Stop()
        self.Clear()

        if self._id == -1:
            return

        record = self._table.GetRow(self._id, ("inspire_id", "dois"))
        self._inspire_id = record["inspire_id"]
        self._doi = None if record["dois"] == [] else record["dois"][0]
        has_inspire_id = self._inspire_id is not None
        has_doi = self._doi is not None

        self._text_edit.setEnabled(has_inspire_id | has_doi)
        self._dowload_inspire.setEnabled(has_inspire_id)
        self._dowload_doi.setEnabled(has_doi)

    def _FetchINSPIRE(self):
        self._fetcher.Fetch(InspireBibTeXPlugin, "recid:" + str(self._inspire_id), batch_size=2)

    def _FetchDOI(self):
        self._fetcher.Fetch(DOIBibTeXPlugin, self._doi)

    def _HandleBatchReady(self, batch):
        self._bibtex_string = batch[0]

    def _HandleFetchingCompleted(self, records_number):
        self._text_edit.setPlainText(self._bibtex_string)

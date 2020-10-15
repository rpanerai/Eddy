from datetime import datetime
import os

from PySide2.QtCore import Signal
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout, QScrollArea, QLineEdit, QTextEdit,
    QToolButton, QComboBox, QFileDialog, QMessageBox
)

from eddy.icons import icons


class ItemWidget(QWidget):
    ItemUpdated = Signal()

    _KEYS = (
        "type",
        "title",
        "authors",
        "authors_bais",
        "editors",
        "editors_bais",
        "abstract",
        "date",
        "publication",
        "volume",
        "issue",
        "pages",
        "year",
        "edition",
        "series",
        "publisher",
        "isbns",
        "institution",
        "degree",
        "texkey",
        "inspire_id",
        "arxiv_id",
        "dois",
        "urls",
        "files"
    )

    _FORMAT_TYPE = {
        "A": "Article",
        "B": "Book",
        "C": "Book Chapter",
        "N": "Note",
        "P": "Conference Proceedings",
        "R": "Report",
        "T": "Thesis"
    }

    _FORMAT_FUNCTIONS = {
        "type": lambda x: ItemWidget._FORMAT_TYPE.get(x, ""),
        "authors": "\n".join,
        "editors": "\n".join,
        "isbns": "\n".join,
        # Alternatively one could use
        # lambda x: "\n".join([a.split(",", 1)[0] for a in x])
        "inspire_id": lambda x: str(x) if x is not None else None,
        "year": lambda x: str(x) if x is not None else None,
        "dois": "\n".join,
        "urls": "\n".join,
        "files": "\n".join
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._source = None
        self._table = None
        self._id = -1

        self._updating = False

        self._scroll = QScrollArea()
        # self._scroll.setBackgroundRole(QPalette.Base)
        self._scroll.setWidgetResizable(True)

        self._date = LineEdit()
        min_height = self._date.sizeHint().height()
        self._type = ComboBox()
        self._title = MultiLineTextEdit(min_height)
        self._authors = LineSplitTextEdit(min_height)
        self._editors = LineSplitTextEdit(min_height)
        self._abstract = MultiLineTextEdit(min_height)
        self._publication = LineEdit()
        self._volume = LineEdit()
        self._issue = LineEdit()
        self._pages = LineEdit()
        self._year = LineEdit()
        self._edition = LineEdit()
        self._series = LineEdit()
        self._publisher = LineEdit()
        self._isbns = LineSplitTextEdit(min_height)
        self._institution = LineEdit()
        self._degree = LineEdit()
        self._texkey = LineEdit()
        self._inspire_id = LineEdit()
        self._arxiv_id = LineEdit()
        self._dois = LineSplitTextEdit(min_height)
        self._urls = LineSplitTextEdit(min_height)
        self._files = LineSplitTextEdit(min_height)

        for (k, v) in ItemWidget._FORMAT_TYPE.items():
            self._type.addItem(v, k)
        # self._type.currentIndexChanged[int].connect(self._RefreshTypeFields)

        bold_font = self._title.document().defaultFont()
        bold_font.setBold(True)
        self._title.document().setDefaultFont(bold_font)

        self._fields = {
            "type": self._type,
            "title": self._title,
            "authors": self._authors,
            "editors": self._editors,
            "abstract": self._abstract,
            "date": self._date,
            "publication": self._publication,
            "volume": self._volume,
            "issue": self._issue,
            "pages": self._pages,
            "year": self._year,
            "edition": self._edition,
            "series": self._series,
            "publisher": self._publisher,
            "isbns": self._isbns,
            "institution": self._institution,
            "degree": self._degree,
            "texkey": self._texkey,
            "inspire_id": self._inspire_id,
            "arxiv_id": self._arxiv_id,
            "dois": self._dois,
            "urls": self._urls,
            "files": self._files
        }

        self._details_frame = QGroupBox()
        self._details_layout = QFormLayout()

        self._scroll_widget = QWidget()
        self._SetupScrollUI()
        self._scroll.setWidget(self._scroll_widget)
        self._scroll_widget.hide()

        self._save = QToolButton()
        self._save.setIcon(QIcon(icons.SAVE))
        self._save.clicked.connect(self._Save)
        self._reload = QToolButton()
        self._reload.setIcon(QIcon(icons.RELOAD))
        self._reload.clicked.connect(self.DisplayItem)
        self._file_add = QToolButton()
        self._file_add.setIcon(QIcon(icons.FILE_ADD))
        self._file_add.clicked.connect(self._AddFile)
        self._tool_widget = QWidget()
        self._SetupToolUI()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        layout.addWidget(self._tool_widget)
        self.setLayout(layout)
        self.Clear()

    def _SetupScrollUI(self):
        self._details_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._details_layout.addRow("Journal", self._publication)
        self._details_layout.addRow("Editors", self._editors)
        self._details_layout.addRow("Volume", self._volume)
        self._details_layout.addRow("Issue", self._issue)
        self._details_layout.addRow("Pages", self._pages)
        self._details_layout.addRow("Edition", self._edition)
        self._details_layout.addRow("Series", self._series)
        self._details_layout.addRow("Publisher", self._publisher)
        self._details_layout.addRow("ISBNs", self._isbns)
        self._details_layout.addRow("Institution", self._institution)
        self._details_layout.addRow("Degree", self._degree)
        self._details_layout.addRow("Year", self._year)
        self._details_layout.setVerticalSpacing(0)
        self._details_frame.setLayout(self._details_layout)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.addRow("Type", self._type)
        form_layout.addRow("Title", self._title)
        form_layout.addRow("Authors", self._authors)
        form_layout.addRow("Abstract", self._abstract)
        form_layout.addRow("Date", self._date)
        form_layout.addRow("", self._details_frame)
        form_layout.addRow("BibTeX", self._texkey)
        form_layout.addRow("INSPIRE", self._inspire_id)
        form_layout.addRow("arXiv", self._arxiv_id)
        form_layout.addRow("DOIs", self._dois)
        form_layout.addRow("URLs", self._urls)
        form_layout.addRow("Files", self._files)
        form_layout.setVerticalSpacing(0)
        form = QWidget()
        form.setLayout(form_layout)

        scroll_layout = QVBoxLayout()
        scroll_layout.addWidget(form)
        scroll_layout.addStretch(1)

        self._scroll_widget.setLayout(scroll_layout)

    def _SetupToolUI(self):
        tool_layout = QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.addWidget(self._file_add)
        tool_layout.addStretch(1)
        tool_layout.addWidget(self._reload)
        tool_layout.addWidget(self._save)
        self._tool_widget.setLayout(tool_layout)

        self._reload.setEnabled(False)
        self._save.setEnabled(False)
        self._file_add.setEnabled(False)

        for w in self._fields.values():
            w.Edited.connect(self._EnableRefreshSave)

    # def _RefreshTypeFields(self, index):
    #     pass

    def _EnableRefreshSave(self):
        self._reload.setEnabled(True)
        self._save.setEnabled(True)

    def _Save(self):
        data = {}
        for (k, w) in self._fields.items():
            data[k] = w.Read()

        authors_raw = [" ".join(a.split()) for a in data["authors"]]
        authors = []
        authors_bais = []
        for a in authors_raw:
            (n, b) = ItemWidget._ParseAuthor(a)
            authors.append(n)
            authors_bais.append(b)
        data["authors"] = authors
        data["authors_bais"] = authors_bais

        editors_raw = [" ".join(e.split()) for e in data["editors"]]
        editors = []
        editors_bais = []
        for e in editors_raw:
            (n, b) = ItemWidget._ParseAuthor(e)
            editors.append(n)
            editors_bais.append(b)
        data["editors"] = editors
        data["editors_bais"] = editors_bais

        if data["date"] is not None:
            try:
                data["date"] = ItemWidget._ParseDate(data["date"])
            except:
                del data["date"]

        if data["year"] is not None:
            try:
                data["year"] = datetime.strptime(data["year"], "%Y").strftime("%Y")
            except:
                del data["year"]

        if data["inspire_id"] is not None:
            try:
                data["inspire_id"] = int(data["inspire_id"])
            except:
                del data["inspire_id"]

        self._table.EditRow(self._id, data)

        self.ItemUpdated.emit()

    def _AddFile(self):
        files_dir = self._source.FilesDir()
        if files_dir is None:
            QMessageBox.critical(None, "Error", "Cannot access storage folder.")
            return

        (file_path, _) = QFileDialog.getOpenFileName(
            None, "Open Document", files_dir, "Documents (*.pdf *.djvu)"
        )
        if file_path == "":
            return
        file_name = os.path.basename(file_path)

        try:
            renaming = self._source.SaveFiles((file_path,))
        except:
            QMessageBox.critical(None, "Error", "Error while copying the file.")
        else:
            self._AppendFile(renaming.get(file_name, file_name))

    def _AppendFile(self, file_name):
        data = self._table.GetRow(self._id, ("files",))
        if file_name in data:
            return
        data["files"].append(file_name)

        # Here self._updating is used to prevent calls to DisplayItem()
        # triggered by an Updated() signal emitted by the database.
        self._updating = True
        self._table.EditRow(self._id, data)
        self._updating = False

        self._files.Write(ItemWidget._FORMAT_FUNCTIONS["files"](data["files"]))

    def SetLocalSource(self, source):
        if self._source == source:
            return

        self._source = source
        self._SetTable(source.table)

    def SetTable(self, database_table):
        if self._table == database_table:
            return

        self._source = None
        self._SetTable(database_table)

    def _SetTable(self, database_table):
        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)

        if self._source is None:
            self._files.setEnabled(False)
        else:
            self._files.setEnabled(True)

    def Clear(self):
        self._scroll_widget.hide()
        self._scroll.verticalScrollBar().hide()

    def DisplayItem(self, id_=False):
        if self._updating:
            return

        if id_:
            self._id = id_

        if self._id == -1:
            self.Clear()
            self._reload.setEnabled(False)
            self._save.setEnabled(False)
            self._file_add.setEnabled(False)
            return

        record = self._table.GetRow(self._id, ItemWidget._KEYS)
        authors = []
        for (a, b) in zip(record["authors"], record["authors_bais"]):
            if b is None:
                authors.append(a)
            else:
                authors.append(a + " (" + b + ")")
        record["authors"] = authors
        editors = []
        for (e, b) in zip(record["editors"], record["editors_bais"]):
            if b is None:
                editors.append(e)
            else:
                editors.append(e + " (" + b + ")")
        record["editors"] = editors
        for (k, v) in ItemWidget._FORMAT_FUNCTIONS.items():
            record[k] = v(record[k])

        for (k, w) in self._fields.items():
            w.Write(record[k])

        self._scroll.verticalScrollBar().show()
        self._scroll_widget.show()

        self._reload.setEnabled(False)
        self._save.setEnabled(False)
        if self._source is not None:
            self._file_add.setEnabled(True)

    @staticmethod
    def _ParseAuthor(author):
        split = author.split("(", 1)
        author = split[0].strip()
        if len(split) == 1:
            return(author, None)

        bai = split[1].split(")", 1)
        if len(bai) == 1:
            return(author, None)

        bai = bai[0].replace(" ", "")
        # The sanity check on the BAI could be further refined

        return(author, bai)

    @staticmethod
    def _ParseDate(date_string):
        n_dashes = date_string.count("-")
        if n_dashes == 2:
            return datetime.strptime(date_string, "%Y-%m-%d").strftime("%Y-%m-%d")
        if n_dashes == 1:
            return datetime.strptime(date_string, "%Y-%m").strftime("%Y-%m")
        return datetime.strptime(date_string, "%Y").strftime("%Y")


class ComboBox(QComboBox):
    Edited = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._editing_call = False
        self.currentIndexChanged.connect(self._HandleCurrentIndexChanged)

    def _HandleCurrentIndexChanged(self):
        if not self._editing_call:
            self.Edited.emit()

    def Write(self, text):
        self._editing_call = True
        super().setCurrentText(text)
        self._editing_call = False

    def Read(self):
        return self.currentData()


class LineEdit(QLineEdit):
    Edited = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.textEdited.connect(self.Edited)

    def Write(self, text):
        super().setText(text)

    def Read(self):
        text = self.text().strip()
        return text if text != "" else None


class AdaptiveTextEdit(QTextEdit):
    Edited = Signal()

    def __init__(self, min_height, parent=None):
        # One might want to add a mechanism for setting a max_height.
        super().__init__(parent)
        self.min_height = min_height
        self.setAcceptRichText(False)
        self.setTabChangesFocus(True)
        self.document().documentLayout().documentSizeChanged.connect(self.Resize)

        self._editing_call = False
        self.textChanged.connect(self._HandleTextChanged)

    def focusOutEvent(self, event):
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

        super().focusOutEvent(event)

    def Write(self, text):
        self._editing_call = True
        super().setPlainText(text)
        self._editing_call = False

    def _HandleTextChanged(self):
        if not self._editing_call:
            self.Edited.emit()

    def Resize(self, new_size):
        margins = self.contentsMargins()
        document_size = self.document().documentLayout().documentSize()
        height = document_size.height() + margins.top() + margins.bottom()
        # self.setMinimumHeight(max(height, self.min_height))
        self.setFixedHeight(max(height, self.min_height))


class MultiLineTextEdit(AdaptiveTextEdit):
    def Read(self):
        text = self.toPlainText().strip()
        return text if text != "" else None


class LineSplitTextEdit(AdaptiveTextEdit):
    def Read(self):
        lines = [l.strip() for l in self.toPlainText().splitlines()]
        return [l for l in lines if l != ""]

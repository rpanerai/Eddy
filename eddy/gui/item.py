from datetime import datetime

from PySide2.QtCore import Signal
from PySide2.QtGui import QFont, QIcon
from PySide2.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout, QScrollArea, QLineEdit, QTextEdit,
    QToolButton, QComboBox, QFileDialog
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
        "dois"
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
        "dois": "\n".join
    }

    def __init__(self, parent=None):
        super(ItemWidget, self).__init__(parent)

        self._table = None
        self._id = -1

        self._scroll = QScrollArea()
        # self._scroll.setBackgroundRole(QPalette.Base)
        self._scroll.setWidgetResizable(True)

        self._type = QComboBox()
        for (k, v) in ItemWidget._FORMAT_TYPE.items():
            self._type.addItem(v, k)

        # self._type.currentIndexChanged[int].connect(self._RefreshTypeFields)

        self._details_frame = QGroupBox()
        self._details_layout = QFormLayout()

        self._date = QLineEdit()
        self._publication = QLineEdit()
        self._volume = QLineEdit()
        self._issue = QLineEdit()
        self._pages = QLineEdit()
        self._year = QLineEdit()
        self._edition = QLineEdit()
        self._series = QLineEdit()
        self._publisher = QLineEdit()
        self._institution = QLineEdit()
        self._degree = QLineEdit()
        self._texkey = QLineEdit()
        # copy_texkey = self._texkey.addAction(
        #     QIcon.fromTheme("edit-copy"), QLineEdit.TrailingPosition
        # )
        self._inspire_id = QLineEdit()
        self._arxiv_id = QLineEdit()

        min_height = self._date.sizeHint().height()

        self._title = AdaptiveTextEdit(min_height)
        self._title.setFontWeight(QFont.Bold)
        self._authors = AdaptiveTextEdit(min_height)
        self._editors = AdaptiveTextEdit(min_height)
        self._abstract = AdaptiveTextEdit(min_height)
        self._isbns = AdaptiveTextEdit(min_height)
        self._dois = AdaptiveTextEdit(min_height)

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
        # self._open = QToolButton()
        # self._open.setIcon(QIcon.fromTheme("document-open"))
        # self._open.clicked.connect(self._Open)
        self._tool_widget = QWidget()
        self._SetupToolUI()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        layout.addWidget(self._tool_widget)
        self.setLayout(layout)

    def _SetupScrollUI(self):
        self._details_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._details_layout.addRow("Title", self._publication)
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
        tool_layout.addWidget(self._reload)
        # tool_layout.addWidget(self._open)
        tool_layout.addStretch(1)
        tool_layout.addWidget(self._save)
        self._tool_widget.setLayout(tool_layout)

        self._reload.setEnabled(False)
        self._save.setEnabled(False)

        self._type.currentIndexChanged.connect(self._EnableRefreshSave)
        self._date.textEdited.connect(self._EnableRefreshSave)
        self._publication.textEdited.connect(self._EnableRefreshSave)
        self._volume.textEdited.connect(self._EnableRefreshSave)
        self._issue.textEdited.connect(self._EnableRefreshSave)
        self._pages.textEdited.connect(self._EnableRefreshSave)
        self._year.textEdited.connect(self._EnableRefreshSave)
        self._edition.textEdited.connect(self._EnableRefreshSave)
        self._series.textEdited.connect(self._EnableRefreshSave)
        self._publisher.textEdited.connect(self._EnableRefreshSave)
        self._institution.textEdited.connect(self._EnableRefreshSave)
        self._degree.textEdited.connect(self._EnableRefreshSave)
        self._texkey.textEdited.connect(self._EnableRefreshSave)
        self._inspire_id.textEdited.connect(self._EnableRefreshSave)
        self._arxiv_id.textEdited.connect(self._EnableRefreshSave)
        # Note that the textChanged() signal is triggered even when the text is modified
        # programmatically. This is not problem since we disable the buttons immediately after the
        # QTextEdit widgets are updated in DisplayItem().
        self._title.textChanged.connect(self._EnableRefreshSave)
        self._authors.textChanged.connect(self._EnableRefreshSave)
        self._editors.textChanged.connect(self._EnableRefreshSave)
        self._abstract.textChanged.connect(self._EnableRefreshSave)
        self._isbns.textChanged.connect(self._EnableRefreshSave)
        self._dois.textChanged.connect(self._EnableRefreshSave)

    # def _RefreshTypeFields(self, index):
    #     pass

    def _EnableRefreshSave(self):
        self._reload.setEnabled(True)
        self._save.setEnabled(True)

    def _Save(self):
        data = {}

        data["type"] = self._type.currentData()

        title = self._title.toPlainText().strip()
        data["title"] = title if title != "" else None

        authors_raw = [
            a for a in
            [" ".join(a.split()) for a in self._authors.toPlainText().splitlines()]
            if a != ""
        ]
        authors = []
        authors_bais = []
        for a in authors_raw:
            (n, b) = ItemWidget._ParseAuthor(a)
            authors.append(n)
            authors_bais.append(b)
        data["authors"] = authors
        data["authors_bais"] = authors_bais

        editors_raw = [
            e for e in
            [" ".join(e.split()) for e in self._editors.toPlainText().splitlines()]
            if e != ""
        ]
        editors = []
        editors_bais = []
        for e in editors_raw:
            (n, b) = ItemWidget._ParseAuthor(e)
            editors.append(n)
            editors_bais.append(b)
        data["editors"] = editors
        data["editors_bais"] = editors_bais

        abstract = self._abstract.toPlainText().strip()
        data["abstract"] = abstract if abstract != "" else None

        date = self._date.text().strip()
        if date == "":
            data["date"] = None
        else:
            date = ItemWidget._ParseDate(date)
            if date is not None:
                data["date"] = date

        publication = self._publication.text().strip()
        data["publication"] = publication if publication != "" else None

        volume = self._volume.text().strip()
        data["volume"] = volume if volume != "" else None

        issue = self._issue.text().strip()
        data["issue"] = issue if issue != "" else None

        pages = self._pages.text().strip()
        data["pages"] = pages if pages != "" else None

        year = self._year.text().strip()
        if year == "":
            data["year"] = None
        else:
            try:
                data["year"] = int(year)
            except:
                pass

        edition = self._edition.text().strip()
        data["edition"] = edition if edition != "" else None

        series = self._series.text().strip()
        data["series"] = series if series != "" else None

        publisher = self._publisher.text().strip()
        data["publisher"] = publisher if publisher != "" else None

        data["isbns"] = [
            i for i in
            [" ".join(i.split()) for i in self._isbns.toPlainText().splitlines()]
            if i != ""
        ]

        institution = self._institution.text().strip()
        data["institution"] = institution if institution != "" else None

        degree = self._degree.text().strip()
        data["degree"] = degree if degree != "" else None

        texkey = self._texkey.text().strip()
        data["texkey"] = texkey if texkey != "" else None

        inspire_id = self._inspire_id.text().strip()
        if inspire_id == "":
            data["inspire_id"] = None
        else:
            try:
                data["inspire_id"] = int(inspire_id)
            except:
                pass

        arxiv_id = self._arxiv_id.text().strip()
        data["arxiv_id"] = arxiv_id if arxiv_id != "" else None

        data["dois"] = [
            d for d in
            [d.strip() for d in self._dois.toPlainText().splitlines()]
            if d != ""
        ]

        self._table.EditRow(self._id, data)

        self.ItemUpdated.emit()

    # def _Open(self):
    #     pass

    def SetTable(self, database_table):
        if self._table is not None:
            self._table.Cleared.disconnect(self.Clear)

        self._table = database_table
        self._table.Cleared.connect(self.Clear)

    def Clear(self):
        self._scroll_widget.hide()
        self._scroll.verticalScrollBar().hide()

    def DisplayItem(self, id_=False):
        if id_:
            self._id = id_

        if self._id == -1:
            self.Clear()
            self._reload.setEnabled(False)
            self._save.setEnabled(False)
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
                authors.append(e)
            else:
                authors.append(e + " (" + b + ")")
        record["editors"] = editors
        for (k, v) in ItemWidget._FORMAT_FUNCTIONS.items():
            record[k] = v(record[k])

        self._type.setCurrentText(record["type"])
        self._title.setPlainText(record["title"])
        self._authors.setPlainText(record["authors"])
        self._editors.setPlainText(record["editors"])
        self._abstract.setPlainText(record["abstract"])
        self._date.setText(record["date"])
        self._publication.setText(record["publication"])
        self._volume.setText(record["volume"])
        self._issue.setText(record["issue"])
        self._pages.setText(record["pages"])
        self._year.setText(record["year"])
        self._edition.setText(record["edition"])
        self._series.setText(record["series"])
        self._publisher.setText(record["publisher"])
        self._isbns.setPlainText(record["isbns"])
        self._institution.setText(record["institution"])
        self._degree.setText(record["degree"])
        self._texkey.setText(record["texkey"])
        self._inspire_id.setText(record["inspire_id"])
        self._arxiv_id.setText(record["arxiv_id"])
        self._dois.setPlainText(record["dois"])

        self._scroll.verticalScrollBar().show()
        self._scroll_widget.show()

        self._reload.setEnabled(False)
        self._save.setEnabled(False)

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
        if n_dashes == 0:
            try:
                return datetime.strptime(date_string, "%Y").strftime("%Y")
            except:
                return None
        if n_dashes == 1:
            try:
                return datetime.strptime(date_string, "%Y-%m").strftime("%Y-%m")
            except:
                return None
        if n_dashes == 2:
            try:
                return datetime.strptime(date_string, "%Y-%m-%d").strftime("%Y-%m-%d")
            except:
                return None
        return None


class AdaptiveTextEdit(QTextEdit):
    def __init__(self, min_height, parent=None):
        # One might want to add a mechanism for setting a max_height.
        super(AdaptiveTextEdit, self).__init__(parent)
        self.min_height = min_height
        self.setAcceptRichText(False)
        self.setTabChangesFocus(True)
        self.document().documentLayout().documentSizeChanged.connect(self.Resize)

    def focusOutEvent(self, event):
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

        super(AdaptiveTextEdit, self).focusOutEvent(event)

    def Resize(self, new_size):
        margins = self.contentsMargins()
        document_size = self.document().documentLayout().documentSize()
        height = document_size.height() + margins.top() + margins.bottom()
        # self.setMinimumHeight(max(height, self.min_height))
        self.setFixedHeight(max(height, self.min_height))

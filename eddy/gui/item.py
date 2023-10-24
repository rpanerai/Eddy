from functools import partial
import base64

from PySide2.QtCore import Qt, Signal, QUrl
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PySide2.QtGui import QIcon, QCursor
from PySide2.QtWidgets import QApplication, QMenu

from eddy.core.web import WebSearch, INSPIRE_SOURCE
from eddy.icons import icons
from eddy.core.platform import ROOT_DIR, OpenWebURL, OpenLocalDocument, OpenOnlineDocument
from eddy.core.documents import PNGFrontPageFromPDF
from eddy.network import inspire, arxiv


class ItemPage(QWebEnginePage):
    ButtonClicked = Signal(QUrl)

    # This is a workaraound necessary since pathlib strips trailing slashes
    _BASE_URL = QUrl.fromLocalFile(
        str(ROOT_DIR / "extern" / "katex" / "_")
        ).toString(QUrl.FormattingOptions(QUrl.RemoveFilename))

    _HEAD_KATEX = '''
        <link rel="stylesheet" href="katex.min.css">
        <script defer src="katex.min.js"></script>
        <script defer src="contrib/auto-render.min.js" onload="
            renderMathInElement(document.body, {delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ]});"></script>
        </script>
        <style>
            .katex {font-size: 1.0em !important;}
        </style>
    '''

    # renderMathInElement(document.body, {delimiters: [
    #     {left: '$$', right: '$$', display: true},
    #     {left: '$', right: '$', display: false},
    #     {left: '\\(', right: '\\)', display: false},
    #     {left: '\\[', right: '\\]', display: true}
    # ]});

    _CSS_TEXT = '''
        <style type="text/css">
        body {
            font-family: "Times New Roman", Times, serif;
        }
        .itemtype{
            font-family: sans-serif;
            color: Gray;
            font-size: 80%;
        }
        </style>
    '''

    _CSS_BUTTON = f'''
        <style type="text/css">
        .iconbutton {{
            background-size: contain;
            background-repeat: no-repeat;
            height: 22px; width: 22px;
            margin-right: 8px;
            border: 1px solid transparent;
            border-radius: 2px;
            outline: none;
        }}
        .iconbutton:hover {{
            border: 1px solid Gray;
        }}
        .disabled{{
            opacity: 0.3;
        }}
        .disabled:hover{{
            border: 1px solid transparent;
        }}
        .inspire{{background-image: url({icons.INSPIRE});}}
        .arxiv{{background-image: url({icons.ARXIV});}}
        .links{{background-image: url({icons.SEARCH});}}
        .files{{background-image: url({icons.FILES}); float: right;}}
        </style>
    '''

    _CSS_COVER = '''
        <style type="text/css">
            img.cover {
            width: 100%;
            max-width: 300px;
            height: auto;
        }
        </style>
    '''

    _TYPES = {
        "A": "ARTICLE",
        "B": "BOOK",
        "C": "BOOK CHAPTER",
        "N": "NOTE",
        "P": "CONFERENCE PROCEEDINGS",
        "R": "REPORT",
        "T": "THESIS"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor(Qt.transparent)

    def acceptNavigationRequest(self, url, type_, isMainFrame):
        if type_ is QWebEnginePage.NavigationType.NavigationTypeTyped:
            # This is the type_ associated with setHtml(). Only in this case, we honor the request.
            return super().acceptNavigationRequest(url, type_, isMainFrame)

        # Any other navigation request is a button click.
        # We simply emit the associated signal and decline the request.
        self.ButtonClicked.emit(url)
        return False

    def Clear(self):
        self.setHtml("")

    def ShowPage(self, item):
        inspire_button = ItemPage._TopButton("inspire", path=item["inspire_id"])
        arxiv_button = ItemPage._TopButton("arxiv", path=item["arxiv_id"])
        links_button = ItemPage._TopButton("links", path=item["inspire_id"])
        files_button = ItemPage._TopButton("files", enabled=(item["files"] != []))

        item_type = ItemPage._TYPES[item["type"]]

        title = t if (t := item["title"]) is not None else "(No Title)"

        abstract = a if (a := item["abstract"]) is not None and item["type"] != "B" else ""

        authors = (" ".join(a.split(", ", 1)[::-1]) for a in item["authors"])
        author_bais = (b if b is not None else "" for b in item["authors_bais"])
        author_button = (
            f'''<button onclick="window.location.href='author:{a}/{b}';">{a}</button>'''
            for (a, b) in zip(authors, author_bais)
        )

        if (js := ItemPage._JournalString(item)) is not None:
            journal_button = (
                f'''<button onclick="window.location.href='dois:';">{js}</button>'''
            )
        else:
            journal_button = ""

        if item["type"] == "B" and item["files"] != []:
            covers = [
                f'<a href="file:{f}"><p>{i}</p></a>' for f in item["files"]
                if (i := ItemPage._FrontCoverHTMLImage(f)) is not None
            ]
            covers = "".join(covers)
        else:
            covers = ""

        html = f'''
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                {ItemPage._HEAD_KATEX}
                {ItemPage._CSS_TEXT}
                {ItemPage._CSS_BUTTON}
                {ItemPage._CSS_COVER}
            </head>
            <body>
            <div class="content">
                <p>{inspire_button}{arxiv_button}{links_button}{files_button}</p>
                <p class="itemtype">{item_type}</p>
                <h3>{title}</h3>
                <p>{" ".join(author_button)}</p>
                <p>{journal_button}</p>
                <p align="justify">{abstract}</p>
                <p>{covers}</p>
            </div>
            </body>
            </html>
        '''

        self.setHtml(html, ItemPage._BASE_URL)

    @staticmethod
    def _TopButton(scheme, path="", enabled=None):
        # This function should be called either with
        #   _TopButton(scheme, path)
        # and the button will be enabled provided path is not None, or with
        #   _TopButton(scheme, enabled)
        # if path is intended to be an empty string.

        is_enabled = enabled if enabled is not None else (path is not None)

        if is_enabled:
            return f'''
                <button class="iconbutton {scheme}"
                    onclick="window.location.href='{scheme}:{path}';">
                </button>
            '''

        return f'''<button class="iconbutton {scheme} disabled"></button>'''

    @staticmethod
    def _JournalString(item):
        if item["publication"] is None:
            return None

        volume = f"<b>{v}</b>" if (v := item["volume"]) is not None else ""
        year = f"({y})" if (y := item["year"]) is not None else ""
        issue = f"{i}," if (i := item["issue"]) is not None else ""
        pages = p if (p := item["pages"]) is not None else ""

        # title volume (year) [issue,] pages
        return f"{item['publication']} {volume} {year} {issue} {pages}"

    @staticmethod
    def _FrontCoverHTMLImage(file):
        match file.suffix:
            case ".pdf":
                try:
                    cover_png = PNGFrontPageFromPDF(file)
                except:
                    return None
            case ".djvu":
                return None
            case _:
                return None

        cover_png_base64 = base64.b64encode(cover_png).decode("utf-8")
        return f'<img src="data:image/png;base64,{cover_png_base64}" class="cover">'


class ItemView(QWebEngineView):
    NewTabRequested = Signal(WebSearch)

    _KEYS = (
        "type",
        "title",
        "authors",
        "authors_bais",
        # "editors",
        # "editors_bais",
        "abstract",
        # "date",
        "publication",
        "volume",
        "issue",
        "pages",
        "year",
        # "edition",
        # "series",
        # "publisher",
        # "isbns",
        # "institution",
        # "degree",
        # "texkey",
        "inspire_id",
        "arxiv_id",
        # "arxiv_cats",
        "dois",
        # "urls",
        "files"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent")

        self._source = None
        self._table = None
        self._id = -1

        self.setContextMenuPolicy(Qt.PreventContextMenu)
        # To have a custom context menu one should reimplement contextMenuEvent as below

        self._page = ItemPage()
        self._page.ButtonClicked.connect(self._HandleButtonClicked)
        self._page.Clear()
        self.setPage(self._page)

        self._item = None

    # def contextMenuEvent(self, event):
    #     self.menu = self.page().createStandardContextMenu()
    #     self.menu.addAction(str(event.pos()))
    #     self.menu.popup(event.globalPos())

    def SetLocalSource(self, source):
        if self._source == source:
            return

        self._source = source
        # if self._table is not None:
        #     self._table.Updated.disconnect(self.DisplayItem)
        self._table = source.table
        # self._table.Updated.connect(self.DisplayItem)

    def SetTable(self, database_table):
        if self._table == database_table:
            return

        self._source = None
        # if self._table is not None:
        #     self._table.Updated.disconnect(self.DisplayItem)
        self._table = database_table
        # self._table.Updated.connect(self.DisplayItem)

    def DisplayItem(self, id_):
        # NOTE: When self._id == id_, we do not skip this function.
        #       In fact, it means that the item was updated and TableView has emitted an
        #       ItemSelected() signal as the result of a model reset triggere by an
        #       Updated() signal from the associated Table.
        #       This method is not quite robust, though, since it relies on the fact that
        #       we are resetting the model for every database update which is not the right
        #       way of dealing with this.
        #       Furthermore, it seems that every Update() triggers two consecutive
        #       ItemSelected() signals. Can we avoid this?

        self._id = id_

        if self._id == -1:
            self._page.Clear()
            return

        self._item = self._table.GetRow(self._id, self._KEYS)
        self._item["files"] = [self._source.FilesDir() / f for f in self._item["files"]]

        self._page.ShowPage(self._item)

    def _HandleButtonClicked(self, url):
        match url.scheme():
            case "author":
                self._ShowAuthorContextMenu(url.path())
            case "dois":
                self._ShowDOIsContextMenu()
            case "inspire":
                self._ShowInspireContextMenu(url.path())
            case "arxiv":
                self._ShowArXivContextMenu(url.path())
            case "links":
                self._ShowLinksContextMenu(url.path())
            case "file":
                OpenLocalDocument(url.path())
            case "files":
                self._ShowFilesContextMenu()
            case _:
                pass

    def _ShowAuthorContextMenu(self, author):
        (name, bai) = author.split('/')
        menu = QMenu()

        if bai != "":
            action_references = menu.addAction(QIcon(icons.SEARCH), f"Search author: {bai}")
            ref_search = INSPIRE_SOURCE.CreateSearch(f"a {bai}")
            action_references.triggered.connect(partial(self.NewTabRequested.emit, ref_search))

        menu.addSeparator()

        action_copy_author = menu.addAction(QIcon(icons.FILES), f"Copy '{name}'")
        action_copy_author.triggered.connect(partial(QApplication.clipboard().setText, name))

        if bai != "":
            action_copy_bai = menu.addAction(QIcon(icons.FILES), f"Copy '{bai}'")
            action_copy_bai.triggered.connect(partial(QApplication.clipboard().setText, bai))

        pos = QCursor().pos()
        menu.exec_(pos)

    def _ShowDOIsContextMenu(self):
        dois = self._item["dois"]
        if dois == []:
            return

        menu = QMenu()

        doi_actions = (menu.addAction(QIcon(icons.DOI), f"Open DOI link: {d}") for d in dois)
        doi_urls = (f"https://doi.org/{d}" for d in dois)
        for (a, u) in zip(doi_actions, doi_urls):
            a.triggered.connect(partial(OpenWebURL, u))

        pos = QCursor().pos()
        menu.exec_(pos)

    @staticmethod
    def _ShowInspireContextMenu(inspire_id):
        menu = QMenu()
        action_inspire_page = menu.addAction(QIcon(icons.INSPIRE), "Open INSPIRE page")
        inspire_url = inspire.LiteratureUrl(inspire_id)
        action_inspire_page.triggered.connect(partial(OpenWebURL, inspire_url))
        pos = QCursor().pos()
        menu.exec_(pos)

    @staticmethod
    def _ShowArXivContextMenu(arxiv_id):
        menu = QMenu()
        action_arxiv_page = menu.addAction(QIcon(icons.ARXIV), "Open arXiv page")
        action_arxiv_pdf = menu.addAction(QIcon(icons.PDF), "Open arXiv PDF")
        arxiv_url = arxiv.AbstractUrl(arxiv_id)
        action_arxiv_page.triggered.connect(partial(OpenWebURL, arxiv_url))
        pdf_url = arxiv.PDFUrl(arxiv_id)
        action_arxiv_pdf.triggered.connect(partial(OpenOnlineDocument, pdf_url))
        pos = QCursor().pos()
        menu.exec_(pos)

    def _ShowLinksContextMenu(self, inspire_id):
        menu = QMenu()
        action_references = menu.addAction(QIcon(icons.SEARCH), "Find references")
        action_citations = menu.addAction(QIcon(icons.SEARCH), "Find citations")
        ref_search = INSPIRE_SOURCE.CreateSearch(f"citedby:recid:{inspire_id}")
        action_references.triggered.connect(partial(self.NewTabRequested.emit, ref_search))
        cit_search = INSPIRE_SOURCE.CreateSearch(f"refersto:recid:{inspire_id}")
        action_citations.triggered.connect(partial(self.NewTabRequested.emit, cit_search))
        pos = QCursor().pos()
        menu.exec_(pos)

    def _ShowFilesContextMenu(self):
        menu = QMenu()
        for f in self._item["files"]:
            a = menu.addAction(icons.FileIcon(f), f.name)
            a.triggered.connect(partial(OpenLocalDocument, f))

        pos = QCursor().pos()
        menu.exec_(pos)

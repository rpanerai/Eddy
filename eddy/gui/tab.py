from PySide2.QtCore import Signal, QSize
from PySide2.QtGui import Qt, QIcon
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget, QStatusBar, QProgressBar,
    QSizePolicy, QToolButton, QLabel
)

from config import LEFT_PANEL_WIDTH
from eddy.network.fetcher import Fetcher
from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.core.local import LocalSource
from eddy.core.web import WebSource, WebSearch, INSPIRE_SOURCE
from eddy.gui.table import TableModel, TableView
from eddy.gui.item import ItemView
from eddy.gui.edit import EditWidget
from eddy.gui.bibtex import BibTeXWidget
from eddy.gui.searchfilter import SearchBar, FilterBar
from eddy.gui.source import SourceModel, SourcePanel
from eddy.icons import icons


class TabContent(QWidget):
    NewTabRequested = Signal(WebSearch)
    TitleRequested = Signal((str, str), ())

    def __init__(self, index, source_model, memory_database, parent=None):
        super().__init__(parent)

        self._database_table = ItemsTable(memory_database, f"tab{index}", drop_on_del=True)
        self._database_table.Clear()

        self._last_search = None

        self._fetcher = Fetcher()
        self._fetcher.FetchingStarted.connect(self._HandleFetchingStarted)
        self._fetcher.BatchReady.connect(self._database_table.AddData)
        self._fetcher.FetchingFinished.connect(self._HandleFetchingCompleted)
        self._fetcher.FetchingStopped.connect(self._HandleFetchingStopped)
        self._fetcher.FetchingError.connect(self._HandleFetchingError)

        self._source_panel = SourcePanel()
        self._source_panel.setModel(source_model)
        self._source_panel.WebSourceSelected.connect(self._HandleWebSourceSelected)
        self._source_panel.LocalSourceSelected.connect(self._HandleLocalSourceSelected)

        self._search_bar = SearchBar()
        self._search_bar.QueryLaunched.connect(self._HandleQueryLaunched)
        self._search_bar.StopPressed.connect(self.StopFetching)

        self._splitter = TableItemSplitter()
        self._splitter.table_view.NewTabRequested.connect(self.NewTabRequested)
        self._splitter.item_view.NewTabRequested.connect(self.NewTabRequested)

        self._filter_bar = FilterBar()
        self._filter_bar.TextChanged.connect(self._splitter.table_model.Filter)

        self._status_bar = QStatusBar()
        self._splitter.table_view.StatusUpdated.connect(self._HandleStatusUpdated)
        self._search_status_bar = SearchStatus()
        self._status_bar.addPermanentWidget(self._search_status_bar)
        self._fetcher.BatchProgress.connect(self._search_status_bar.SetProgress)

        self._active_source = None
        self._source_panel.SelectSource(INSPIRE_SOURCE)

        self._SetupUI()

        self.setFocusProxy(self._search_bar)

    def _SetupUI(self):
        main_layout = QVBoxLayout()
        search_filter_widget = QWidget()
        search_filter_layout = QHBoxLayout(search_filter_widget)
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        panel_splitter = QSplitter(Qt.Horizontal)
        panel_splitter.setHandleWidth(4)
        panel_splitter.addWidget(self._source_panel)
        panel_splitter.addWidget(central_widget)
        panel_splitter.setStretchFactor(0, 0)
        panel_splitter.setStretchFactor(1, 1)
        panel_splitter.moveSplitter(LEFT_PANEL_WIDTH, 1)
        panel_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        search_filter_layout.addWidget(self._search_bar)
        search_filter_layout.addWidget(self._filter_bar)
        search_filter_layout.setContentsMargins(0, 0, 0, 0)

        central_layout.addWidget(search_filter_widget)
        central_layout.addWidget(self._splitter)
        central_layout.addWidget(self._status_bar)
        central_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(panel_splitter)
        self.setLayout(main_layout)

    def RunSearch(self, search):
        self._source_panel.SelectSource(search.source)
        self._search_bar.LaunchQuery(search.query)

    def StopFetching(self):
        self._fetcher.Stop()

    def _HandleWebSourceSelected(self, source):
        if self._last_search is None:
            self._splitter.table_view.SetShowCitations(source.has_cites)

        if isinstance(self._active_source, WebSource):
            self._active_source = source
            return

        self._active_source = source
        self._search_bar.SetQueryEditEnabled(True)
        self._filter_bar.clear()

        if self._last_search is None:
            self.TitleRequested[()].emit()
        else:
            self._search_bar.SetQuery(self._last_search.query)
            self.TitleRequested.emit(self._last_search.source.icon, self._last_search.title)
            self._splitter.table_view.SetShowCitations(self._last_search.source.has_cites)
        self._search_status_bar.text.show()

        self._splitter.SetTable(self._database_table)

    def _HandleLocalSourceSelected(self, source, tags):
        if not isinstance(self._active_source, LocalSource):
            self.StopFetching()
            self._search_bar.Clear()
            self._search_bar.SetQueryEditEnabled(False)
            self._splitter.table_view.SetShowCitations(False)

        self._active_source = source
        title = f"{source.name}: {tags[0].name}" if tags != [] else source.name
        self.TitleRequested.emit(icons.DATABASE, title)
        self._filter_bar.clear()
        self._search_status_bar.text.hide()
        self._splitter.SetLocalSource(source, tags)

    def _HandleQueryLaunched(self, query):
        if not isinstance(self._active_source, WebSource):
            return

        self._database_table.Clear()
        self._filter_bar.clear()

        search = self._active_source.CreateSearch(query)
        self._last_search = search
        self.TitleRequested.emit(search.source.icon, search.title)
        self._splitter.table_view.SetShowCitations(self._active_source.has_cites)
        self._fetcher.Fetch(search.source.plugin, search.query)

    def _HandleFetchingStarted(self):
        self._search_bar.SetStopEnabled(True)
        self._search_status_bar.text.clear()
        self._search_status_bar.ShowProgress()

    def _HandleFetchingCompleted(self):
        self._HandleFetchingEnded("Fetching completed")

    def _HandleFetchingStopped(self):
        self._HandleFetchingEnded("Fetching stopped")

    def _HandleFetchingError(self, error):
        self._HandleFetchingEnded(f"Fetching error: {error}")

    def _HandleFetchingEnded(self, message):
        self._search_bar.SetStopEnabled(False)
        self._search_status_bar.HideProgress()
        self._search_status_bar.text.setText(message)

    def _HandleStatusUpdated(self, total, selected_ids):
        match total:
            case 0:
                self._status_bar.showMessage("0 items")
                return
            case 1:
                message = f"1 item, {len(selected_ids)} selected"
            case _:
                message = f"{total} items, {len(selected_ids)} selected"

        if selected_ids != []:
            if isinstance(self._active_source, WebSource) and self._last_search.source.has_cites:
                citations = self._database_table.GetTotalCitations(selected_ids)
                message = f"{message} ({citations} citations among selected)"

        self._status_bar.showMessage(message)


class TableItemSplitter(QSplitter):
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)

        self.table_model = TableModel(self)

        self.table_view = TableView()
        self.table_view.setModel(self.table_model)

        property_tab = QTabWidget()
        property_tab.setDocumentMode(True)

        self.item_view = ItemView()
        self.edit_widget = EditWidget()
        self.bibtex_widget = BibTeXWidget()
        self.table_view.ItemSelected.connect(self.item_view.DisplayItem)
        self.table_view.ItemSelected.connect(self.edit_widget.DisplayItem)
        self.table_view.ItemSelected.connect(self.bibtex_widget.DisplayItem)
        self.edit_widget.ItemUpdated.connect(self.table_model.Update)

        property_tab.addTab(self.item_view, "Item")
        property_tab.addTab(self.edit_widget, "Edit")
        property_tab.addTab(self.bibtex_widget, "BibTeX")

        self.setHandleWidth(4)
        self.addWidget(self.table_view)
        self.addWidget(property_tab)
        self.setStretchFactor(0, 5)
        self.setStretchFactor(1, 2)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def SetTable(self, table):
        self.item_view.SetTable(table)
        self.table_model.SetTable(table)
        self.edit_widget.SetTable(table)
        self.bibtex_widget.SetTable(table)

    def SetLocalSource(self, source, tags):
        self.item_view.SetLocalSource(source)
        self.table_model.SetLocalSource(source)
        self.table_model.SetTags(tags)
        self.edit_widget.SetLocalSource(source)
        self.bibtex_widget.SetTable(source.table)


class SearchStatus(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.text = QLabel()
        self._progress = QProgressBar()
        self._progress.hide()

        layout = QHBoxLayout()
        layout.addWidget(self.text)
        layout.addWidget(self._progress)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def sizeHint(self):
        width = super().sizeHint().width()
        height = self._progress.sizeHint().height()
        return QSize(width, height)

    def SetProgress(self, bytes_received, bytes_total):
        self._progress.setMaximum(bytes_total)
        self._progress.setValue(bytes_received)

    def ShowProgress(self):
        self._progress.show()

    def HideProgress(self):
        self._progress.hide()
        self._progress.reset()


class TabSystem(QTabWidget):
    LastTabClosed = Signal()

    _DEFAULT_TEXT = "New Tab"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setElideMode(Qt.ElideRight)

        self.setDocumentMode(True)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._CloseTab)

        new_tab_button = QToolButton()
        new_tab_button.setIcon(QIcon(icons.TAB_NEW))
        new_tab_button.clicked.connect(self.AddTab)
        self.setCornerWidget(new_tab_button, Qt.Corner.TopLeftCorner)

        self.setMovable(True)

        # self.setFocusPolicy(Qt.NoFocus)

        self._source_model = SourceModel()
        self._memory_database = Database()

        self._index = 0

    def _CloseTab(self, index):
        content = self.widget(index)
        content.StopFetching()
        content.deleteLater()

        self.removeTab(index)

        if self.count() == 0:
            self.LastTabClosed.emit()
        else:
            self.currentWidget().setFocus()

    def CloseCurrentTab(self):
        self._CloseTab(self.currentIndex())

    def AddTab(self, search=False):
        self._index = self._index + 1
        new_tab = TabContent(self._index, self._source_model, self._memory_database)
        self.addTab(new_tab, TabSystem._DEFAULT_TEXT)

        new_tab.NewTabRequested.connect(self.AddTab)
        new_tab.TitleRequested[str, str].connect(self.RenameTab)
        new_tab.TitleRequested[()].connect(self.RenameTab)

        self.setCurrentWidget(new_tab)

        new_tab.setFocus()

        if search:
            new_tab.RunSearch(search)

    def RenameTab(self, icon=QIcon(), text=_DEFAULT_TEXT):
        index = self.indexOf(self.sender())

        self.setTabIcon(index, QIcon(icon))
        self.setTabText(index, text)

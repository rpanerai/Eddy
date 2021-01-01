from PySide2.QtCore import Signal
from PySide2.QtGui import Qt, QIcon
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget, QStatusBar, QProgressBar,
    QSizePolicy, QToolButton
)

from config import LEFT_PANEL_WIDTH
from eddy.network.fetcher import Fetcher
from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.core.local import LocalSource
from eddy.core.web import WebSource, WebSearch, INSPIRE_SOURCE
from eddy.gui.table import TableModel, TableView
from eddy.gui.item import ItemWidget
from eddy.gui.searchfilter import SearchBar, FilterBar
from eddy.gui.source import SourceModel, SourcePanel
from eddy.icons import icons


class TabContent(QWidget):
    NewTabRequested = Signal(WebSearch)
    TitleRequested = Signal((str, str), ())

    def __init__(self, index, source_model, memory_database, parent=None):
        super().__init__(parent)

        self._database_table = ItemsTable(memory_database, "tab" + str(index), drop_on_del=True)
        # self._database_table = ItemsTable(Database("./test.db"), "items", drop_on_del=False)
        self._database_table.Clear()

        self._last_search = None
        self._last_search_status = ""

        self._fetcher = Fetcher()
        self._fetcher.FetchingStarted.connect(self._HandleFetchingStarted)
        self._fetcher.BatchProgress.connect(self._HandleFetchingProgress)
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

        self._table_model = TableModel(self)

        self._filter_bar = FilterBar()
        self._filter_bar.TextChanged.connect(self._table_model.Filter)

        self._table_view = TableView()
        self._table_view.setModel(self._table_model)
        self._table_view.NewTabRequested.connect(self.NewTabRequested)

        self._item_widget = ItemWidget()
        self._item_widget.SetTable(self._database_table)
        self._table_view.ItemSelected.connect(self._item_widget.DisplayItem)
        self._item_widget.ItemUpdated.connect(self._table_model.Update)

        self._status_bar = QStatusBar()
        self._table_view.StatusUpdated.connect(self._HandleStatusUpdated)
        self._progress_bar = QProgressBar()
        self._progress_bar.hide()
        self._status_bar.addPermanentWidget(self._progress_bar)

        self._active_source = None
        self._source_panel.SelectSource(INSPIRE_SOURCE)

        self._SetupUI()

        self.setFocusProxy(self._search_bar)

    def RunSearch(self, search):
        self._source_panel.SelectSource(search.source)
        self._search_bar.LaunchQuery(search.query)

    def StopFetching(self):
        self._fetcher.Stop()

    def _SetupUI(self):
        main_layout = QVBoxLayout()
        search_filter_widget = QWidget()
        search_filter_layout = QHBoxLayout(search_filter_widget)
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        item_splitter = QSplitter(Qt.Horizontal)
        item_splitter.setHandleWidth(4)
        item_splitter.addWidget(self._table_view)
        item_splitter.addWidget(self._item_widget)
        item_splitter.setStretchFactor(0, 5)
        item_splitter.setStretchFactor(1, 2)
        item_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        central_layout.addWidget(item_splitter)
        central_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(panel_splitter)
        main_layout.addWidget(self._status_bar)
        self.setLayout(main_layout)

    def _HandleWebSourceSelected(self, source):
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
        self._status_bar.showMessage(self._last_search_status)

        self._table_view.SetShowCitations(True)
        self._table_model.SetTable(self._database_table)
        self._item_widget.SetTable(self._database_table)

    def _HandleLocalSourceSelected(self, source, tag_ids):
        if not isinstance(self._active_source, LocalSource):
            self.StopFetching()
            self._search_bar.Clear()
            self._search_bar.SetQueryEditEnabled(False)
            self._table_view.SetShowCitations(False)

        self._active_source = source
        self.TitleRequested.emit(icons.DATABASE, source.name)
        self._filter_bar.clear()
        self._status_bar.clearMessage()
        self._table_model.SetLocalSource(source)
        self._table_model.SetTags(tag_ids)
        self._item_widget.SetLocalSource(source)

    def _HandleQueryLaunched(self, query):
        if not isinstance(self._active_source, WebSource):
            return

        self._database_table.Clear()
        self._filter_bar.clear()
        search = self._active_source.CreateSearch(query)
        self._last_search = search
        self.TitleRequested.emit(search.source.icon, search.title)
        self._fetcher.Fetch(search.source.plugin, search.query)

    def _HandleFetchingStarted(self):
        self._status_bar.showMessage("Fetching…")
        self._progress_bar.reset()
        self._progress_bar.show()
        self._search_bar.SetStopEnabled(True)

    def _HandleFetchingProgress(self, bytes_received, bytes_total):
        self._progress_bar.setMaximum(bytes_total)
        self._progress_bar.setValue(bytes_received)

    def _HandleFetchingCompleted(self, records_number):
        message = "Fetching completed: " + str(records_number) + " records found."
        self._last_search_status = message
        self._status_bar.showMessage(message)
        self._progress_bar.hide()
        self._search_bar.SetStopEnabled(False)

    def _HandleFetchingStopped(self):
        message = "Fetching stopped."
        self._last_search_status = message
        self._status_bar.showMessage(message)
        self._progress_bar.hide()
        self._search_bar.SetStopEnabled(False)

    def _HandleFetchingError(self, error):
        message = "Fetching error: " + error + "."
        self._last_search_status = message
        self._status_bar.showMessage(message)
        self._progress_bar.hide()
        self._search_bar.SetStopEnabled(False)

    def _HandleStatusUpdated(self, total, selected):
        if isinstance(self._active_source, LocalSource):
            self._status_bar.showMessage(
                str(total) + " item" + ("" if total == 1 else "s") + ", "
                + str(selected) + " selected."
            )


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

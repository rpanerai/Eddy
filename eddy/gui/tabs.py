from functools import partial

from PySide2.QtCore import Signal
from PySide2.QtGui import Qt, QIcon
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget, QStatusBar, QProgressBar,
    QSizePolicy, QPushButton
)

from eddy.network.fetcher import Fetcher
from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import ArXivPlugin
from eddy.data.database import Database, Table
from eddy.gui.table import TableModel, TableView
from eddy.gui.item import ItemModel, ItemView
from eddy.gui.searchfilter import SearchBar, FilterBar
from eddy.gui.source import SourceModel, SourcePanel
from eddy.icons import icons


class TabContent(QWidget):
    NewTabRequested = Signal(dict)
    TitleRequested = Signal(str, str)

    _PLUGINS = {
        "INSPIRE": InspirePlugin,
        "arXiv": ArXivPlugin
    }

    def __init__(self, index, source_model, memory_database, parent=None):
        super(TabContent, self).__init__(parent)

        self._database_table = Table(memory_database, "tab" + str(index), drop_on_del=True)
        self._database_table.Clear()

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
        self._search_bar.QueryLaunched.connect(self._source_panel.LaunchSearch)
        self._source_panel.SearchRequested.connect(self._HandleSearchRequested)
        self._search_bar.StopPressed.connect(self.StopFetching)

        self._table_model = TableModel(self)

        self._filter_bar = FilterBar()
        self._filter_bar.TextChanged.connect(self._table_model.Filter)

        self._table_view = TableView()
        self._table_view.setModel(self._table_model)
        self._table_view.NewTabRequested.connect(self.NewTabRequested)

        self._item_model = ItemModel(self)
        self._table_view.ItemSelected.connect(self._item_model.DisplayRecord)
        self._item_view = ItemView()
        self._item_view.setModel(self._item_model)

        self._status_bar = QStatusBar()
        self._progress_bar = QProgressBar()
        self._progress_bar.hide()
        self._status_bar.addPermanentWidget(self._progress_bar)

        self._web_source_active = False
        self._source_panel.SelectSource("INSPIRE")

        self._SetupUI()

        self.setFocusProxy(self._search_bar)

    def RunSearch(self, search):
        self._source_panel.SelectSource(search["source"])
        self._search_bar.LaunchQuery(search["query"])

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
        item_splitter.addWidget(self._item_view)
        item_splitter.setStretchFactor(0, 2)
        item_splitter.setStretchFactor(1, 1)
        item_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        panel_splitter = QSplitter(Qt.Horizontal)
        panel_splitter.setHandleWidth(4)
        panel_splitter.addWidget(self._source_panel)
        panel_splitter.addWidget(central_widget)
        # panel_splitter.setStretchFactor(0, 1)
        # panel_splitter.setStretchFactor(1, 3)
        panel_splitter.setSizes([80, panel_splitter.width() - 80])
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

    def _HandleWebSourceSelected(self):
        if self._web_source_active:
            return

        self._web_source_active = True
        self.TitleRequested.emit("", "")
        self._search_bar.SetQueryEditEnabled(True)
        self._filter_bar.clear()
        self._database_table.Clear()
        self._table_model.SetTable(self._database_table)
        self._item_model.SetTable(self._database_table)

    def _HandleLocalSourceSelected(self, table):
        if self._web_source_active:
            self._web_source_active = False
            self._search_bar.Clear()
            self._search_bar.SetQueryEditEnabled(False)

        # We might use 'table' to extract the name of the local database,
        # or call a function in '_source_panel'.
        self.TitleRequested.emit("Local", "Local database")
        self._filter_bar.clear()
        self._status_bar.clearMessage()
        self._table_model.SetTable(table)
        self._item_model.SetTable(table)

    def _HandleSearchRequested(self, search):
        (source, query) = (search["source"], search["query"])

        self._database_table.Clear()
        self._filter_bar.clear()
        self.TitleRequested.emit(source, query)
        self._fetcher.Fetch(TabContent._PLUGINS[source], query, 50)

    def _HandleFetchingStarted(self):
        self._status_bar.showMessage("Fetching…")
        self._progress_bar.reset()
        self._progress_bar.show()
        self._search_bar.SetStopEnabled(True)

    def _HandleFetchingProgress(self, bytes_received, bytes_total):
        self._progress_bar.setMaximum(bytes_total)
        self._progress_bar.setValue(bytes_received)

    def _HandleFetchingCompleted(self, records_number):
        self._status_bar.showMessage(
            "Fetching completed: " + str(records_number) + " records found."
        )
        self._progress_bar.hide()
        self._search_bar.SetStopEnabled(False)

    def _HandleFetchingStopped(self):
        self._status_bar.showMessage("Fetching stopped.")
        self._progress_bar.hide()
        self._search_bar.SetStopEnabled(False)

    def _HandleFetchingError(self, error):
        self._status_bar.showMessage("Fetching error: " + error + ".")
        self._progress_bar.hide()
        self._search_bar.SetStopEnabled(False)


class TabSystem(QTabWidget):
    LastTabClosed = Signal()

    _DEFAULT_TEXT = "New Tab"

    _ICONS = {
        "INSPIRE": icons.INSPIRE,
        "arXiv": icons.ARXIV
    }

    def __init__(self, parent=None):
        super(TabSystem, self).__init__(parent)

        self.setElideMode(Qt.ElideRight)

        self.setDocumentMode(True)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._CloseTab)

        new_tab_button = QPushButton(QIcon(icons.TAB_NEW), "")
        new_tab_button.clicked.connect(partial(self.AddTab, None))
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

    def AddTab(self, search=None):
        self._index = self._index + 1
        new_tab = TabContent(self._index, self._source_model, self._memory_database)
        self.addTab(new_tab, TabSystem._DEFAULT_TEXT)

        new_tab.NewTabRequested.connect(self.AddTab)
        new_tab.TitleRequested.connect(self.RenameTab)

        self.setCurrentWidget(new_tab)

        new_tab.setFocus()

        if search is not None:
            new_tab.RunSearch(search)

    def RenameTab(self, icon, text):
        index = self.indexOf(self.sender())

        if icon == "":
            icon = QIcon()
        elif icon == "Local":
            icon = QIcon(icons.DATABASE)
        else:
            icon = QIcon(TabSystem._ICONS[icon])
        self.setTabIcon(index, icon)

        if text == "":
            text = TabSystem._DEFAULT_TEXT
        self.setTabText(index, text)

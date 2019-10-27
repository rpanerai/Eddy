from functools import partial

from PySide2.QtCore import Signal
from PySide2.QtGui import Qt, QIcon
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTabWidget, QStatusBar, QProgressBar, QSizePolicy,
    QPushButton
)

from eddy.network.fetcher import Fetcher
from eddy.network.inspire import InspirePlugin
from eddy.network.arxiv import ArXivPlugin
from eddy.data.database import DATABASE_IN_MEMORY, Table
from eddy.gui.table import TableModel, TableView
from eddy.gui.item import ItemModel, ItemView
from eddy.gui.searchfilter import SearchBar, FilterBar
from eddy.icons import icons


class TabContent(QWidget):
    NewTabRequested = Signal(dict)
    SearchStarted = Signal(dict)

    _PLUGINS = {
        "INSPIRE": InspirePlugin,
        "arXiv": ArXivPlugin
    }

    def __init__(self, index, parent=None):
        super(TabContent, self).__init__(parent)

        self._database_table = Table(DATABASE_IN_MEMORY, "tab" + str(index))

        self._fetcher = Fetcher()
        self._fetcher.FetchingStarted.connect(self._HandleFetchingStarted)
        self._fetcher.BatchProgress.connect(self._HandleFetchingProgress)
        self._fetcher.BatchReady.connect(self._database_table.AddData)
        self._fetcher.FetchingFinished.connect(self._HandleFetchingCompleted)
        self._fetcher.FetchingStopped.connect(self._HandleFetchingStopped)
        self._fetcher.FetchingError.connect(self._HandleFetchingError)

        self._search_bar = SearchBar()
        self._search_bar.SearchRequested.connect(self._HandleSearchRequested)
        self._search_bar.StopPressed.connect(self._fetcher.Stop)

        table_model = TableModel(self)
        table_model.SetTable(self._database_table)

        self._filter_bar = FilterBar()
        self._filter_bar.TextChanged.connect(table_model.Filter)

        self._table_view = TableView()
        self._table_view.setModel(table_model)
        self._table_view.NewTabRequested.connect(self.NewTabRequested)

        item_model = ItemModel(self)
        item_model.SetTable(self._database_table)
        self._table_view.ItemSelected.connect(item_model.DisplayRecord)
        self._item_view = ItemView()
        self._item_view.setModel(item_model)

        self._status_bar = QStatusBar()
        self._progress_bar = QProgressBar()
        self._progress_bar.hide()
        self._status_bar.addPermanentWidget(self._progress_bar)

        self._SetupUI()

        self.setFocusProxy(self._search_bar)

    def RunSearch(self, search):
        self._search_bar.RunSearch(search)

    def _SetupUI(self):
        main_layout = QVBoxLayout()
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.addWidget(self._table_view)
        splitter.addWidget(self._item_view)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self._search_bar)
        main_layout.addWidget(self._filter_bar)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self._status_bar)
        self.setLayout(main_layout)

    def _HandleSearchRequested(self, search):
        self._database_table.Clear()
        self._filter_bar.clear()
        self.SearchStarted.emit(search)
        self._fetcher.Fetch(TabContent._PLUGINS[search["source"]], search["query"], 50)

    def _HandleFetchingStarted(self):
        self._status_bar.showMessage("Fetching from Inspire…")
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

    _ICONS = {
        "INSPIRE": icons.INSPIRE,
        "arXiv": icons.ARXIV
    }

    def __init__(self, parent=None):
        super(TabSystem, self).__init__(parent)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.CloseTab)

        self.index = 0

        # self.setFocusPolicy(Qt.NoFocus)

        new_tab_button = QPushButton(QIcon.fromTheme("tab-new"), "")
        new_tab_button.clicked.connect(partial(self.AddTab, None))
        self.setCornerWidget(new_tab_button, Qt.Corner.TopLeftCorner)

    def CloseTab(self, index):
        self.widget(index).deleteLater()
        self.removeTab(index)

        if self.count() == 0:
            self.LastTabClosed.emit()
        else:
            self.currentWidget().setFocus()

    def AddTab(self, search=None):
        self.index = self.index + 1
        new_tab = TabContent(self.index)
        self.addTab(new_tab, "New Tab")

        new_tab.NewTabRequested.connect(self.AddTab)
        new_tab.SearchStarted.connect(self.RenameTab)

        self.setCurrentWidget(new_tab)

        new_tab.setFocus()

        if search is not None:
            new_tab.RunSearch(search)

    def RenameTab(self, search):
        index = self.indexOf(self.sender())
        self.setTabIcon(index, QIcon(TabSystem._ICONS[search["source"]]))
        self.setTabText(index, search["query"])

    def mouseDoubleClickEvent(self, event):
        super(TabSystem, self).mouseDoubleClickEvent(event)

        # We should check the region where the double click takes place.
        # So far, any part of the widget will trigger this.
        self.AddTab()

from PySide2.QtCore import Signal
from PySide2.QtGui import Qt
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTabWidget, QStatusBar, QProgressBar, QSizePolicy
)

from eddy.network.inspire import InspireFetcher
from eddy.data.database import DATABASE_IN_MEMORY, Table
from eddy.gui.table import TableModel, TableView
from eddy.gui.item import ItemModel, ItemView
from eddy.gui.searchfilter import SearchBar, FilterBar


class TabContent(QWidget):
    def __init__(self, index, parent=None):
        super(TabContent, self).__init__(parent)

        self.search_bar = SearchBar()
        self.search_bar.SearchRequested.connect(self._Search)
        self.search_bar.StopPressed.connect(self._KillSearch)

        self.database_table = Table(DATABASE_IN_MEMORY, "tab" + str(index))

        table_model = TableModel(self)
        table_model.SetTable(self.database_table)

        self.filter_bar = FilterBar()
        self.filter_bar.TextChanged.connect(table_model.Filter)

        self.table_view = TableView()
        self.table_view.setModel(table_model)

        item_model = ItemModel(self)
        item_model.SetTable(self.database_table)
        self.table_view.ItemSelected.connect(item_model.DisplayRecord)
        self.item_view = ItemView()
        self.item_view.setModel(item_model)

        self.status_bar = QStatusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        self._SetupUI()

        self.fetcher = InspireFetcher()
        self.fetcher.FetchingStarted.connect(self._HandleFetchingStarted)
        self.fetcher.BatchProgress.connect(self._HandleFetchingProgress)
        self.fetcher.BatchReady.connect(self.database_table.AddData)
        self.fetcher.FetchingFinished.connect(self._HandleFetchingCompleted)
        self.fetcher.FetchingStopped.connect(self._HandleFetchingStopped)

    def _SetupUI(self):
        main_layout = QVBoxLayout()
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.addWidget(self.table_view)
        splitter.addWidget(self.item_view)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.search_bar)
        main_layout.addWidget(self.filter_bar)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.status_bar)
        self.setLayout(main_layout)

    def _KillSearch(self):
        self.fetcher.Stop()

    def _Search(self, query):
        self._KillSearch()
        self.database_table.Clear()
        self.fetcher.Fetch(query, 50)

    def _HandleFetchingStarted(self):
        self.status_bar.showMessage("Fetching from Inspire…")
        self.progress_bar.reset()
        self.progress_bar.show()
        self.search_bar.EnableStopButton()

    def _HandleFetchingProgress(self, bytes_received, bytes_total):
        self.progress_bar.setMaximum(bytes_total)
        self.progress_bar.setValue(bytes_received)

    def _HandleFetchingCompleted(self, records_number):
        self.status_bar.showMessage(
            "Fetching completed: " + str(records_number) + " records found."
        )
        self.progress_bar.hide()
        self.search_bar.DisableStopButton()

    def _HandleFetchingStopped(self):
        self.status_bar.showMessage("Fetching stopped.")
        self.progress_bar.hide()
        self.search_bar.DisableStopButton()


class TabSystem(QTabWidget):
    LastTabClosed = Signal()

    def __init__(self, parent=None):
        super(TabSystem, self).__init__(parent)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.CloseTab)

        self.index = 0
        self.AddTab()

    def CloseTab(self, index):
        self.widget(index).deleteLater()
        self.removeTab(index)

        if self.count() == 0:
            self.LastTabClosed.emit()

    def AddTab(self):
        self.index = self.index + 1
        new_tab = TabContent(self.index)
        self.addTab(new_tab, "INSPIRE")
        self.setCurrentWidget(new_tab)

    def mouseDoubleClickEvent(self, event):
        super(TabSystem, self).mouseDoubleClickEvent(event)

        # We should check the region where the double click takes place.
        # So far, any part of the widget will trigger this.
        self.AddTab()

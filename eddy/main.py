import sys

from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QApplication, QMainWindow, QAction, QStyle

from eddy.gui.tab import TabSystem
from eddy.icons import icons


class MainWindow(QMainWindow):
    def __init__(self, application, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Eddy")

        self.setMinimumSize(600, 400)
        self.setGeometry(
            QStyle.alignedRect(
                Qt.LeftToRight,
                Qt.AlignCenter,
                QSize(1250, 720),
                self.screen().availableGeometry()
            )
        )

        main_widget = TabSystem()
        # main_widget.LastTabClosed.connect(application.quit)
        main_widget.LastTabClosed.connect(main_widget.AddTab)
        self.setCentralWidget(main_widget)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        new_tab_action = QAction(QIcon(icons.TAB_NEW), "New &Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(main_widget.AddTab)
        file_menu.addAction(new_tab_action)
        self.addAction(new_tab_action)

        close_tab_action = QAction(QIcon(icons.TAB_CLOSE), "Close Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(main_widget.CloseCurrentTab)
        file_menu.addAction(close_tab_action)
        self.addAction(close_tab_action)

        exit_action = QAction(QIcon(icons.QUIT), "&Quit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(application.quit)
        file_menu.addAction(exit_action)
        self.addAction(exit_action)

        toggle_menubar_action = QAction(self)
        toggle_menubar_action.setShortcut("Ctrl+M")
        toggle_menubar_action.triggered.connect(
            lambda: menubar.setVisible(not menubar.isVisible())
        )
        self.addAction(toggle_menubar_action)

        menubar.setVisible(False)

        main_widget.AddTab()


def run():
    application = QApplication(sys.argv)
    # application.setWindowIcon(QIcon(…))

    main_window = MainWindow(application)

    main_window.show()

    sys.exit(application.exec_())

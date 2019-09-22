import sys

from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QApplication, QMainWindow, QAction

from eddy.gui.tabs import TabSystem


class MainWindow(QMainWindow):
    def __init__(self, application, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setWindowTitle("Eddy")

        self.setMinimumSize(600, 400)
        # screen_space = application.desktop().availableGeometry(self)
        # self.resize(screen_space.width() * 0.5, screen_space.height() * 0.5)
        self.resize(1200, 800)

        main_widget = TabSystem()
        # main_widget.LastTabClosed.connect(application.quit)
        main_widget.LastTabClosed.connect(main_widget.AddTab)
        self.setCentralWidget(main_widget)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        new_tab_action = QAction(QIcon.fromTheme("tab-new"), "New &Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(main_widget.AddTab)
        file_menu.addAction(new_tab_action)

        exit_action = QAction(QIcon.fromTheme("application-exit"), "&Quit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(application.quit)
        file_menu.addAction(exit_action)


def run():
    application = QApplication(sys.argv)
    # application.setWindowIcon(QIcon(…))

    main_window = MainWindow(application)

    main_window.show()

    sys.exit(application.exec_())

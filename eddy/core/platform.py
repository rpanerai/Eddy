import os
import webbrowser

from PySide2.QtCore import QUrl
from PySide2.QtGui import QDesktopServices


def OpenFolder(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def OpenInFolder(path):
    os.system("dolphin --select '" + path + "' &")

def OpenLocalDocument(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def OpenOnlineDocument(url):
    os.system("okular " + url + " &")

def OpenWebURL(url):
    webbrowser.open(url)

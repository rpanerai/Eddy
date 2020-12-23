import os
import shutil
import sys
import subprocess
import webbrowser

from PySide2.QtCore import QUrl, QDir, QProcess
from PySide2.QtGui import QDesktopServices


def IsInstalled(tool):
    return shutil.which(tool) is not None

def WhichPlatform():
    if sys.platform in ["win32", "cygwin"]:
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"

def WhichLinuxDesktop():
    session = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "kde" in session:
        return "kde"
    if "gnome" in session:
        return "gnome"
    return "other"

def OpenFolder(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def OpenInFolder(path):
    dir_ = os.path.dirname(path)
    platform = WhichPlatform()
    if platform == "windows":
        args = ["/select,", QDir.toNativeSeparators(path)]
        QProcess.startDetached("explorer", args)
        return
    if platform == "mac":
        args = [
            "-e", "tell application \"Finder\"",
            "-e", "activate",
            "-e", "select POSIX file \"" + path + "\"",
            "-e", "end tell",
            "-e", "return"
        ]
        QProcess.execute('/usr/bin/osascript', args)
        return
    if platform == "linux" and WhichLinuxDesktop() == "kde" and IsInstalled("dolphin"):
        os.system("dolphin --select '" + path + "' &")
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(dir_))

def OpenLocalDocument(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))

def OpenOnlineDocument(url):
    if WhichPlatform() == "linux":
        command = "xdg-mime query default application/pdf".split(" ")
        stdout = subprocess.run(command, stdout=subprocess.PIPE).stdout.decode("UTF-8")
        if "evince" in stdout:
            os.system("evince " + url + " &")
            return
        if "okular" in stdout:
            os.system("okular " + url + " &")
            return
    QDesktopServices.openUrl(QUrl(url))

def OpenWebURL(url):
    webbrowser.open(url)

from pathlib import Path
import os
import shutil
import sys
import subprocess
import webbrowser

from PySide2.QtCore import QUrl, QDir, QProcess
from PySide2.QtGui import QDesktopServices


ROOT_DIR = Path(__file__).resolve().parent.parent.parent

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
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

def OpenInFolder(path):
    platform = WhichPlatform()
    if platform == "windows":
        args = ["/select,", QDir.toNativeSeparators(str(path))]
        QProcess.startDetached("explorer", args)
        return
    if platform == "mac":
        args = [
            "-e", f"tell application \"Finder\"",
            "-e", f"activate",
            "-e", f"select POSIX file \"{path}\"",
            "-e", f"end tell",
            "-e", f"return"
        ]
        QProcess.execute('/usr/bin/osascript', args)
        return
    if platform == "linux" and WhichLinuxDesktop() == "kde" and IsInstalled("dolphin"):
        os.system(f"dolphin --select '{path}' &")
        return
    dir_ = path.parent
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(dir_)))

def OpenLocalDocument(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

def OpenOnlineDocument(url):
    if WhichPlatform() == "linux":
        command = "xdg-mime query default application/pdf".split(" ")
        stdout = subprocess.run(command, stdout=subprocess.PIPE).stdout.decode("UTF-8")
        if "evince" in stdout:
            os.system(f"evince {url} &")
            return
        if "okular" in stdout:
            os.system(f"okular {url} &")
            return
    QDesktopServices.openUrl(QUrl(url))

def OpenWebURL(url):
    webbrowser.open(url)

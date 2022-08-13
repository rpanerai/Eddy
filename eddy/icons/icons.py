from pathlib import Path

from PySide2.QtCore import QFileInfo
from PySide2.QtWidgets import QFileIconProvider


ICONS_FOLDER = Path(__file__).resolve().parent

ARXIV = str(ICONS_FOLDER / "arxiv.ico")
DOI = str(ICONS_FOLDER / "doi.ico")
INSPIRE = str(ICONS_FOLDER / "inspire.ico")

BREEZE_FOLDER = ICONS_FOLDER / "breeze"

ADD = str(BREEZE_FOLDER / "add.svg")
DATABASE = str(BREEZE_FOLDER / "database.svg")
DELETE = str(BREEZE_FOLDER / "delete.svg")
FILE = str(BREEZE_FOLDER / "file.svg")
FILES = str(BREEZE_FOLDER / "files.svg")
FILE_ADD = str(BREEZE_FOLDER / "file_add.svg")
FILE_CHECK = str(BREEZE_FOLDER / "file_check.svg")
FILE_DELETE = str(BREEZE_FOLDER / "file_delete.svg")
FILTER = str(BREEZE_FOLDER / "filter.svg")
LOCAL = str(BREEZE_FOLDER / "local.svg")
OPEN = str(BREEZE_FOLDER / "open.svg")
PDF = str(BREEZE_FOLDER / "pdf.svg")
QUIT = str(BREEZE_FOLDER / "quit.svg")
RELOAD = str(BREEZE_FOLDER / "reload.svg")
SAVE = str(BREEZE_FOLDER / "save.svg")
SEARCH = str(BREEZE_FOLDER / "search.svg")
STOP = str(BREEZE_FOLDER / "stop.svg")
TAB_CLOSE = str(BREEZE_FOLDER / "tab_close.svg")
TAB_NEW = str(BREEZE_FOLDER / "tab_new.svg")
TAG = str(BREEZE_FOLDER / "tag.svg")
TAG_NEW = str(BREEZE_FOLDER / "tag_new.svg")
WEB = str(BREEZE_FOLDER / "web.svg")

def FileIcon(file_):
    return QFileIconProvider().icon(QFileInfo(file_))

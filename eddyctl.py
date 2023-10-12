#!/usr/bin/env python

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import argparse
from urllib.request import urlretrieve
from zipfile import ZipFile

from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.database.tags import TagsTable


KATEX_URL = "https://github.com/KaTeX/KaTeX/releases/download/v0.16.9/katex.zip"
EXTERN_FOLDER = ROOT_DIR / "extern"

def NewDatabase(file):
    if file.exists():
        print(f"{sys.argv[0]}: Cannot create database file ‘{file}’: File exists")
    else:
        database = Database(file)
        ItemsTable(database).Clear()
        TagsTable(database).Clear()

def KaTeXDownload():
    # TODO: Catch possible errors in the download
    (path, _) = urlretrieve(KATEX_URL)

    # This will overwrite any existing file
    with ZipFile(path, 'r') as zip_file:
        zip_file.extractall(EXTERN_FOLDER)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="commands", required=True, dest="command")

    parser_new = subparsers.add_parser("new", help="creates an Eddy database")
    parser_new.add_argument("FILE", type=Path, help="the file name of the new database")

    parser_katex = subparsers.add_parser("katex-download", help="downloads and installs KaTeX")

    args = parser.parse_args()

    match args.command:
        case "new":
            NewDatabase(args.FILE)
        case "katex-download":
            KaTeXDownload()

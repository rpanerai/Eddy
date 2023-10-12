#!/usr/bin/env python

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

import argparse

from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.database.tags import TagsTable


def NewDatabase(file):
    if file.exists():
        print(f"{sys.argv[0]}: Cannot create database file ‘{file}’: File exists")
    else:
        database = Database(file)
        ItemsTable(database).Clear()
        TagsTable(database).Clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="commands", required=True, dest="command")

    parser_new = subparsers.add_parser("new", help="creates an Eddy database")
    parser_new.add_argument("FILE", type=Path, help="the file name of the new database")

    args = parser.parse_args()

    match args.command:
        case "new":
            NewDatabase(args.FILE)

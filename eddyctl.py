#!/usr/bin/env python

import sys
from pathlib import Path
import argparse
import pathlib

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from eddy.database.database import Database
from eddy.database.items import ItemsTable
from eddy.database.tags import TagsTable

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--new", metavar="FILE", type=pathlib.Path,
        help="creates an Eddy database in FILE")
    args = parser.parse_args()

    if args.new:
        if args.new.exists():
            print(f"{sys.argv[0]}: Cannot create database file ‘{args.new}’: File exists")
        else:
            database = Database(args.new)
            ItemsTable(database).Clear()
            TagsTable(database).Clear()

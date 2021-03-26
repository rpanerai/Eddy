#!/usr/bin/env python

import sys
import os
import getpass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from eddy import customstderr
sys.stderr = customstderr.StandardErr('error.log', getpass.getuser())

from eddy.main import run

run()

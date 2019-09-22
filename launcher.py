import sys
import os

DEVPATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DEVPATH)

from eddy.main import run

run()

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_DATABASES = {
    "Test": os.path.join(ROOT_DIR, "Data/Test/Test.db")
}

WINDOW_SIZE = (1250, 720)
LEFT_PANEL_WIDTH = 200

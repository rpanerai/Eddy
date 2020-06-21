import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

STORAGE_FOLDER = "Files"

LOCAL_DATABASES = {
    "Test": os.path.join(ROOT_DIR, "Data/Test/Test.db")
}

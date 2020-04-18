import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_DATABASES = {
    "Witten": os.path.join(ROOT_DIR, "test.db")
}

import os
import sys
from datetime import datetime
import time
import fcntl
import errno


class SimpleFlock:
    """Provides the simplest possible interface to flock-based file locking. Intended for use with the `with` syntax.
    It will create/truncate/delete the lock file as necessary."""

    # Modified from https://github.com/derpston/python-simpleflock.git

    def __init__(self, path, timeout=None, mode='r+'):
        self._path = path
        self._timeout = timeout
        self._fd = None
        self.mode = mode

    def __enter__(self):
        if self.mode == 'r' and not os.path.isfile(self._path):
            raise FileNotFoundError(f'[Errno 2] No such file or directory: \'{self._path}\'')
        self._fd = open(self._path, 'a+')
        start_lock_search = time.time()
        while True:
            try:
                fcntl.lockf(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Lock acquired!
                if 'w' in self.mode:
                    self._fd.truncate(0)
                elif 'a' in self.mode:
                    self._fd.seek(0,2)
                elif 'r' in self.mode:
                    self._fd.seek(0)
                return self._fd
            except (OSError, IOError) as ex:
                if ex.errno not in [errno.EAGAIN, errno.EACCES]:
                    # Resource temporarily unavailable
                    raise
                elif self._timeout is not None and time.time() > (start_lock_search + self._timeout):
                    # Exceeded the user-specified timeout.
                    raise

            # It would be nice to avoid an arbitrary sleep here, but spinning
            # without a delay is also undesirable.
            time.sleep(.1)

    def __exit__(self, *args):
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        self._fd.close()
        self._fd = None


class StandardErr:
    """Redirects stderr to a logfile with timestamps. Locks the file to allow for concurrent processes to generate
    error logs. """

    def __init__(self, path, username):

        # Puts error.log in the path of main, and if there is no main it puts it here
        main_module = sys.modules['__main__']
        if hasattr(main_module, '__file__'):
            self.path = os.path.join(os.path.dirname(os.path.realpath(main_module.__file__)), path)
        else:
            self.path = os.path.join(os.path.dirname(os.path.realpath(__file__)), path)
        self.last_write = datetime(1999, 1, 1)
        self.username = username

    def write(self, text):

        # Locks the file before writing to it
        with SimpleFlock(self.path, timeout=5, mode='a+') as f:
            n = datetime.now()
            if (n - self.last_write).total_seconds() > 1:
                print(f'\033[1m\033[91mAn error occurred\033[0m, see {self.path}')
                f.write(datetime.now().strftime(f'[%a %d-%m-%Y %H:%M:%S] by {self.username}\n'))
                self.last_write = datetime.now()
            print(text, end='')
            f.write(text)

    def flush(self):
        pass

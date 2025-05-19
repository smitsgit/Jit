import os


class LockfileError(Exception):
    """Base class for lockfile errors."""


class MissingParent(LockfileError):
    """Raised when the parent directory does not exist."""


class NoPermission(LockfileError):
    """Raised when lacking permissions to create the lock file."""


class StaleLock(LockfileError):
    """Raised when trying to write or commit without holding the lock."""


class Lockfile:
    def __init__(self, path: str):
        self.file_path = path
        self.lock_path = os.path.splitext(path)[0] + ".lock"
        self.lock_file = None

    def hold_for_update(self) -> bool:
        if self.lock_file is not None:
            return True  # Already holding the lock

        try:
            fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL)
            self.lock_file = os.fdopen(fd, 'w')
            return True
        except FileExistsError:
            return False
        except FileNotFoundError as e:
            raise MissingParent(str(e))
        except PermissionError as e:
            raise NoPermission(str(e))

    def write(self, content: str) -> None:
        self._ensure_lock_held()
        self.lock_file.write(content)

    def commit(self) -> None:
        self._ensure_lock_held()
        self.lock_file.close()
        os.rename(self.lock_path, self.file_path)
        self.lock_file = None

    def _ensure_lock_held(self):
        if self.lock_file is None:
            raise StaleLock(f"Not holding lock on file: {self.lock_path}")

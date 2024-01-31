import os
import errno
import sys
from fuse import FUSE, FuseOSError, Operations
import sqlite3
import hashlib


class Passthrough(Operations):
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def _full_path(self, partial, primary=True):
        if primary:
            path = os.path.join(self.primary, partial.lstrip("/"))
        else:
            path = os.path.join(self.fallback, partial.lstrip("/"))
        return path

    def getattr(self, path, fh=None):
        try:
            st = os.lstat(self._full_path(path))
        except FileNotFoundError:
            st = os.lstat(self._full_path(path, primary=False))
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                        'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size',
                                                        'st_uid'))

    def create(self, path, mode, fi=None):
        connector = sqlite3.connect('files.db')
        cursor = connector.cursor()
        print("Path:", path)
        hashed_path = self.generate_hash(path)

        # print("Hashed path:", hashed_path)
        cursor.execute('''
            INSERT INTO files (name, hashed_name, is_locked)
            VALUES (?, ?, ?)
        ''', (path, hashed_path, 0))

        connector.commit()
        connector.close()

        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def readdir(self, path, fh):
        dirs = set()
        for p in [self.primary, self.fallback]:
            full_path = os.path.join(p, path.lstrip("/"))
            if os.path.exists(full_path):
                try:
                    for item in os.listdir(full_path):
                        item_full_path = os.path.join(full_path, item)
                        if os.path.isfile(item_full_path):
                            hashed_name = self.generate_hash(item_full_path)
                            connector = sqlite3.connect('files.db')
                            cursor = connector.cursor()
                            try:
                                cursor.execute('''
                                    INSERT INTO files (name, hashed_name, is_locked)
                                    VALUES (?, ?, ?)
                                ''', (item_full_path, hashed_name, 0))
                                connector.commit()  # Don't forget to commit the changes
                            except sqlite3.IntegrityError:
                                pass
                            connector.close()
                        dirs.add(item)
                except FileNotFoundError:
                    pass
        return ['.', '..'] + list(dirs)

    def read(self, path, size, offset, fh):
        if not self.acquire_file_lock(path):
            return -1
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            full_path = self._full_path(path, primary=False)

        with open(full_path, 'rb') as f:
            f.seek(offset)
            content = f.read(size)
            self.release_file_lock(path)
            return content

    def write(self, path, buf, offset, fh):
        if not self.acquire_file_lock(path):
            return -1
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            full_path = self._full_path(path, primary=False)

        mode = 'r+b' if os.path.exists(full_path) else 'wb'
        with open(full_path, mode) as f:
            f.seek(offset)
            written = f.write(buf)
            self.release_file_lock(path)
            return written

    def unlink(self, path):
        connector = sqlite3.connect('files.db')
        cursor = connector.cursor()
        cursor.execute('''
            DELETE FROM files
            WHERE name = ?
        ''', (path,))
        connector.commit()
        connector.close()

        primary_path = self._full_path(path)
        fallback_path = self._full_path(path, primary=False)

        if os.path.exists(primary_path):
            os.unlink(primary_path)
        elif os.path.exists(fallback_path):
            os.unlink(fallback_path)
        else:
            raise FuseOSError(errno.ENOENT)

    def generate_hash(self, value):
        hash_algorithm = hashlib.sha256()
        value_bytes = str(value).encode('utf-8')
        hash_algorithm.update(value_bytes)
        hash_value = hash_algorithm.hexdigest()

        return hash_value

    def acquire_file_lock(self, path):
        hashed_path = self.generate_hash(path)
        with sqlite3.connect('files.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_locked FROM files WHERE hashed_name = ?", (hashed_path,))
            result = cursor.fetchone()

            if result is None:
                pass
            elif result[0] == 1:
                print("Error: The file is currently in use by someone else, try again later.")
                return False
            cursor.execute("UPDATE files SET is_locked = 1 WHERE hashed_name = ?", (hashed_path,))
            conn.commit()
            return True

    def release_file_lock(self, path):
        hashed_path = self.generate_hash(path)
        with sqlite3.connect('files.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE files SET is_locked = 0 WHERE hashed_name = ?", (hashed_path,))
            conn.commit()


def main(mountpoint, primary, fallback):
    username = os.getlogin()
    print("Username:", username)

    connector = sqlite3.connect('files.db')
    cursor = connector.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            "id" INTEGER PRIMARY KEY,
            "name" TEXT,
            "hashed_name" TEXT UNIQUE,       
            "is_locked" INTEGER
        )
    ''')

    connector.commit()
    connector.close()

    FUSE(Passthrough(primary, fallback), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])

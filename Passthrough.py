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
            try:
                dirs.update(os.listdir(p + path))
            except FileNotFoundError:
                pass
        return ['.', '..'] + list(dirs)

    def read(self, path, size, offset, fh):
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            full_path = self._full_path(path, primary=False)

        with open(full_path, 'rb') as f:
            f.seek(offset)
            return f.read(size)

    def write(self, path, buf, offset, fh):
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            full_path = self._full_path(path, primary=False)

        # Open the file in binary read-write mode, don't truncate (r+b)
        # If the file doesn't exist, open in write mode which will create the file (wb)
        mode = 'r+b' if os.path.exists(full_path) else 'wb'
        with open(full_path, mode) as f:
            f.seek(offset)
            written = f.write(buf)
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

        # Check if the file exists in the primary filesystem
        if os.path.exists(primary_path):
            os.unlink(primary_path)
        elif os.path.exists(fallback_path):
            # Optionally handle the case where the file is in the fallback filesystem
            os.unlink(fallback_path)
        else:
            raise FuseOSError(errno.ENOENT)
        
    def generate_hash(self, value):
        hash_algorithm = hashlib.sha256()
        value_bytes = str(value).encode('utf-8')
        hash_algorithm.update(value_bytes)
        hash_value = hash_algorithm.hexdigest()

        return hash_value    

def main(mountpoint, primary, fallback):
    username = os.getlogin()
    print("Username:", username)

    connector = sqlite3.connect('files.db')
    cursor = connector.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            "id" INTEGER PRIMARY KEY,
            "name" TEXT,
            "hashed_name" TEXT,       
            "is_locked" INTEGER
        )
    ''')

    connector.commit()
    connector.close()

    FUSE(Passthrough(primary, fallback), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])

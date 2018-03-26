import os
import errno
import stat
import logging
from time import time, mktime, strptime

from fuse import FuseOSError, Operations, LoggingMixIn


logger = logging.getLogger('dochub_fs')

def wrap_enoent(func):
    """
    @brief      Transform KeyErrors happening inside func into ENOENT
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            raise FuseOSError(errno.ENOENT)
    return wrapper


class Node:
    """
    @brief      Map Dochub API nodes onto filesystem nodes.
                Takes a JSON serialized representation of Dochub objects,
                and expose useful attributes
    """
    def __init__(self, serialized, fs):
        self.serialized = serialized
        self.fs = fs

    def sub_node(self, serialized):
        return Node(serialized, self.fs)

    @property
    def is_category(self):
        return 'courses' in self.serialized and 'children' in self.serialized

    @property
    def is_course(self):
        return 'slug' in self.serialized

    @property
    def is_document(self):
        return 'votes' in self.serialized

    @property
    def is_dir(self):
        return self.is_category or self.is_course

    @property
    def name(self):
        if self.is_course:
            return "{slug} {name}".format(**self.serialized)
        if self.is_document:
            return "{name}{file_type}".format(**self.serialized)
        return self.serialized['name']

    @property
    def size(self):
        return self.serialized.get('file_size', 4096)

    @property
    def ctime(self):
        if 'date' in self.serialized:
            t = strptime(self.serialized['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
            return int(mktime(t))
        return self.fs.mount_time

    atime = ctime
    mtime = ctime

    def stat(self):
        mode = (0o755|stat.S_IFDIR) if self.is_dir else (0o644|stat.S_IFREG)
        return {
            'st_mode': mode,
            'st_ctime': self.ctime,
            'st_mtime': self.mtime,
            'st_atime': self.atime,
            'st_nlink': 1,
            'st_uid': self.fs.uid,
            'st_gid': self.fs.gid,
            'st_size': self.size,
        }

    @property
    def children(self):
        if not self.is_dir:
            raise ValueError(
                "Attempt to get direcctory children on non-directory %s" %
                self.serialized['name']
            )

        if self.is_category:
            children = self.serialized['children'] + self.serialized['courses']
        elif self.is_course:
            r = self.fs.api.get_course(self.serialized['slug'])
            children = r['document_set']
        return {child.name: child for child in map(self.sub_node, children)}

    @property
    def content(self):
        if not self.is_document:
            raise ValueError(
                "Attempt to get file content on non-file %s" %
                self.serialized['name']
            )

        return self.fs.api.get_document(self.serialized['id'])

    def find(self, path):
        if len(path) > 0:
            return self.children[path[0]].find(path[1:])
        else:
            return self


class DochubFileSystem(LoggingMixIn, Operations):
    """
    @brief      Implementation of filesystem operations
    """
    def __init__(self, api):
        self.api = api
        self.mount_time = int(time())
        self.uid, self.gid = os.getuid(), os.getgid()

        tree = self.api.get_tree()
        assert len(tree) == 1
        self.tree = Node(tree[0], self)

    @wrap_enoent
    def find_path(self, path):
        components = [x for x in path.strip('/').split('/') if x != '']
        return self.tree.find(components)

    def getattr(self, path, fh=None):
        return self.find_path(path).stat()

    def readdir(self, path, fh=None):
        node = self.find_path(path)
        return ['.', '..'] + list(node.children.keys())

    def read(self, path, size, offset, fh=None):
        node = self.find_path(path)
        return node.content[offset:offset+size]

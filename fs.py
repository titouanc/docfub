import os
import errno
import stat
import logging
from io import BytesIO
from time import time, mktime, strptime

from fuse import FuseOSError, Operations, LoggingMixIn


logger = logging.getLogger('dochub_fs')

def wrap_errno(func):
    """
    @brief      Transform Exceptions happening inside func into meaningful
                errno if possible
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            raise FuseOSError(errno.ENOENT)
        except ValueError:
            raise FuseOSError(errno.EINVAL)
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

    def getattr(self):
        mode = (0o500|stat.S_IFDIR) if self.is_dir else (0o400|stat.S_IFREG)
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


class DocumentUpload:
    """
    @brief      A file created locally, being buffered before posting to the
                server. 
    """
    def __init__(self, fs, course, name):
        self.fs = fs
        self.io = BytesIO()
        self.ctime = time()
        self.mtime, self.atime = self.ctime, self.ctime
        self.name, self.ext = name.split('.', 1)
        self.course = course

    @property
    def size(self):
        return self.io.tell()

    def getattr(self):
        return {
            'st_mode': 0o200 | stat.S_IFREG,
            'st_ctime': self.ctime,
            'st_mtime': self.mtime,
            'st_atime': self.atime,
            'st_nlink': 1,
            'st_uid': self.fs.uid,
            'st_gid': self.fs.gid,
            'st_size': self.size,
        }

    def do_upload(self):
        self.io.seek(0)
        self.fs.api.add_document(course_slug=self.course.serialized['slug'],
                                 name=self.name, file=self.io,
                                 filename='.'.join([self.name, self.ext]))


def to_breadcrumbs(path):
    res = []
    prefix, name = os.path.split(path)
    while name:
        res = [name] + res
        prefix, name = os.path.split(prefix)
    return res



class DochubFileSystem(LoggingMixIn, Operations):
    """
    @brief      Implementation of filesystem operations
    """
    def __init__(self, api):
        self.api = api
        self.mount_time = int(time())
        self.uid, self.gid = os.getuid(), os.getgid()
        self.uploads = {}

        tree = self.api.get_tree()
        assert len(tree) == 1
        self.tree = Node(tree[0], self)

    @wrap_errno
    def find_path(self, path):
        if path in self.uploads:
            return self.uploads[path]
        return self.tree.find(to_breadcrumbs(path))

    def getattr(self, path, fh=None):
        return self.find_path(path).getattr()

    def readdir(self, path, fh=None):
        node = self.find_path(path)
        return ['.', '..'] + list(node.children.keys())

    def read(self, path, size, offset, fh=None):
        node = self.find_path(path)
        return node.content[offset:offset+size]

    def create(self, path, mode):
        directory, name = os.path.split(path)
        parent = self.find_path(directory)
        if not parent.is_course:
            raise Exception()

        if (mode & stat.S_IFREG):
            logger.info("Create file %s", path)
            self.uploads[path] = DocumentUpload(self, parent, name)
        return 3

    def release(self, path, fh):
        """
        @brief      When the file is closed, perform the actual upload to DocHub
        """
        if path in self.uploads and self.uploads[path].size > 0:
            upload = self.uploads.pop(path)
            upload.do_upload()

    def write(self, path, data, offset, fh=None):
        if path in self.uploads:
            upload = self.uploads[path]
            if offset != upload.size:
                upload.io.seek(offset)
            self.uploads[path].io.write(data)
            return len(data)
        return -1

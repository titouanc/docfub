from sys import argv

from fuse import FUSE

from dochub_api import DochubAPI
from fs import DochubFileSystem
import config

if len(argv) != 2:
    print('usage: %s <mountpoint>' % argv[0])
    exit(1)

api = DochubAPI(base_url=config.BASE_URL,
                username=config.USERNAME,
                password=config.PASSWORD)
fuse = FUSE(DochubFileSystem(api=api), argv[1], foreground=True)
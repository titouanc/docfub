# The DocHub site to which you want to connect
BASE_URL = "https://dochub.be"

# Get your own on https://dochub.be/users/settings/#foo
TOKEN = "fillme"

try:  # IGNORE
    from local_config import *  # IGNORE
except ImportError:  # IGNORE
    pass  # IGNORE

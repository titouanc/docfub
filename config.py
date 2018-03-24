BASE_URL = "http://localhost:8000"
USERNAME = "test"
PASSWORD = "test"

try:  # IGNORE
    from local_config import *  # IGNORE
except ImportError:  # IGNORE
    pass  # IGNORE

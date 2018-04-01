import logging
import requests

logger = logging.getLogger("dochub_api")


def memoize(func):
    memoized = {}
    def wrapper(*args):
        if args not in memoized:
            memoized[args] = func(*args)
        return memoized[args]
    return wrapper


class DochubAPI(requests.Session):
    def __init__(self, token, base_url, *args, **kwargs):
        self.base_url = base_url
        super(DochubAPI, self).__init__(*args, **kwargs)
        self.headers['Authorization'] = 'Token ' + token

    def post(self, path, *args, **kwargs):
        full_url = self.base_url + path
        r = super(DochubAPI, self).post(full_url, *args, **kwargs)
        r.raise_for_status()
        return r

    def get(self, path, *args, **kwargs):
        full_url = self.base_url + path
        r = super(DochubAPI, self).get(full_url, *args, **kwargs)
        r.raise_for_status()
        return r

    def get_tree(self):
        logger.info("Download site tree")
        return self.get("/api/tree/").json()

    @memoize
    def get_course(self, slug):
        logger.info("Download course page %s", slug)
        api_path = "/api/courses/{slug}/".format(slug=slug)
        return self.get(api_path).json()

    @memoize
    def get_document(self, doc_id):
        logger.info("Download document %d", doc_id)
        api_path = "/api/documents/{doc_id}/original/".format(doc_id=doc_id)
        return self.get(api_path).content

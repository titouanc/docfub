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
    def __init__(self, base_url, username, password, *args, **kwargs):
        self.courses_cache = {}
        self.base_url = base_url
        super(DochubAPI, self).__init__(*args, **kwargs)
        self.get('/syslogin')
        self.post("/syslogin", data={
            'username': username,
            'password': password,
        })

    @property
    def _csrf(self):
        for key, val in getattr(self, 'cookies', {}).items():
            if 'csrf' in key:
                return val

    def post(self, path, *args, **kwargs):
        full_url = self.base_url + path
        if 'data' in kwargs and self._csrf:
            kwargs['data']['csrfmiddlewaretoken'] = self._csrf
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
        return self.get("/catalog/course_tree.json").json()

    @memoize
    def get_course(self, slug):
        logger.info("Download course page %s", slug)
        api_path = "/api/courses/{slug}/".format(slug=slug)
        return self.get(api_path).json()

    @memoize
    def get_document(self, doc_id):
        logger.info("Download document %d", doc_id)
        api_path = "/documents/{doc_id}/original".format(doc_id=doc_id)
        return self.get(api_path).content


if __name__ == "__main__":
    api = DochubAPI()
    print(api.get_tree())

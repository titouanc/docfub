import logging
import platform
import functools

import requests

from version import VERSION


logger = logging.getLogger("dochub_api")


class DochubAPI(requests.Session):
    def __init__(self, token, base_url, *args, **kwargs):
        self.base_url = base_url
        super(DochubAPI, self).__init__(*args, **kwargs)
        self.headers['Authorization'] = 'Token ' + token
        self.headers['User-Agent'] = 'docfub {version} {os} {arch}'.format(
            version=VERSION,
            os=platform.system(),
            arch=platform.machine(),
        )

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

    @functools.lru_cache(maxsize=256)
    def get_course(self, slug):
        logger.info("Download course page %s", slug)
        api_path = "/api/courses/{slug}/".format(slug=slug)
        return self.get(api_path).json()

    @functools.lru_cache(maxsize=64)
    def get_document(self, doc_id):
        logger.info("Download document %d", doc_id)
        api_path = "/api/documents/{doc_id}/original/".format(doc_id=doc_id)
        return self.get(api_path).content

    def add_document(self, course_slug, name, filename, file):
        logger.info("Upload document %s in %s", name, course_slug)
        api_path = "/api/documents/"
        try:
            res = self.post(api_path,
                            data={'name': name, 'course': course_slug,
                                  'description': '_Uploadé avec docfub_'},
                            files={'file': (filename, file)})
        except:
            logger.exception("Upload document %s in %s", name, course_slug)
            raise

        # We modified the course, so we need to evict its cache.
        # functools.clear_cache currently does not allow to evict a single
        # entry, therefore we have to clear everything
        self.get_course.cache_clear()
        return res

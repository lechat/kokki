from __future__ import with_statement
import logging

__all__ = ["Source", "Template", "StaticFile", "DownloadSource"]

import hashlib
import os
import urllib2
import urlparse
from kokki import environment
from kokki.exceptions import Fail

def load_class(class_name, *args, **kwargs):
    parts = class_name.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m(*args, **kwargs)

class Source(object):
    def get_content(self):
        raise NotImplementedError()

    def get_checksum(self):
        return None

    def __call__(self):
        return self.get_content()

class StaticFile(Source):
    def __init__(self, name, env=None):
        self.name = name
        self.env = env or environment.Environment.get_instance()

    def get_content(self):
        try:
            cookbook, name = self.name.split('/', 1)
        except ValueError:
            raise Fail("[StaticFile(%s)] Path must include cookbook name (e.g. 'nginx/nginx.conf')" % self.name)
        cb = self.env.cookbooks[cookbook]
        path = os.path.join(cb.path, "files", name)
        with open(path, "rb") as fp:
            return fp.read()

class Template(Source):
    ''' Template Factory '''
    def __init__(self, name, variables=None, env=None, engine=None, **kwargs):
        self._log = logging.getLogger("kokki")

        self.name = name

        self.env = env or environment.Environment.get_instance()
        if engine:
            self.template_engine_name = engine
        else:
            # Extra care in case template engine is not onfigured at all
            self.template_engine_name = env.config['kokki'].get('template_engine', 'jinja2')

        self._log.debug('Going to use "%s" template engine' % self.template_engine_name)
        self.template_engine = load_class('kokki.providers.template.' + self.template_engine_name.capitalize() + 'Template', name, variables, env, **kwargs)

    def get_content(self):
        return self.template_engine.get_content()

class DownloadSource(Source):
    def __init__(self, url, cache=True, md5sum=None, env=None):
        self.env = env or environment.Environment.get_instance()
        self.url = url
        self.md5sum = md5sum
        self.cache = cache
        if not 'download_path' in env.config:
            env.config.download_path = '/var/tmp/downloads'
        if not os.path.exists(env.config.download_path):
            os.makedirs(self.env.config.download_path)

    def get_content(self):
        filepath = os.path.basename(urlparse.urlparse(self.url).path)
        content = None
        if not self.cache or not os.path.exists(os.path.join(self.env.config.download_path, filepath)):
            web_file = urllib2.urlopen(self.url)
            content = web_file.read()
        else:
            update = False
            with open(os.path.join(self.env.config.download_path, filepath)) as fp:
                content = fp.read()
            if self.md5sum:
                m = hashlib.md5(content)
                md5 = m.hexdigest()
                if md5 != self.md5sum:
                    web_file = urllib2.urlopen(self.url)
                    content = web_file.read()
                    update = True
            if self.cache and update:
                with open(os.path.join(self.env.config.download_path, filepath), 'w') as fp:
                    fp.write(content)
        return content

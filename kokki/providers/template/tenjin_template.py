import os
from kokki import Environment, Source, Fail
import tenjin
from tenjin.helpers import *

class TenjinTemplate(Source):
    def __init__(self, name, variables=None, env=None, **kwargs):
        self.name = name
        self.env = env or Environment.Environment.get_instance()
        self.context = variables.copy() if variables else env.config
        # self.template = TenjinTemplateLoader(self.env).get_source(self.env, self.name)
        self.engine = tenjin.Engine(cache=False, **kwargs)

    def get_source(self, env, template):
        try:
            cookbook, name = template.split('/', 1)
        except ValueError:
            raise Fail("[Template(%s)] Path must include cookbook name (e.g. 'nginx/nginx.conf.j2')" % template)

        cb = self.env.cookbooks[cookbook]
        path = os.path.join(cb.path, "templates", name)
        if not os.path.exists(path):
            raise Fail("Template %s not found at %s. Check File resources in recipe file." % (name, os.path.join(cb.path, "templates")))
        return path

    def get_content(self):
        return self.engine.render(self.get_source(self.env, self.name), self.context)

import os
from kokki import environment, Source
from kokki.exceptions import Fail

try:
    from jinja2 import Environment, BaseLoader, TemplateNotFound
except ImportError:
    class Jinja2Template(Source):
        ''' Error template '''
        def __init__(self, name, variables=None, env=None):
            raise Exception("Jinja2 required for Template")

else:
    class Jinja2TemplateLoader(BaseLoader):
        def __init__(self, env=None):
            self.env = env or environment.Environment.get_instance()

        def get_source(self, environment, template):
            try:
                cookbook, name = template.split('/', 1)
            except ValueError:
                raise Fail("[Template(%s)] Path must include cookbook name (e.g. 'nginx/nginx.conf.j2')" % template)
            cb = self.env.cookbooks[cookbook]
            path = os.path.join(cb.path, "templates", name)
            if not os.path.exists(path):
                raise TemplateNotFound("%s at %s" % (template, path))
            mtime = os.path.getmtime(path)
            with open(path, "rb") as fp:
                source = fp.read().decode('utf-8')
            return source, path, lambda:mtime == os.path.getmtime(path)

    class Jinja2Template(Source):
        def __init__(self, name, variables=None, env=None, **kwargs):
            self.name = name
            self.env = env or environment.Environment.get_instance()
            self.context = variables.copy() if variables else {}
            self.template_env = Environment(loader=Jinja2TemplateLoader(self.env), autoescape=False)
            self.template = self.template_env.get_template(self.name)

        def get_content(self):
            self.context.update(
                env = self.env,
                repr = repr,
                str = str,
                bool = bool,
            )
            rendered = self.template.render(self.context)
            return rendered + "\n" if not rendered.endswith('\n') else rendered



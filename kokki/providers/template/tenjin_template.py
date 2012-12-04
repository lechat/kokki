import os
from kokki import environment, Source, Fail
import logging
import re
import tenjin
from tenjin.helpers import *

class NoShellVarSubstTemplate(tenjin.Template):
    """Same as standard replacemt except that we ignore patters like this: ${...}"""
    s = '(?:\{.*?\}.*?)*'
    EXPR_PATTERN = re.compile(r'#\{(.*?' + s + r')\}|\{=(?:=(.*?)=|(.*?))=\}', re.S)
    del s

    def __init__(self, filename=None, encoding=None, iinput=None, escapefunc=None, tostrfunc=None,
                    indent=None, preamble=None, postamble=None, smarttrim=None, trace=None):
        tenjin.Template.__init__(self, filename, encoding, iinput, escapefunc, tostrfunc,
                                    indent, preamble, postamble, smarttrim, trace)

    def expr_pattern(self):
        return self.EXPR_PATTERN

    def get_expr_and_flags(self, match):
        expr1, expr2, expr3 = match.groups()
        if expr1:
            return expr1, (False, True)   # not escape,  call to_str
        if expr2:
            return expr2, (False, True)   # not escape,  call to_str
        if expr3:
            return expr3, (True,  True)   # call escape, call to_str

class TenjinTemplate(Source):
    def __init__(self, name, variables=None, env=None, **kwargs):
        self._log = logging.getLogger("kokki").getChild('TenjinTemlate')
        self._log.debug('In TenjinTemplate __init__')
        self.name = name
        self.env = env or environment.Environment.get_instance()
        self._log.debug('In TenjinTemplate __init__: before set engine')
        self.context = variables.copy() if variables else env.config
        if 'templateclass' not in kwargs.keys():
            self.engine = tenjin.Engine(cache=False, templateclass=NoShellVarSubstTemplate, **kwargs)
        else:
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

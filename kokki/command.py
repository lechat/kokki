
import logging
import os
import sys
from optparse import OptionParser

from kokki.kitchen import Kitchen

def build_parser():
    parser = OptionParser(usage="Usage: %prog [options] <role> ...")
    parser.add_option("-f", "--file", dest="filename",
        help="Look for the command in FILE. If file name is not specified, will look for 'kitchen.py'", metavar="FILE", default="kitchen.py")
    parser.add_option("-l", "--load", dest="config",
            help="Load dumped kitchen from FILE. Optional prefix fmt: specifies file type (yaml, pickle or json). Default format is yaml.", metavar="FILE", default=None)
    parser.add_option("-d", "--dump", dest="dump",
        help = "Dump a serialized representation of what would be run"
               " to FILE (default to YAML, can specify <format>:<filename>"
               " e.g. pickle:kitchen.dump)", metavar="FILE", default=None)
    parser.add_option("-o", "--override", dest="overrides", help="Config overrides (key=value)", action="append", default=[])
    parser.add_option("-v", "--verbose", dest="verbose", default=False, action="store_true")
    return parser

def load_kitchen_from_dump(options_config, logger):
    logger.debug('Config file specified as %s' % options_config)
    if ':' in options_config:
        fmt, filename = options_config.split(':', 1)
    else:
        logger.debug('Assuming that config is in yaml format')
        fmt, filename = "yaml", options_config

    if fmt == "yaml":
        logger.debug(msg='Config file format is yaml')
        import yaml
        with open(filename, "rb") as fp:
            return yaml.load(fp.read())
    elif fmt == "pickle":
        logger.debug(msg='Config file format is pickle')
        import cPickle as pickle
        with open(filename, "rb") as fp:
            return pickle.load(fp)
    elif fmt == "json":
        logger.debug(msg='Config file format is json')
        import jsonpickle
        with open(filename, "rb") as fp:
            return jsonpickle.decode(fp.read())
    else:
        sys.stderr.write("Unknown config format specified '%s'. Can only work with yaml, json or pickle \n" % fmt)
        sys.exit(1)

def load_kitchens(options_filename, args, logger):
    logger.debug('Config file not specified, trying to read "kitchen.py"')
    path = os.path.abspath(options_filename)
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    if path not in sys.path:
        sys.path.insert(0, path)

    if os.path.isdir(options_filename):
        files = [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.endswith('.py')]
    else:
        files = [options_filename]

    logger.debug('Processing %s as kitchen file(s)' % files)

    globs = {}
    file_found = False
    for fname in files:
        globs["__file__"] = os.path.abspath(fname)
        if os.path.exists(globs["__file__"]):
            file_found = True
            with open(fname, "rb") as fp:
                logger.debug('Compiling %s' % fname)
                source = fp.read()
                exec compile(source, fname, 'exec') in globs
            del globs['__file__']

    if not file_found:
        sys.stderr.write("Need to have 'kitchen.py' or other files specified by -f parameter")
        sys.exit(1)

    kit = Kitchen()
    roles = []
    for c in args:
        try:
            roles.append(globs[c])
        except KeyError:
            sys.stderr.write("Function for role '%s' not found in config\n" % c)
            sys.exit(1)
    for r in roles:
        r(kit)

    return kit

def produce_dump(options_dump, kitchen, logger):
    logger.debug('Dumping config files')
    if ':' in options_dump:
        fmt, filename = options_dump.split(':', 1)
    else:
        logger.debug('Assuming format is yaml')
        fmt, filename = "yaml", options_dump
    if fmt == "yaml":
        import yaml
        if filename == "-":
            print yaml.dump(kitchen)
        else:
            with open(filename, "wb") as fp:
                yaml.dump(kitchen, fp)
    elif fmt == "pickle":
        import cPickle as pickle
        if filename == "-":
            print pickle.dumps(kitchen)
        else:
            with open(filename, "wb") as fp:
                pickle.dump(kitchen, fp, pickle.HIGHEST_PROTOCOL)
    elif fmt == "json":
        import jsonpickle
        if filename == "-":
            print jsonpickle.encode(kitchen)
        else:
            with open(filename, "wb") as fp:
                fp.write(jsonpickle.encode(kitchen))
    else:
        sys.stderr.write("Unknown config format specified '%s'. Can only work with yaml or pickle \n" % fmt)
        sys.exit(1)

    sys.exit(0)

def main():
    parser = build_parser()
    options, args = parser.parse_args()
    if not args and not options.config:
        parser.error("must specify at least one command")

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('kokki')

    logger.debug('Options: %s' % options)

    if options.verbose:
        logger.setLevel(logging.DEBUG)

    if options.config:
        kitchen = load_kitchen_from_dump(options.config, logger)
    else:
        kitchen = load_kitchens(options.filename, args, logger)

    logger.debug('Processing overrides: %s' % options.overrides)
    for over in options.overrides:
        name, value = over.split('=', 1)
        kitchen.update_config({name: value})

    if options.dump:
        produce_dump(options.dump, kitchen, logger)

    logger.debug('Configuration is done. Visiting kitchen.')
    kitchen.run()
    logger.info('All done')

if __name__ == "__main__":
    main()

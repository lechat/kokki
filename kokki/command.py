
import logging
import os
import sys
from optparse import OptionParser

from kokki.kitchen import Kitchen

def build_parser():
    parser = OptionParser(usage="Usage: %prog [options] <command> ...")
    parser.add_option("-f", "--file", dest="filename",
        help="Look for the command in FILE", metavar="FILE", default="kitchen.py")
    parser.add_option("-l", "--load", dest="config",
        help="Load dumped kitchen from FILE", metavar="FILE", default=None)
    parser.add_option("-d", "--dump", dest="dump",
        help = "Dump a serialized representation of what would be run"
               " to FILE (default to YAML, can specify <format>:<filename>"
               " e.g. pickle:kitchen.dump)", metavar="FILE", default=None)
    parser.add_option("-o", "--override", dest="overrides", help="Config overrides (key=value)", action="append", default=[])
    parser.add_option("-v", "--verbose", dest="verbose", default=False, action="store_true")
    return parser

def main():
    parser = build_parser()
    options, args = parser.parse_args()
    if not args and not options.config:
        parser.error("must specify at least one command")

    logging.basicConfig(level=logging.INFO)
    if options.verbose:
        logger = logging.getLogger('kokki')
        logger.setLevel(logging.DEBUG)

    if options.config:
        logger.debug('Config file specified as %s' % options.config)
        if ':' in options.config:
            fmt, filename = options.config.split(':', 1)
        else:
            logger.debug('Assuming that config is in yaml format')
            fmt, filename = "yaml", options.config
        if fmt == "yaml":
            logger.debug(msg='Config file format is yaml')
            import yaml
            with open(options.config, "rb") as fp:
                kit = yaml.load(fp.read())
        elif fmt == "pickle":
            logger.debug(msg='Config file format is pickle')
            import cPickle as pickle
            with open(filename, "rb") as fp:
                kit = pickle.load(fp)
        else: 
            sys.stderr.write("Unknown config format specified '%s'. Can only work with yaml or pickle \n" % fmt)
            sys.exit(1)
                
            
    else:
        logger.debug('Config file not specified, trying to read "kitchen.py"')
        path = os.path.abspath(options.filename)
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        if path not in sys.path:
            sys.path.insert(0, path)

        if os.path.isdir(options.filename):
            files = [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.endswith('.py')]
        else:
            files = [options.filename]

        logger.debug('Processing %s as kitchen file(s)' % files)

        globs = {}
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
    
    logger.debug('Processing overrides: %s' % options.overrides)
    for over in options.overrides:
        name, value = over.split('=', 1)
        try:
            value = int(value)
        except ValueError:
            pass
        kit.update_config({name: value})
    
    if options.dump:
        logger.debug('Dumping config files')
        if ':' in options.dump:
            fmt, filename = options.dump.split(':', 1)
        else:
            logger.debug('Assuming format is yaml')
            fmt, filename = "yaml", options.dump
        if fmt == "yaml":
            import yaml 
            if filename == "-":
                print yaml.dump(kit)
            else:
                with open(filename, "wb") as fp:
                    yaml.dump(kit, fp)
        elif fmt == "pickle":
            import cPickle as pickle
            if filename == "-":
                print pickle.dumps(kit)
            else:
                with open(filename, "wb") as fp:
                    pickle.dump(kit, fp, pickle.HIGHEST_PROTOCOL)
        else: 
            sys.stderr.write("Unknown config format specified '%s'. Can only work with yaml or pickle \n" % fmt)
            sys.exit(1)

        sys.exit(0)

    logger.debug('Configuration is done. Visiting kitchen.')
    kit.run()

if __name__ == "__main__":
    main()

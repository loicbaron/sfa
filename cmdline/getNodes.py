#!/usr/bin/python

import sys
import os
from optparse import OptionParser
from pprint import pprint
from types import StringTypes
from geni.util.rspec import Rspec

def create_parser():
    command = sys.argv[0]
    argv = sys.argv[1:]
    usage = "%(command)s [options]" % locals()
    description = """getNodes will open a rspec file and print all key/values, or filter results based on a given key or set of keys."""
    parser = OptionParser(usage=usage,description=description)
    parser.add_option("-i", "--infile", dest="infile", default=None,  help = "record file path")
    parser.add_option("-f", "--filter", dest="filter", default=None,  help = "record file path")
    parser.add_option("-r", "--recursive", dest="recursive", default=False,  action="store_true", help = "record file path")
   
    return parser    

print 

def print_dict(rdict, counter=1):
    lists = []
    if not isinstance(rdict, dict):
        raise "%s not a dict" % rdict 
    for (key, value) in rdict.items():
        if isinstance(value, StringTypes):
            print "    " * counter + "%s: %s" % (key, value)
        elif isinstance(value, list):
            for listitem in value:
                if isinstance(listitem, dict):
                    lists.append((key, listitem))
        elif isinstance(value, dict):
            lists.append((key, value)) 

    for (key, listitem) in lists:
        if isinstance(listitem, dict):
            print "    " * (counter - 1) + key
            print_dict(listitem, counter+1)   
        

def main():
    parser = create_parser(); 
    (options, args) = parser.parse_args()

    if not options.infile:
        print "Rspec file not specified"
        return 
        
    rspec = Rspec()
    try:
        rspec.parseFile(options.infile)
    except:
        print "Error reading rspec file"

    if options.filter:
        filter_name = options.filter
        rspec_dicts = rspec.getDictsByTagName(options.filter)
        rspec_dict = {filter_name: rspec_dicts}
    else:
        rspec_dict = rspec.toDict()     

    print_dict(rspec_dict, options.recursive)

    return

if __name__ == '__main__':
    try: main()
    except Exception, e:
        raise
        print e

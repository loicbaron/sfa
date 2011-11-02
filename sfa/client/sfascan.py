#!/usr/bin/env python

import sys, os.path
import pickle
import time
import socket
import traceback
from urlparse import urlparse

import pygraphviz

from optparse import OptionParser

from sfa.client.sfi import Sfi
from sfa.util.sfalogging import logger, DEBUG
import sfa.client.xmlrpcprotocol as xmlrpcprotocol

def url_hostname_port (url):
    if url.find("://")<0:
        url="http://"+url
    parsed_url=urlparse(url)
    # 0(scheme) returns protocol
    default_port='80'
    if parsed_url[0]=='https': default_port='443'
    # 1(netloc) returns the hostname+port part
    parts=parsed_url[1].split(":")
    # just a hostname
    if len(parts)==1:
        return (url,parts[0],default_port)
    else:
        return (url,parts[0],parts[1])

### a very simple cache mechanism so that successive runs (see make) 
### will go *much* faster
### assuming everything is sequential, as simple as it gets
### { url -> (timestamp,version)}
class VersionCache:
    def __init__ (self, filename=None, expires=60*60):
        # default is to store cache in the same dir as argv[0]
        if filename is None:
            filename=os.path.join(os.path.dirname(sys.argv[0]),"sfascan-version-cache.pickle")
        self.filename=filename
        self.expires=expires
        self.url2version={}
        self.load()

    def load (self):
        try:
            infile=file(self.filename,'r')
            self.url2version=pickle.load(infile)
            infile.close()
        except:
            logger.info("Cannot load version cache, restarting from scratch")
            self.url2version = {}
        logger.debug("loaded version cache with %d entries"%(len(self.url2version)))

    def save (self):
        try:
            outfile=file(self.filename,'w')
            pickle.dump(self.url2version,outfile)
            outfile.close()
        except:
            logger.log_exc ("Cannot save version cache into %s"%self.filename)
    def clean (self):
        try:
            os.unlink(self.filename)
            logger.info("Cleaned up version cache %s"%self.filename)
        except:
            logger.log_exc ("Could not unlink version cache %s"%self.filename)

    def show (self):
        entries=len(self.url2version)
        print "version cache from file %s has %d entries"%(self.filename,entries)
        for (url,tuple) in self.url2version.iteritems():
            (timestamp,version) = tuple
            how_old = time.time()-timestamp
            if how_old<=self.expires:
                print url,"(%d seconds ago)"%how_old,"-> keys=",version.keys()
            else:
                print url,"(%d seconds ago)"%how_old,"too old"
    
    def set (self,url,version):
        self.url2version[url]=( time.time(), version)
    def get (self,url):
        try:
            (timestamp,version)=self.url2version[url]
            how_old = time.time()-timestamp
            if how_old<=self.expires: return version
            else: return None
        except:
            return None

###
class Interface:

    def __init__ (self,url,verbose=False):
        self._url=url
        self.verbose=verbose
        try:
            (self._url,self.hostname,self.port)=url_hostname_port(url)
            self.ip=socket.gethostbyname(self.hostname)
            self.probed=False
        except:
            self.hostname="unknown"
            self.ip='0.0.0.0'
            self.port="???"
            # don't really try it
            self.probed=True
            self._version={}

    def url(self):
        return self._url

    # this is used as a key for creating graph nodes and to avoid duplicates
    def uid (self):
        return "%s:%s"%(self.ip,self.port)

    # connect to server and trigger GetVersion
    def get_version(self):
        ### if we already know the answer:
        if self.probed:
            return self._version
        ### otherwise let's look in the cache file
        cached_version = VersionCache().get(self.url())
        if cached_version:
            logger.info("Retrieved version info from cache")
            return cached_version
        ### otherwise let's do the hard work
        # dummy to meet Sfi's expectations for its 'options' field
        class DummyOptions:
            pass
        options=DummyOptions()
        options.verbose=self.verbose
        options.timeout=10
        try:
            client=Sfi(options)
            client.read_config()
            key_file = client.get_key_file()
            cert_file = client.get_cert_file(key_file)
            url=self.url()
            logger.info('issuing GetVersion at %s'%url)
            # setting timeout here seems to get the call to fail - even though the response time is fast
            #server=xmlrpcprotocol.server_proxy(url, key_file, cert_file, verbose=self.verbose, timeout=options.timeout)
            server=xmlrpcprotocol.server_proxy(url, key_file, cert_file, verbose=self.verbose)
            self._version=server.GetVersion()
        except:
            logger.log_exc("failed to get version")
            self._version={}
        self.probed=True
        cache=VersionCache()
        cache.set(self.url(),self._version)
        cache.save()
        logger.info("Saved version for url=%s in version cache"%self.url())
        return self._version

    @staticmethod
    def multi_lines_label(*lines):
        result='<<TABLE BORDER="0" CELLBORDER="0"><TR><TD>' + \
            '</TD></TR><TR><TD>'.join(lines) + \
            '</TD></TR></TABLE>>'
        return result

    # default is for when we can't determine the type of the service
    # typically the server is down, or we can't authenticate, or it's too old code
    shapes = {"registry": "diamond", "slicemgr":"ellipse", "aggregate":"box", 'default':'plaintext'}
    abbrevs = {"registry": "REG", "slicemgr":"SA", "aggregate":"AM", 'default':'[unknown interface]'}

    # return a dictionary that translates into the node's attr
    def get_layout (self):
        layout={}
        ### retrieve cached GetVersion
        version=self.get_version()
        # set the href; xxx would make sense to try and 'guess' the web URL, not the API's one...
        layout['href']=self.url()
        ### set html-style label
        ### see http://www.graphviz.org/doc/info/shapes.html#html
        # if empty the service is unreachable
        if not version:
            label="offline"
        else:
            label=''
            try: abbrev=Interface.abbrevs[version['interface']]
            except: abbrev=Interface.abbrevs['default']
            label += abbrev
            if 'hrn' in version: label += " %s"%version['hrn']
            else:                label += "[no hrn]"
            if 'code_tag' in version: 
                label += " %s"%version['code_tag']
            if 'testbed' in version:
                label += " (%s)"%version['testbed']
        layout['label']=Interface.multi_lines_label(self.url(),label)
        ### set shape
        try: shape=Interface.shapes[version['interface']]
        except: shape=Interface.shapes['default']
        layout['shape']=shape
        ### fill color to outline wrongly configured bodies
        if 'geni_api' not in version and 'sfa' not in version:
            layout['style']='filled'
            layout['fillcolor']='gray'
        return layout

class SfaScan:

    # provide the entry points (a list of interfaces)
    def __init__ (self, left_to_right=False, verbose=False):
        self.verbose=verbose
        self.left_to_right=left_to_right

    def graph (self,entry_points):
        graph=pygraphviz.AGraph(directed=True)
        if self.left_to_right: 
            graph.graph_attr['rankdir']='LR'
        self.scan(entry_points,graph)
        return graph
    
    # scan from the given interfaces as entry points
    def scan(self,interfaces,graph):
        if not isinstance(interfaces,list):
            interfaces=[interfaces]

        # remember node to interface mapping
        node2interface={}
        # add entry points right away using the interface uid's as a key
        to_scan=interfaces
        for i in interfaces: 
            graph.add_node(i.uid())
            node2interface[graph.get_node(i.uid())]=i
        scanned=[]
        # keep on looping until we reach a fixed point
        # don't worry about abels and shapes that will get fixed later on
        while to_scan:
            for interface in to_scan:
                # performing xmlrpc call
                version=interface.get_version()
                if self.verbose:
                    logger.info("GetVersion at interface %s"%interface.url())
                    if not version:
                        logger.info("<EMPTY GetVersion(); offline or cannot authenticate>")
                    else: 
                        for (k,v) in version.iteritems(): 
                            if not isinstance(v,dict):
                                logger.info("\r\t%s:%s"%(k,v))
                            else:
                                logger.info(k)
                                for (k1,v1) in v.iteritems():
                                    logger.info("\r\t\t%s:%s"%(k1,v1))
                # 'geni_api' is expected if the call succeeded at all
                # 'peers' is needed as well as AMs typically don't have peers
                if 'geni_api' in version and 'peers' in version: 
                    # proceed with neighbours
                    for (next_name,next_url) in version['peers'].iteritems():
                        next_interface=Interface(next_url)
                        # locate or create node in graph
                        try:
                            # if found, we're good with this one
                            next_node=graph.get_node(next_interface.uid())
                        except:
                            # otherwise, let's move on with it
                            graph.add_node(next_interface.uid())
                            next_node=graph.get_node(next_interface.uid())
                            node2interface[next_node]=next_interface
                            to_scan.append(next_interface)
                        graph.add_edge(interface.uid(),next_interface.uid())
                scanned.append(interface)
                to_scan.remove(interface)
            # we've scanned the whole graph, let's get the labels and shapes right
            for node in graph.nodes():
                interface=node2interface.get(node,None)
                if interface:
                    for (k,v) in interface.get_layout().iteritems():
                        node.attr[k]=v
                else:
                    logger.error("MISSED interface with node %s"%node)
    

default_outfiles=['sfa.png','sfa.svg','sfa.dot']

def main():
    usage="%prog [options] url-entry-point(s)"
    parser=OptionParser(usage=usage)
    parser.add_option("-o","--output",action='append',dest='outfiles',default=[],
                      help="output filenames (cumulative) - defaults are %r"%default_outfiles)
    parser.add_option("-l","--left-to-right",action="store_true",dest="left_to_right",default=False,
                      help="instead of top-to-bottom")
    parser.add_option("-v", "--verbose", action="count", dest="verbose", default=0,
                      help="verbose - can be repeated for more verbosity")
    parser.add_option("-c", "--clear-cache",action='store_true',
                      dest='clear_cache',default=False,
                      help='clear/trash version cache and exit')
    parser.add_option("-s","--show-cache",action='store_true',
                      dest='show_cache',default=False,
                      help='show/display version cache')
    
    (options,args)=parser.parse_args()
    if options.show_cache: 
        VersionCache().show()
        sys.exit(0)
    if options.clear_cache:
        VersionCache().clean()
        sys.exit(0)
    if not args:
        parser.print_help()
        sys.exit(1)
        
    if not options.outfiles:
        options.outfiles=default_outfiles
    logger.enable_console()
    # apply current verbosity to logger
    logger.setLevelFromOptVerbose(options.verbose)
    # figure if we need to be verbose for these local classes that only have a bool flag
    bool_verbose=logger.getBoolVerboseFromOpt(options.verbose)
    scanner=SfaScan(left_to_right=options.left_to_right, verbose=bool_verbose)
    entries = [ Interface(entry) for entry in args ]
    g=scanner.graph(entries)
    logger.info("creating layout")
    g.layout(prog='dot')
    for outfile in options.outfiles:
        logger.info("drawing in %s"%outfile)
        g.draw(outfile)
    logger.info("done")

if __name__ == '__main__':
    main()

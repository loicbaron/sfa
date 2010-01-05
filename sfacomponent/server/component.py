#
# Component is a SfaServer that implements the Component interface
#
### $Id: 
### $URL: 
#

import tempfile
import os
import time
import sys

from sfa.util.server import SfaServer
from sfacomponent.plc.api import ComponentAPI
 
# GeniLight client support is optional
try:
    from egeni.geniLight_client import *
except ImportError:
    GeniClientLight = None            

##
# Component is a SfaServer that serves component operations.

class Component(SfaServer):
    ##
    # Create a new registry object.
    #
    # @param ip the ip address to listen on
    # @param port the port to listen on
    # @param key_file private key filename of registry
    # @param cert_file certificate filename containing public key (could be a GID file)

    def __init__(self, ip, port, key_file, cert_file):
        SfaServer.__init__(self, ip, port, key_file, cert_file)
        # re-initialize the servers api as Component api  
        self.server.api = ComponentAPI(interface='component', key_file=key_file, cert_file=cert_file)  
        self.server.interface = 'component'

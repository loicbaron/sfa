#!/usr/bin/python

import sys
import os
from sfa.util.misc import *
from sfa.util.genitable import GeniTable
from sfa.util.geniclient import GeniClient
from sfa.plc.api import GeniAPI
from sfa.util.config import Config
from sfa.trust.hierarchy import Hierarchy
from sfa.util.report import trace, error
from sfa.server.registry import Registries

def main():
    config = Config()
    if not config.SFA_REGISTRY_ENABLED:
        sys.exit(0)

    # Get the path to the sfa server key/cert files from 
    # the sfa hierarchy object
    sfa_hierarchy = Hierarchy()
    sfa_key_path = sfa_hierarchy.basedir
    key_file = os.path.join(sfa_key_path, "server.key")
    cert_file = os.path.join(sfa_key_path, "server.cert")

    # get a connection to our local sfa registry
    # and a valid credential
    authority = config.SFA_INTERFACE_HRN
    url = 'http://%s:%s/' %(config.SFA_REGISTRY_HOST, config.SFA_REGISTRY_PORT)
    registry = GeniClient(url, key_file, cert_file)
    sfa_api = GeniAPI(key_file = key_file, cert_file = cert_file, interface='registry')
    credential = sfa_api.getCredential()

    # get peer registries
    registries = Registries(sfa_api)


    # get local peer records
    table = GeniTable()
    peer_records = table.find({'~peer_authority': None})

    # get a list of authorities contained in the peer record list
    for peer_record in peer_records:
        peer_auth = peer_record['peer_authority']
        if peer_auth in registries:
            records = registries[peer_auth].resolve(credential, peer_record['hrn'])
            if not records:
                table.remove(peer_record) 

if __name__ == '__main__':
    main()

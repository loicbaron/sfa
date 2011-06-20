#!/usr/bin/python 
from lxml import etree
from StringIO import StringIO
from sfa.rspecs.rspec import RSpec 
from sfa.util.xrn import *
from sfa.util.plxrn import hostname_to_urn
from sfa.util.config import Config 
from sfa.rspecs.rspec_version import RSpecVersion 

_ad_version = {'type':  'ProtoGENI',
            'version': '2',
            'schema': 'http://www.protogeni.net/resources/rspec/2/ad.xsd',
            'namespace': 'http://www.protogeni.net/resources/rspec/2',
            'extensions':  [
                'http://www.protogeni.net/resources/rspec/ext/gre-tunnel/1',
                'http://www.protogeni.net/resources/rspec/ext/other-ext/3'
            ]
}

_request_version = {'type':  'ProtoGENI',
            'version': '2',
            'schema': 'http://www.protogeni.net/resources/rspec/2/request.xsd',
            'namespace': 'http://www.protogeni.net/resources/rspec/2',
            'extensions':  [
                'http://www.protogeni.net/resources/rspec/ext/gre-tunnel/1',
                'http://www.protogeni.net/resources/rspec/ext/other-ext/3'
            ]
}
pg_rspec_ad_version = RSpecVersion(_ad_version)
pg_rspec_request_version = RSpecVersion(_request_version)

class PGRSpec(RSpec):
    xml = None
    header = '<?xml version="1.0"?>\n'
    template = '<rspec xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.protogeni.net/resources/rspec/2" xsi:schemaLocation="http://www.protogeni.net/resources/rspec/2 http://www.protogeni.net/resources/rspec/2/%(rspec_type)s.xsd"/>'

    def __init__(self, rspec="", namespaces={}, type=None):
        if not type:
            type = 'advertisement'
        self.type = type

        if type == 'advertisement':
            self.version = pg_rspec_ad_version
            rspec_type = 'ad'
        else:
            self.version = pg_rspec_request_version
            rspec_type = type
        
        self.template = self.template % {'rspec_type': rspec_type}

        if not namespaces:
            self.namespaces = {'rspecv2': self.version['namespace']}
        else:
            self.namespaces = namespaces 

        if rspec:
            self.parse_rspec(rspec, self.namespaces)
        else: 
            self.create()

    def create(self):
        RSpec.create(self)
        if self.type:
            self.xml.set('type', self.type) 
       
    def get_network(self):
        network = None 
        nodes = self.xml.xpath('//rspecv2:node[@component_manager_uuid][1]', namespaces=self.namespaces)
        if nodes:
            network  = nodes[0].get('component_manager_uuid')
        return network

    def get_networks(self):
        networks = self.xml.xpath('//rspecv2:node[@component_manager_uuid]/@component_manager_uuid', namespaces=self.namespaces)
        return set(networks)

    def get_node_elements(self):
        nodes = self.xml.xpath('//rspecv2:node | //node', namespaces=self.namespaces)
        return nodes

    def get_nodes(self, network=None):
        xpath = '//rspecv2:node[@component_name]/@component_name | //node[@component_name]/@component_name'
        return self.xml.xpath(xpath, namespaces=self.namespaces) 

    def get_nodes_with_slivers(self, network=None):
        if network:
            return self.xml.xpath('//rspecv2:node[@component_manager_id="%s"][sliver_type]/@component_name' % network, namespaces=self.namespaces)
        else:
            return self.xml.xpath('//rspecv2:node[rspecv2:sliver_type]/@component_name', namespaces=self.namespaces)

    def get_nodes_without_slivers(self, network=None):
        pass

    def add_nodes(self, nodes, check_for_dupes=False):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for node in nodes:
            urn = ""
            if check_for_dupes and \
              self.xml.xpath('//rspecv2:node[@component_uuid="%s"]' % urn, namespaces=self.namespaces):
                # node already exists
                continue
                
            node_tag = etree.SubElement(self.xml, 'node', exclusive='false')
            if 'network_urn' in node:
                node_tag.set('component_manager_id', node['network_urn'])
            if 'urn' in node:
                node_tag.set('component_id', node['urn'])
            if 'hostname' in node:
                node_tag.set('component_name', node['hostname'])
            # TODO: should replace plab-pc with pc model 
            node_type_tag = etree.SubElement(node_tag, 'hardware_type', name='plab-pc')
            node_type_tag = etree.SubElement(node_tag, 'hardware_type', name='pc')
            available_tag = etree.SubElement(node_tag, 'available', now='true')
            location_tag = etree.SubElement(node_tag, 'location', country="us")
            if 'site' in node:
                if 'longitude' in node['site']:
                    location_tag.set('longitude', str(node['site']['longitude']))
                if 'latitude' in node['site']:
                    location_tag.set('latitude', str(node['site']['latitude']))
            #if 'interfaces' in node:
            

    def add_slivers(self, slivers, sliver_urn=None, no_dupes=False): 
        slivers = self._process_slivers(slivers)
        nodes_with_slivers = self.get_nodes_with_slivers()
        for sliver in slivers:
            hostname = sliver['hostname']
            if hostname in nodes_with_slivers:
                continue
            nodes = self.xml.xpath('//rspecv2:node[@component_name="%s"] | //node[@component_name="%s"]' % (hostname, hostname), namespaces=self.namespaces)
            if nodes:
                node = nodes[0]
                node.set('client_id', hostname)
                if sliver_urn:
                    node.set('sliver_id', sliver_urn)
                etree.SubElement(node, 'sliver_type', name='plab-vnode')

    def add_interfaces(self, interfaces, no_dupes=False):
        pass

    def add_links(self, links, no_dupes=False):
        pass


    def merge(self, in_rspec):
        """
        Merge contents for specified rspec with current rspec
        """
        
        # just copy over all the child elements under the root element
        tree = etree.parse(StringIO(in_rspec))
        root = tree.getroot()
        for child in root.getchildren():
            self.xml.append(child)
                  
    def cleanup(self):
        # remove unncecessary elements, attributes
        if self.type in ['request', 'manifest']:
            # remove nodes without slivers
            nodes = self.get_node_elements()
            for node in nodes:
                delete = True
                hostname = node.get('component_name')
                parent = node.getparent()
                children = node.getchildren()
                for child in children:
                    if child.tag.endswith('sliver_type'):
                        delete = False
                if delete:
                    parent.remove(node)

            # remove 'available' element from remaining node elements
            self.remove_element('//rspecv2:available | //available')

if __name__ == '__main__':
    rspec = PGRSpec()
    rspec.add_nodes([1])
    print rspec

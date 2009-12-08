### $Id:  $
### $URL:  $
import os
import tempfile
import commands
from sfa.util.faults import *
from sfa.util.misc import *
from sfa.util.method import Method
from sfa.util.parameter import Parameter, Mixed
from sfa.trust.auth import Auth
from sfa.util.genitable import *
from sfa.trust.certificate import Keypair

class get_key(Method):
    """
    Generate a new keypair and gid for requesting caller (component).     
    @return 1 If successful  
    """

    interfaces = ['registry']
    
    accepts = []

    returns = Parameter(int, "1 if successful, faults otherwise")
    
    def call(self):
        # verify that the callers's ip address exist in the db and is an inteface
        # for a node in the db
        (ip, port) = self.api.remote_addr
        interfaces = self.api.plshell.GetInterfaces(self.api.plauth, {'ip': ip}, ['node_id'])
        if not interfaces:
            raise NonExistingRecord("no such ip %(ip)s" % locals())
        nodes = self.api.plshell.GetNodes(self.api.plauth, [interfaces[0]['node_id']], ['node_id', 'hostname'])
        if not nodes:
            raise NonExistingRecord("no such node using ip %(ip)s" % locals())
        node = nodes[0]
       
        # look up the sfa record
        table = GeniTable()
        records = table.findObjects({'type': 'node', 'pointer': node['node_id']})
        if not records:
            raise RecordNotFound("pointer:" + str(node['node_id']))  
        record = records[0]
        
        # generate a new keypair and gid
        uuid = create_uuid()
        pkey = Keypair(create=True)
        gid_object = self.api.auth.hierarchy.create_gid(record['hrn'], uuid, pkey)
        gid = gid_object.save_to_string(save_parents=True)
        record['gid'] = gid
        record.set_gid(gid)

        # update the record
        table.update(record)
  
        # attempt the scp the key
        # and gid onto the node
        # this will only work for planetlab based compoenents
        (kfd, key_filename) = tempfile.mkstemp() 
        (gfd, gid_filename) = tempfile.mkstemp() 
        pkey.save_to_file(key_filename)
        gid_str = gid.save_to_file(save_parents=True)
        host = node['hostname']
        key_dest="/etc/sfa/node.key"
        gid_dest="/etc/sfa/node.gid" 
        scp = "/usr/bin/scp" 
        identity = "/etc/planetlab/root_ssh_key.rsa"
        scp_options=" -i %(identity)s %(filename)s " % locals()
        scp_options+="-o StrictHostKeyChecking=no " % locals()
        scp_key_command="%(scp)s %(scp_options)s root@%(host)s:%(key_dest)s" %\
                         locals()
        scp_gid_command="%(scp)s %(scp_options)s root@%(host)s:%(gid_dest)s" %\
                         locals()    

        all_commands = [scp_key_command, scp_gid_command]
        
        for command in all_commands:
            (status, output) = commands.getstatusoutput(command)
            if status:
                raise Exception, output

        for filename in [key_filename, gid_filename]:
            os.unlink(filename)

        return 1 

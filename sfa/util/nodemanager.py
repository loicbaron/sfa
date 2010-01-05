import tempfile
import commands
import os

class NodeManager:

    method = None

    def __getattr__(self, method):
        self.method = method
        return self.__call__
    
    def __call__(self, *args):
        method = self.method
        ### WARNING -- hardwired name needs to be computed 
        sfa_slice = "pl_genicw"
        python = "/usr/bin/python"
        vserver_path = "/vservers/%s" % (sfa_slice)
        script_path = "/tmp/"
        path = "%(vserver_path)s/%(script_path)s" % locals()
        (fd, filename) = tempfile.mkstemp(dir=path)        
        scriptname = script_path + os.sep + filename.split(os.sep)[-1:][0]
        # define the script to execute
        script = """
#!%(python)s
import xmlrpclib
s = xmlrpclib.ServerProxy('http://127.0.0.1:812')
print s.%(method)s%(args)s"""  % locals()

        try:    
            # write the script to a temporary file
            f = open(filename, 'w')
            f.write(script % locals())
            f.close()
            # make the file executeable
            chmod_cmd = "/bin/chmod 775 %(filename)s" % locals()
            print chmod_cmd
            (status, output) = commands.getstatusoutput(chmod_cmd)

            # execute the commad as a slice with root NM privs    
            cmd = 'su - %(sfa_slice)s -c "%(python)s %(scriptname)s"' % locals()
            print cmd
            (status, output) = commands.getstatusoutput(cmd)
            return (status, output)  
        finally: os.unlink(filename)

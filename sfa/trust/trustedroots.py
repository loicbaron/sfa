import os.path
import glob

from sfa.trust.gid import GID

class TrustedRoots:
    def __init__(self, dir):
        self.basedir = dir
        # create the directory to hold the files, if not existing
        if not os.path.isdir (self.basedir):
            os.makedirs(self.basedir)

    def add_gid(self, gid):
        fn = os.path.join(self.basedir, gid.get_hrn() + ".gid")
        gid.save_to_file(fn)

    def get_list(self):
        gid_list = [GID(filename=cert_file) for cert_file in self.get_file_list()]
        return gid_list

    def get_file_list(self):
        file_list  = []
        pattern=os.path.join(self.basedir,"*.gid")
        for cert_file in glob.glob(pattern):
            if os.path.isfile(cert_file):
                file_list.append(cert_file) 
        return file_list
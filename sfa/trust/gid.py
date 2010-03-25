##
# Implements SFA GID. GIDs are based on certificates, and the GID class is a
# descendant of the certificate class.
##

### $Id$
### $URL$

import xmlrpclib
import uuid
from sfa.trust.certificate import Certificate
from sfa.util.namespace import *
##
# Create a new uuid. Returns the UUID as a string.

def create_uuid():
    return str(uuid.uuid4().int)

##
# GID is a tuple:
#    (uuid, urn, public_key)
#
# UUID is a unique identifier and is created by the python uuid module
#    (or the utility function create_uuid() in gid.py).
#
# HRN is a human readable name. It is a dotted form similar to a backward domain
#    name. For example, planetlab.us.arizona.bakers.
#
# URN is a human readable identifier of form:
#   "urn:publicid:IDN+toplevelauthority[:sub-auth.]*[\res. type]\ +object name"
#   For  example, urn:publicid:IDN+planetlab:us:arizona+user+bakers      
#
# PUBLIC_KEY is the public key of the principal identified by the UUID/HRN.
# It is a Keypair object as defined in the cert.py module.
#
# It is expected that there is a one-to-one pairing between UUIDs and HRN,
# but it is uncertain how this would be inforced or if it needs to be enforced.
#
# These fields are encoded using xmlrpc into the subjectAltName field of the
# x509 certificate. Note: Call encode() once the fields have been filled in
# to perform this encoding.


class GID(Certificate):
    uuid = None
    hrn = None
    urn = None

    ##
    # Create a new GID object
    #
    # @param create If true, create the X509 certificate
    # @param subject If subject!=None, create the X509 cert and set the subject name
    # @param string If string!=None, load the GID from a string
    # @param filename If filename!=None, load the GID from a file

    def __init__(self, create=False, subject=None, string=None, filename=None, uuid=None, hrn=None, urn=None):
        
        Certificate.__init__(self, create, subject, string, filename)
        if uuid:
            self.uuid = int(uuid)
        if hrn:
            self.hrn = hrn
        if urn:
            self.urn = urn
            self.hrn, type = urn_to_hrn(urn)

    def set_uuid(self, uuid):
        self.uuid = uuid

    def get_uuid(self):
        if not self.uuid:
            self.decode()
        return self.uuid

    def set_hrn(self, hrn):
        self.hrn = hrn

    def get_hrn(self):
        if not self.hrn:
            self.decode()
        return self.hrn

    def set_urn(self, urn):
        self.urn = urn
        self.hrn, type = urn_to_hrn(urn)
 
    def get_urn(self):
        if not self.urn:
            self.decode()
        return self.urn            

    ##
    # Encode the GID fields and package them into the subject-alt-name field
    # of the X509 certificate. This must be called prior to signing the
    # certificate. It may only be called once per certificate.

    def encode(self):
        if self.urn:
            urn = self.urn
        else:
            urn = hrn_to_urn(self.hrn, None)
            
        szURN = "URI:" + urn
        szUUID = "URI:" + uuid.UUID(int=self.uuid).urn
        
        
        str = szURN + ", " + szUUID
        self.set_data(str, 'subjectAltName')


    ##
    # Decode the subject-alt-name field of the X509 certificate into the
    # fields of the GID. This is automatically called by the various get_*()
    # functions in this class.

    def decode(self):
        data = self.get_data('subjectAltName')
        dict = {}
        if data:
            if data.lower().startswith('uri:http://<params>'):
                dict = xmlrpclib.loads(data[11:])[0][0]
            else:
                spl = data.split(', ')
                for val in spl:
                    if val.lower().startswith('uri:urn:uuid:'):
                        dict['uuid'] = uuid.UUID(val[4:]).int
                    elif val.lower().startswith('uri:urn:publicid:idn+'):
                        dict['urn'] = val[4:]
                    
        self.uuid = dict.get("uuid", None)
        self.urn = dict.get("urn", None)
        self.hrn = dict.get("hrn", None)    
        if self.urn:
            self.hrn = urn_to_hrn(self.urn)[0]

    ##
    # Dump the credential to stdout.
    #
    # @param indent specifies a number of spaces to indent the output
    # @param dump_parents If true, also dump the parents of the GID

    def dump(self, indent=0, dump_parents=False):
        print " "*indent, " hrn:", self.get_hrn()
        print " "*indent, " urn:", self.get_urn()
        print " "*indent, "uuid:", self.get_uuid()

        if self.parent and dump_parents:
            print " "*indent, "parent:"
            self.parent.dump(indent+4)

    ##
    # Verify the chain of authenticity of the GID. First perform the checks
    # of the certificate class (verifying that each parent signs the child,
    # etc). In addition, GIDs also confirm that the parent's HRN is a prefix
    # of the child's HRN.
    #
    # Verifying these prefixes prevents a rogue authority from signing a GID
    # for a principal that is not a member of that authority. For example,
    # planetlab.us.arizona cannot sign a GID for planetlab.us.princeton.foo.

    def verify_chain(self, trusted_certs = None):
        # do the normal certificate verification stuff
        Certificate.verify_chain(self, trusted_certs)

        if self.parent:
            # make sure the parent's hrn is a prefix of the child's hrn
            if not self.get_hrn().startswith(self.parent.get_hrn()):
                raise GidParentHrn(self.parent.get_subject())

        return






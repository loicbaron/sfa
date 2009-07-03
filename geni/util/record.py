##
# Implements support for geni records
#
# TODO: Use existing PLC database methods? or keep this separate?
##

### $Id$
### $URL$

from types import StringTypes

import geni.util.report

from geni.trust.gid import *
from geni.util.rspec import *
from geni.util.parameter import *

class GeniRecord(dict):
    """ 
    The GeniRecord class implements a Geni Record. A GeniRecord is a tuple
    (Name, GID, Type, Info).
 
    Name specifies the HRN of the object
    GID is the GID of the object
    Type is user | authority | slice | component
 
    Info is comprised of the following sub-fields
           pointer = a pointer to the record in the PL database
 
    The pointer is interpreted depending on the type of the record. For example,
    if the type=="user", then pointer is assumed to be a person_id that indexes
    into the persons table.
 
    A given HRN may have more than one record, provided that the records are
    of different types.
    """

    fields = {
        'hrn': Parameter(str, "Human readable name of object"),
        'gid': Parameter(str, "GID of the object"),
        'type': Parameter(str, "Record type"),
        #'last_updated': Parameter(int, 'Date and time of last update'),
        #'date_created': Parameter(int, 'Date and time this record was created'),
    }

    internal_fields = {
        'pointer': Parameter(int, "Internal ID")
    }

    ##
    # Create a Geni Record
    #
    # @param name if !=None, assign the name of the record
    # @param gid if !=None, assign the gid of the record
    # @param type one of user | authority | slice | component
    # @param pointer is a pointer to a PLC record
    # @param dict if !=None, then fill in this record from the dictionary

    def __init__(self, name=None, gid=None, type=None, pointer=None, dict=None, string=None):
        self.dirty = True
        self.name = None
        self.gid = None
        self.type = None
        self.pointer = None
        if name:
            self.set_name(name)
        if gid:
            self.set_gid(gid)
        if type:
            self.set_type(type)
        if pointer:
            self.set_pointer(pointer)
        if dict:
            self.load_from_dict(dict)
        if string:
            self.load_from_string(string)

    
    def update(self, new_dict):
        if isinstance(new_dict, list):
            new_dict = new_dict[0]

        # Convert any boolean strings to real bools
        for key in new_dict:
            if isinstance(new_dict[key], StringTypes):
                if new_dict[key].lower() in ["true"]:
                    new_dict[key] = True
                elif new_dict[key].lower() in ["false"]:
                    new_dict[key] = False
        dict.update(self, new_dict)

    ##
    # Set the name of the record
    #
    # @param name is a string containing the HRN

    def set_name(self, name):
        """
        Set the name of the record
        """
        self.name = name
        self.dirty = True

    ##
    # Set the GID of the record
    #
    # @param gid is a GID object or the string representation of a GID object

    def set_gid(self, gid):
        """
        Set the GID of the record
        """

        if isinstance(gid, StringTypes):
            self.gid = gid
        else:
            self.gid = gid.save_to_string(save_parents=True)
        self.dirty = True

    ##
    # Set the type of the record
    #
    # @param type is a string: user | authority | slice | component

    def set_type(self, type):
        """
        Set the type of the record
        """
        self.type = type
        self.dirty = True

    ##
    # Set the pointer of the record
    #
    # @param pointer is an integer containing the ID of a PLC record

    def set_pointer(self, pointer):
        """
        Set the pointer of the record
        """
        self.pointer = pointer
        self.dirty = True

    ##
    # Return the name (HRN) of the record

    def get_name(self):
        """
        Return the name (HRN) of the record
        """
        return self.name

    ##
    # Return the type of the record

    def get_type(self):
        """
        Return the type of the record
        """
        return self.type

    ##
    # Return the pointer of the record. The pointer is an integer that may be
    # used to look up the record in the PLC database. The evaluation of pointer
    # depends on the type of the record

    def get_pointer(self):
        """
        Return the pointer of the record. The pointer is an integer that may be
        used to look up the record in the PLC database. The evaluation of pointer
        depends on the type of the record
        """
        return self.pointer

    ##
    # Return the GID of the record, in the form of a GID object
    # TODO: not the best name for the function, because we have things called
    # gidObjects in the Cred

    def get_gid_object(self):
        """
        Return the GID of the record, in the form of a GID object
        """
        return GID(string=self.gid)

    ##
    # Return a key that uniquely identifies this record among all records in
    # Geni. This key is used to uniquely identify the record in the Geni
    # database.

    def get_key(self):
        """
        Return a key that uniquely identifies this record among all records in
        Geni. This key is used to uniquely identify the record in the Geni
        database.
        """
        return self.name + "#" + self.type

    ##
    # Returns a list of field names in this record. 

    def get_field_names(self):
        """
        Returns a list of field names in this record.
        """
        return ["name", "gid", "type", "pointer"]

    ##
    # Given a field name ("name", "gid", ...) return the value of that field.
    #
    # @param name is the name of field to be returned

    def get_field_value_string(self, fieldname):
        """
        Given a field name ("name", "gid", ...) return the value of that field.
        """
        if fieldname == "key":
            val = self.get_key()
        else:
            val = getattr(self, fieldname)
        if isinstance(val, str):
            return "'" + str(val) + "'"
        else:
            return str(val)

    ##
    # Given a list of field names, return a list of values for those fields.
    #
    # @param fieldnames is a list of field names

    def get_field_value_strings(self, fieldnames):
        """
        Given a list of field names, return a list of values for those fields.
        """
        strs = []
        for fieldname in fieldnames:
            strs.append(self.get_field_value_string(fieldname))
        return strs

    ##
    # Return the record in the form of a dictionary

    def as_dict(self):
        """
        Return the record in the form of a dictionary
        """
        return dict(self)

    ##
    # Load the record from a dictionary
    #
    # @param dict dictionary to load record fields from

    def load_from_dict(self, dict):
        """
        Load the record from a dictionary 
        """
        self.set_name(dict['name'])
        gidstr = dict.get("gid", None)
        if gidstr:
            self.set_gid(dict['gid'])

        if "pointer" in dict:
           self.set_pointer(dict['pointer'])

        self.set_type(dict['type'])
        self['hrn'] = dict['name'] 
        self.update(dict)        
    
    ##
    # Save the record to a string. The string contains an XML representation of
    # the record.

    def save_to_string(self):
        """
        Save the record to a string. The string contains an XML representation of
        the record.
        """
        dict = self.as_dict()
        record = RecordSpec()
        record.parseDict(dict)
        str = record.toxml()
        #str = xmlrpclib.dumps((dict,), allow_none=True)
        return str

    ##
    # Load the record from a string. The string is assumed to contain an XML
    # representation of the record.

    def load_from_string(self, str):
        """
        Load the record from a string. The string is assumed to contain an XML
        representation of the record.
        """
        #dict = xmlrpclib.loads(str)[0][0]
        
        record = RecordSpec()
        record.parseString(str)
        record_dict = record.toDict()
        geni_dict = record_dict['record']
        self.load_from_dict(geni_dict)

    ##
    # Dump the record to stdout
    #
    # @param dump_parents if true, then the parents of the GID will be dumped

    def dump(self, dump_parents=False):
        """
        Walk tree and dump records.
        """
        #print "RECORD", self.name
        #print "        hrn:", self.name
        #print "       type:", self.type
        #print "        gid:"
        #if (not self.gid):
        #    print "        None"
        #else:
        #    self.get_gid_object().dump(8, dump_parents)
        #print "    pointer:", self.pointer
       
        order = GeniRecord.fields.keys() 
        for key in self.keys():
            if key not in order:
                order.append(key)
        for key in order:
            if key in (self and self.fields):
                if key in 'gid' and self[key]:
                    gid = GID(string=self[key])
                    print "     %s:" % key
                    gid.dump(8, dump_parents)
                else:    
                    print "     %s: %s" % (key, self[key])
    
    def getdict(self):
        return dict(self)
    

class UserRecord(GeniRecord):

    fields = {
        'email': Parameter(str, 'email'),
        'first_name': Parameter(str, 'First name'),
        'last_name': Parameter(str, 'Last name'),
        'phone': Parameter(str, 'Phone Number'),
        'key': Parameter(str, 'Public key'),
        'slice': Parameter([str], 'List of slices this user belongs to'),
        }
    fields.update(GeniRecord.fields)
 
    internal_fields = {
        'roles': Parameter([str], 'List of roles'),
        'title': Parameter(str, 'Title'),
        'sites': Parameter([str], 'List of sites this user belongs to'),
        'enabled': Parameter(bool, 'Is this person enabled'),
        }
    internal_fields.update(GeniRecord.internal_fields)
    
class SliceRecord(GeniRecord):
    fields = {
        'name': Parameter(str, 'Slice name'),
        'url': Parameter(str, 'Slice url'),
        'expires': Parameter(int, 'Date and time this slice exipres'),
        'researcher': Parameter([str], 'List of users for this slice'),
        'description': Parameter([str], 'Description of this slice'), 
        }
    fields.update(GeniRecord.fields)

    internal_fields = {
        'site': Parameter(str, 'Site this slice belongs to'),
        'instantiation': Parameter(str, 'Slice instantiation'),
        'nodes': Parameter([str], 'List of nodes this slice is instantiated on'),
        'max_nodes': Parameter(int, 'Maximum number of nodes this slice is allowed on')
        }
    internal_fields.update(GeniRecord.internal_fields)
 
class NodeRecord(GeniRecord):
    fields = {
        'hostname': Parameter(str, 'This nodes dns name'),
        'node_type': Parameter(str, 'Type of node this is'),
        'node_type': Parameter(str, 'Type of node this is'),
        'latitude': Parameter(str, 'latitude'),
        'longitude': Parameter(str, 'longitude'),
        }
    fields.update(GeniRecord.fields)

    internal_fields = {
        'slice_ids_whitelist': Parameter([str], 'List of allowed slices on this node'),
        'site': Parameter(str, 'Site this node belongs to'),
        'slices': Parameter([str], 'List of instantiated slices on this node'),
        'boot_state': Parameter(str, 'This nodes boot state'),
        'session': Parameter(str, 'This nodes session key'),
        'ssh_rsa_key': Parameter(str, 'Last known ssh host key'),
        'verified': Parameter(str, 'Whether the node configuration is verified correct'),
        'last_contact': Parameter(int, 'Date and time this node last phoned home'),
        'run_level': Parameter(str, 'Run level'),
        'version': Parameter(str, 'Node software version'),
        'key': Parameter(str, 'Node key'),
        'boot_noonce': Parameter(str, 'Random value generate at nodes last boot'),
        'model': Parameter(str, 'Model of node'),
        'ports': Parameter([int], 'List of pcu ports this node is connected to') 
        }
    internal_fields.update(GeniRecord.internal_fields)

class AuthorityRecord(GeniRecord):
    fields =  {
        'name': Parameter(str, 'Name'),
        'login_base': Parameter(str, 'login base'),
        'enabled': Parameter(bool, 'Is this site enabled'),
        'url': Parameter(str, 'URL'),
        'nodes': Parameter([str], 'List of nodes at this site'),  
        'operator': Parameter([str], 'List of operators'),
        'researcher': Parameter([str], 'List of researchers'),
        'PI': Parameter([str], 'List of Principal Investigators'),
        }
    fields.update(GeniRecord.fields)
    
    internal_fields = {
        'nodes': Parameter([str], 'List of nodes at this site'),  
        'slices': Parameter([str], 'List of slices instantiated by this site'),
        'abbreviated_name': Parameter(str, 'Abbreviated name'),
        'owners': Parameter([str], 'List of owners'),
        'max_slices': Parameter(int, 'Maximum number of slices this site can instantiate'),
        'max_slivers': Parameter(int, 'Maximum number of slivers this site can instantiate'),
        'pi': Parameter([str], 'List of pis'),
        'is_public': Parameter(bool, 'Is this site public'),
        
        }
    internal_fields.update(GeniRecord.internal_fields) 

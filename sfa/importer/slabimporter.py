from sfa.util.config import Config
from sfa.util.xrn import Xrn, get_authority, hrn_to_urn

from sfa.senslab.slabdriver import SlabDriver

from sfa.trust.certificate import Keypair, convert_public_key
from sfa.trust.gid import create_uuid

from sfa.storage.alchemy import dbsession
from sfa.storage.model import RegRecord, RegAuthority, RegSlice, RegNode, \
                                                    RegUser, RegKey


from sqlalchemy.exc import SQLAlchemyError



class SlabImporter:
    """ 
    SlabImporter class, generic importer_class. Used to populate the SFA DB
    with senslab resources' records. 
    Used to update records when new resources, users or nodes, are added
    or deleted.
    """
     
    def __init__ (self, auth_hierarchy, loc_logger):
        """ 
        Sets and defines import logger and the authority name. Gathers all the 
        records already registerd in the SFA DB, broke them into 3 dicts,
        by type and hrn, by email and by type and pointer.
        
        :param auth_hierarchy: authority name
        :type auth_hierarchy: string
        :param loc_logger: local logger
        :type loc_logger: _SfaLogger
        
        """
        self.auth_hierarchy = auth_hierarchy
        self.logger = loc_logger
        self.logger.setLevelDebug()
        #retrieve all existing SFA objects
        self.all_records = dbsession.query(RegRecord).all()
        
        # initialize record.stale to True by default, 
        # then mark stale=False on the ones that are in use
        for record in self.all_records: 
            record.stale = True
        #create hash by (type,hrn) 
        #used  to know if a given record is already known to SFA 
        self.records_by_type_hrn = \
            dict([( (record.type,record.hrn), record) \
                                        for record in self.all_records])

        self.users_rec_by_email = \
            dict([ (record.email, record) \
                for record in self.all_records if record.type == 'user'])
            
        # create hash by (type,pointer) 
        self.records_by_type_pointer = \
            dict([ ( (str(record.type), record.pointer) , record) \
                for record in self.all_records  if record.pointer != -1])
            
            
        
    @staticmethod
    def hostname_to_hrn_escaped(root_auth, hostname):
        """ 
        
        Returns a node's hrn based on its hostname and the root 
        authority and by removing special caracters from the hostname.
        
        :param root_auth: root authority name
        :param hostname: nodes's hostname
        :type  root_auth: string
        :type hostname: string
        :rtype: string
        """
        return '.'.join( [root_auth, Xrn.escape(hostname)] )


    @staticmethod
    def slicename_to_hrn(person_hrn):
        """
        
        Returns the slicename associated to a given person's hrn.
        
        :param person_hrn: user's hrn
        :type person_hrn: string
        :rtype: string
        """
        return  (person_hrn +'_slice')
    
    def add_options (self, parser):
        # we don't have any options for now
        pass
    
    def find_record_by_type_hrn(self, record_type, hrn):
        """
        
        Returns the record associated with a given hrn and hrn type.
        Returns None if the key tuple is not in dictionary. 
        
        :param record_type: the record's type (slice, node, authority...)
        :type  record_type: string
        :param hrn: Human readable name of the object's record
        :type hrn: string
        :rtype: RegUser if user, RegSlice if slice, RegNode if node...
                or None if record does not exist.
        
        """
        return self.records_by_type_hrn.get ( (record_type, hrn), None)
    
    def locate_by_type_pointer (self, record_type, pointer):
        """
        
        Returns the record corresponding to the key pointer and record
        type. Returns None if the record does not exist and is not in the
        records_by_type_pointer dictionnary.
        
        :param record_type: the record's type (slice, node, authority...)
        :type  record_type: string
        :param pointer:Pointer to where the record is in the origin db, 
        used in case the record comes from a trusted authority.
        :type pointer: integer
        :rtype: RegUser if user, RegSlice if slice, RegNode if node...
                or None if record does not exist.
        """
        return self.records_by_type_pointer.get ( (record_type, pointer), None)
        
    
    def update_just_added_records_dict (self, record):
        """
        
        Updates the records_by_type_hrn dictionnary if the record has 
        just been created.
        
        :param record: Record to add in the records_by_type_hrn dict.
        :type record: dictionary
        """
        rec_tuple = (record.type, record.hrn)
        if rec_tuple in self.records_by_type_hrn:
            self.logger.warning ("SlabImporter.update_just_added_records_dict:\
                        duplicate (%s,%s)"%rec_tuple)
            return
        self.records_by_type_hrn [ rec_tuple ] = record
        
    def import_sites_and_nodes(self, slabdriver):
        """ 
        
        Gets all the sites and nodes from OAR, process the information,
        creates hrns and RegAuthority for sites, and feed them to the database.
        For each site, import the site's nodes to the DB by calling 
        import_nodes.
        
        :param slabdriver: SlabDriver object, used to have access to slabdriver
        methods and fetching info on sites and nodes.
        :type slabdriver: SlabDriver  
        """
        
        sites_listdict  = slabdriver.slab_api.GetSites()  
        nodes_listdict  = slabdriver.slab_api.GetNodes()
        nodes_by_id = dict([(node['node_id'], node) for node in nodes_listdict])
        for site in sites_listdict:
            site_hrn = site['name']
            site_record = self.find_record_by_type_hrn ('authority', site_hrn)
            if not site_record:
                try:
                    urn = hrn_to_urn(site_hrn, 'authority') 
                    if not self.auth_hierarchy.auth_exists(urn):
                        self.auth_hierarchy.create_auth(urn)
                        
                    auth_info = self.auth_hierarchy.get_auth_info(urn)
                    site_record = RegAuthority(hrn=site_hrn, \
                                            gid=auth_info.get_gid_object(),
                                            pointer='-1',
                                            authority=get_authority(site_hrn))
                    site_record.just_created()
                    dbsession.add(site_record)
                    dbsession.commit()
                    self.logger.info("SlabImporter: imported authority (site) \
                         %s" % site_record) 
                    self.update_just_added_records_dict(site_record)
                except SQLAlchemyError:
                    # if the site import fails then there is no point in 
                    # trying to import the
                    # site's child records(node, slices, persons), so skip them.
                    self.logger.log_exc("SlabImporter: failed to import site. \
                        Skipping child records") 
                    continue
            else:
                # xxx update the record ...
                pass
            
            
            site_record.stale = False
            self.import_nodes(site['node_ids'], nodes_by_id, slabdriver)
            
            return 
        
    def import_nodes(self, site_node_ids, nodes_by_id, slabdriver) :
        """  
        
        Creates appropriate hostnames and RegNode records for
        each node in site_node_ids, based on the information given by the
        dict nodes_by_id that was made from data from OAR. 
        Saves the records to the DB.
        
        :param site_node_ids: site's node ids
        :type site_node_ids: list of integers
        :param nodes_by_id: dictionary , key is the node id, value is the a dict
        with node information.
        :type nodes_by_id: dictionary
        :param slabdriver:SlabDriver object, used to have access to slabdriver
        attributes.
        :type slabdriver:SlabDriver
        
        """
       
        for node_id in site_node_ids:
            try:
                node = nodes_by_id[node_id]
            except KeyError:
                self.logger.warning ("SlabImporter: cannot find node_id %s \
                        - ignored" %(node_id))
                continue             
            escaped_hrn =  \
            self.hostname_to_hrn_escaped(slabdriver.slab_api.root_auth, \
            node['hostname'])
            self.logger.info("SLABIMPORTER node %s " %(node))               
            hrn =  node['hrn']


            # xxx this sounds suspicious
            if len(hrn) > 64: 
                hrn = hrn[:64]
            node_record = self.find_record_by_type_hrn( 'node', hrn )
            if not node_record:
                pkey = Keypair(create=True)
                urn = hrn_to_urn(escaped_hrn, 'node') 
                node_gid = \
                    self.auth_hierarchy.create_gid(urn, \
                    create_uuid(), pkey)
                    
                def slab_get_authority(hrn):
                    return hrn.split(".")[0]
                    
                node_record = RegNode(hrn=hrn, gid=node_gid, 
                                    pointer = '-1',
                                    authority=slab_get_authority(hrn))
                try:
                        
                    node_record.just_created()
                    dbsession.add(node_record)
                    dbsession.commit()
                    self.logger.info("SlabImporter: imported node: %s" \
                                % node_record)  
                    self.update_just_added_records_dict(node_record)
                except SQLAlchemyError:
                    self.logger.log_exc("SlabImporter: \
                                    failed to import node") 
            else:
                #TODO:  xxx update the record ...
                pass
            node_record.stale = False
                    

    def init_person_key (self, person, slab_key):
        """ 
        
        Returns a tuple pubkey and pkey.
        
        :param person Person's data.
        :type person: dict
        :param slab_key: SSH public key, from LDAP user's data. 
        RSA type supported.
        :type slab_key: string
        :rtype (string, Keypair)
        """
        pubkey = None
        if  person['pkey']:
            # randomly pick first key in set
            pubkey = slab_key
            
            try:
                pkey = convert_public_key(pubkey)
            except TypeError:
                #key not good. create another pkey
                self.logger.warn('SlabImporter: \
                                    unable to convert public \
                                    key for %s' %person['hrn'])
                pkey = Keypair(create=True)
            
        else:
            # the user has no keys. 
            #Creating a random keypair for the user's gid
            self.logger.warn("SlabImporter: person %s does not have a  \
                        public key" %(person['hrn']))
            pkey = Keypair(create=True) 
        return (pubkey, pkey)
                                
        
    def import_persons_and_slices(self, slabdriver):
        """
        
        Gets user data from LDAP, process the information.
        Creates hrn for the user's slice, the user's gid, creates
        the RegUser record associated with user. Creates the RegKey record
        associated nwith the user's key.
        Saves those records into the SFA DB.
        import the user's slice onto the database as well by calling
        import_slice.
      
        :param slabdriver:SlabDriver object, used to have access to slabdriver
        attributes.
        :type slabdriver:SlabDriver
        """
        ldap_person_listdict = slabdriver.slab_api.GetPersons()
        self.logger.info("SLABIMPORT \t ldap_person_listdict %s \r\n" \
                %(ldap_person_listdict)) 
        
         # import persons
        for person in ldap_person_listdict : 
            
            self.logger.info("SlabImporter: person :" %(person))
            if 'ssh-rsa' not in person['pkey']:
                #people with invalid ssh key (ssh-dss, empty, bullshit keys...)
                #won't be imported
                continue
            person_hrn = person['hrn']
            slice_hrn = self.slicename_to_hrn(person['hrn'])
            
            # xxx suspicious again
            if len(person_hrn) > 64: 
                person_hrn = person_hrn[:64]
            person_urn = hrn_to_urn(person_hrn, 'user')
            
            
            self.logger.info("SlabImporter: users_rec_by_email %s " \
                                            %(self.users_rec_by_email))
            
            #Check if user using person['email'] from LDAP is already registered
            #in SFA. One email = one person. In this case, do not create another
            #record for this person
            #person_hrn returned by GetPerson based on senslab root auth + 
            #uid ldap
            user_record = self.find_record_by_type_hrn('user', person_hrn)
            
            if not user_record and  person['email'] in self.users_rec_by_email:
                user_record = self.users_rec_by_email[person['email']]
                person_hrn = user_record.hrn
                person_urn = hrn_to_urn(person_hrn, 'user')
                
            
            slice_record = self.find_record_by_type_hrn ('slice', slice_hrn)
                    
            slab_key = person['pkey']
            # new person
            if not user_record:
                (pubkey, pkey) = self.init_person_key(person, slab_key)
                if pubkey is not None and pkey is not None :
                    person_gid = \
                    self.auth_hierarchy.create_gid(person_urn, \
                    create_uuid(), pkey)
                    if person['email']:
                        self.logger.debug( "SLAB IMPORTER \
                            PERSON EMAIL OK email %s " %(person['email']))
                        person_gid.set_email(person['email'])
                        user_record = RegUser(hrn=person_hrn, \
                                            gid=person_gid, 
                                            pointer='-1', 
                                            authority=get_authority(person_hrn),
                                            email=person['email'])
                    else:
                        user_record = RegUser(hrn=person_hrn, \
                                            gid=person_gid, 
                                            pointer='-1', 
                                            authority=get_authority(person_hrn))
                        
                    if pubkey: 
                        user_record.reg_keys = [RegKey(pubkey)]
                    else:
                        self.logger.warning("No key found for user %s" \
                        %(user_record))
                            
                        try:    
                            user_record.just_created()
                            dbsession.add (user_record)
                            dbsession.commit()
                            self.logger.info("SlabImporter: imported person %s"\
                            %(user_record))
                            self.update_just_added_records_dict( user_record )
                            
                        except SQLAlchemyError:
                            self.logger.log_exc("SlabImporter: \
                                failed to import person  %s"%(person))       
            else:
                # update the record ?
                # if user's primary key has changed then we need to update 
                # the users gid by forcing an update here
                sfa_keys = user_record.reg_keys
                
                new_key = False
                if slab_key is not sfa_keys : 
                    new_key = True
                if new_key:
                    self.logger.info("SlabImporter: \t \t USER UPDATE \
                        person: %s" %(person['hrn']))
                    (pubkey, pkey) = self.init_person_key (person, slab_key)
                    person_gid = \
                        self.auth_hierarchy.create_gid(person_urn, \
                        create_uuid(), pkey)
                    if not pubkey:
                        user_record.reg_keys = []
                    else:
                        user_record.reg_keys = [RegKey(pubkey)]
                    self.logger.info("SlabImporter: updated person: %s" \
                    % (user_record))
                    
                if person['email']:
                    user_record.email = person['email']
                   
            try:       
                dbsession.commit()
                user_record.stale = False
            except SQLAlchemyError:
                self.logger.log_exc("SlabImporter: \
                failed to update person  %s"%(person)) 
            
            self.import_slice(slice_hrn, slice_record, user_record)
           
                       
    def import_slice(self, slice_hrn, slice_record, user_record):
        """
         
         Create RegSlice record according to the slice hrn if the slice
         does not exist yet.Creates a relationship with the user record 
         associated with the slice.
         Commit the record to the database.
        
         
        :param slice_hrn: Human readable name of the slice.
        :type slice_hrn: string
        :param slice_record: record of the slice found in the DB, if any.
        :type slice_record: RegSlice or None
        :param user_record: user record found in the DB if any.
        :type user_record: RegUser
        
        .. todo::Update the record if a slice record already exists.
        """
        if not slice_record :           
            pkey = Keypair(create=True)
            urn = hrn_to_urn(slice_hrn, 'slice')
            slice_gid = \
                self.auth_hierarchy.create_gid(urn, \
                create_uuid(), pkey)
            slice_record = RegSlice (hrn=slice_hrn, gid=slice_gid, 
                                        pointer='-1',
                                        authority=get_authority(slice_hrn))
            try:
                slice_record.just_created()
                dbsession.add(slice_record)
                dbsession.commit()
                
               
                self.update_just_added_records_dict ( slice_record )

            except SQLAlchemyError:
                self.logger.log_exc("SlabImporter: failed to import slice")
                
        #No slice update upon import in senslab 
        else:
            # xxx update the record ...
            self.logger.warning ("Slice update not yet implemented")
            pass
        # record current users affiliated with the slice


        slice_record.reg_researchers =  [user_record]
        try:
            dbsession.commit()
            slice_record.stale = False 
        except SQLAlchemyError:
            self.logger.log_exc("SlabImporter: failed to update slice")
            
             
    def run (self, options):
        """
        Create the special senslab table, slab_xp, in the senslab database.
        Import everything (users, slices, nodes and sites from OAR
        and LDAP) into the SFA database.
        Delete stale records that are no longer in OAR or LDAP.
        :param options:
        :type options: 
        """
        config = Config()
        
        slabdriver = SlabDriver(config)
        
        #Create special slice table for senslab 
        
        if not slabdriver.db.exists('slab_xp'):
            slabdriver.db.createtable()
            self.logger.info ("SlabImporter.run:  slab_xp table created ")

            
        # import site and node records in site into the SFA db.
        self.import_sites_and_nodes(slabdriver)
        #import users and slice into the SFA DB.   
        self.import_persons_and_slices(slabdriver)
      
         ### remove stale records
        # special records must be preserved
        system_hrns = [slabdriver.hrn, slabdriver.slab_api.root_auth,  \
                                        slabdriver.hrn+ '.slicemanager']
        for record in self.all_records: 
            if record.hrn in system_hrns: 
                record.stale = False
            if record.peer_authority:
                record.stale = False
          

        for record in self.all_records: 
            if record.type == 'user':
                self.logger.info("SlabImporter: stale records: hrn %s %s" \
                                            %(record.hrn,record.stale) )
            try:        
                stale = record.stale
            except :     
                stale = True
                self.logger.warning("stale not found with %s"%record)
            if stale:
                self.logger.info("SlabImporter: deleting stale record: %s" \
                %(record))
                
                try:
                    dbsession.delete(record)
                    dbsession.commit()         
                except SQLAlchemyError:
                    self.logger.log_exc("SlabImporter: failed to delete stale \
                    record %s" %(record) )

  

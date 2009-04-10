


from geni.util.faults import *
from geni.util.excep import *
from geni.util.method import Method
from geni.util.parameter import Parameter, Mixed
from geni.util.auth import Auth
from geni.util.record import GeniRecord
from geni.registry import Registries
from geni.util.debug import log

class resolve(Method):
    """
    Resolve a record.

    @param cred credential string authorizing the caller
    @param hrn human readable name to resolve
    @return a list of record dictionaries or empty list     
    """

    interfaces = ['registry']
    
    accepts = [
        Parameter(str, "Credential string"),
        Parameter(str, "Human readable name (hrn)")
        ]

    returns = [GeniRecord]
    
    def call(self, cred, hrn):
        
        self.api.auth.check(cred, 'resolve')
        
        # is this a foreign record
        if not hrn.startswith(self.api.hrn):
            registries = Registries(self.api)
            credential = self.api.getCredential()
            for registry in registries:
                if hrn.startswith(registry):
                    records = registries[registry].resolve(credential, hrn)
                    good_records = records   
        else:
            auth_hrn = self.api.auth.get_authority(hrn)
            if not auth_hrn:
                auth_hrn = hrn
            table = self.api.auth.get_auth_table(auth_hrn)
            records = table.resolve('*', hrn)
            if not records:
                raise RecordNotFound(hrn) 
            good_records = []
            for record in records:
                try:
                    self.api.fill_record_info(record)
                    good_records.append(record)
                except PlanetLabRecordDoesNotExist:
                    # silently drop the ones that are missing in PL
                    print >> log, "ignoring geni record ", record.get_name(), \
                              " because pl record does not exist"
                    table.remove(record)

        print good_records
        dicts = [record.as_dict() for record in good_records]

        return dicts    
            

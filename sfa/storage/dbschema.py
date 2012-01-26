import sys
import traceback

from sqlalchemy import MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from migrate.versioning.api import version, db_version, version_control, upgrade

from sfa.util.sfalogging import logger
from sfa.storage.model import init_tables

### this script will upgrade from a pre-2.1 db 
# * 1.0 and up to 1.1-4:  ('very old')    
#       was piggybacking the planetlab5 database
#       this is kind of out of our scope here, we don't have the credentials 
#       to connect to planetlab5, but this is documented in
#       https://svn.planet-lab.org/wiki/SFATutorialConfigureSFA#Upgradingnotes
#       and essentially this is seamless to users
# * from 1.1-5 up to 2.0-x: ('old')
#       uses the 'sfa' db and essentially the 'records' table,
#       as well as record_types
#       together with an 'sfa_db_version' table (version, subversion)
# * from 2.1:
#       we have an 'records' table, plus 'users' and the like
#       and once migrate has kicked in there is a table named 
#       migrate_db_version (repository_id, repository_path, version)
####
# An initial attempt to run this as a 001_*.py migrate script 
# did not quite work out (essentially we need to set the current version
# number out of the migrations logic)
# also this approach has less stuff in the initscript, which seems just right

class DBSchema:

    header="Upgrading to 2.1 or higher"

    def __init__ (self):
        from sfa.storage.alchemy import alchemy
        self.url=alchemy.url
        self.engine=alchemy.engine
        self.repository="/usr/share/sfa/migrations"
        self.meta=MetaData (bind=self.engine)

    def current_version (self):
        try:
            return db_version (self.url, self.repository)
        except:
            return None

    def table_exists (self, tablename):
        try:
            table=Table (tablename, self.meta, autoload=True)
            return True
        except NoSuchTableError:
            return False

    def drop_table (self, tablename):
        if self.table_exists (tablename):
            print >>sys.stderr, "%s: Dropping table %s"%(DBSchema.header,tablename)
            self.engine.execute ("drop table %s cascade"%tablename)
        else:
            print >>sys.stderr, "%s: no need to drop table %s"%(DBSchema.header,tablename)
        
    def handle_old_releases (self):
        try:
            # try to find out which old version this can be
            if not self.table_exists ('records'):
                # this likely means we've just created the db, so it's either a fresh install
                # or we come from a 'very old' depl.
                # in either case, an import is required but there's nothing to clean up
                print >> sys.stderr,"%s: make sure to run import"%(DBSchema.header,)
            elif self.table_exists ('sfa_db_version'):
                # we come from an 'old' version
                self.drop_table ('records')
                self.drop_table ('record_types')
                self.drop_table ('sfa_db_version')
            else:
                # we should be good here
                pass
        except:
            print >> sys.stderr, "%s: unknown exception"%(DBSchema.header,)
            traceback.print_exc ()

    # after this call the db schema and the version as known by migrate should 
    # reflect the current data model and the latest known version
    def init_or_upgrade (self):
        # check if under version control, and initialize it otherwise
        if self.current_version() is None:
            before="Unknown"
            # can be either a very old version, or a fresh install
            # for very old versions:
            self.handle_old_releases()
            # in any case, initialize db from current code and reflect in migrate
            init_tables(self.engine)
            code_version = version (self.repository)
            version_control (self.url, self.repository, code_version)
        else:
            # use migrate in the usual way
            before="%s"%self.current_version()
            upgrade (self.url, self.repository)
        after="%s"%self.current_version()
        if before != after:
            logger.info("DBSchema : upgraded from %s to %s"%(before,after))
    
    # this call will trash the db altogether
    def nuke (self):
        drop_tables(self.engine)

if __name__ == '__main__':
    DBSchema().init_or_upgrade()
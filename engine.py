"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Implements the Terminal Engine in Tank, e.g the a way to run apps inside of a standard python
terminal session.
"""

from tank.platform import Engine
import tank
import sys


class TerminalEngine(Engine):
    """
    An engine for a terminal.    
    """
        
    def init_engine(self):
        pass
                
    ##########################################################################################
    # logging interfaces

    def log_debug(self, msg):
        if self.get_setting("debug_logging", False):
            sys.stdout.write("DEBUG: %s\n" % msg)
    
    def log_info(self, msg):
        sys.stdout.write("%s\n" % msg)
        
    def log_warning(self, msg):
        # note: java bridge only captures stdout, not stderr
        sys.stdout.write("WARNING: %s\n" % msg)
    
    def log_error(self, msg):
        # note: java bridge only captures stdout, not stderr
        sys.stdout.write("ERROR: %s\n" % msg)

    

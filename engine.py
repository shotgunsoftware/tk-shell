"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Implements the Terminal Engine in Tank, e.g the a way to run apps inside of a standard python
terminal session.
"""

import sys
import code

import tank
from tank.platform import Engine


class ShellEngine(Engine):
    """
    An engine for a terminal.    
    """
        
    def init_engine(self):
        pass
        
    def run_command(self, command_name, *args, **kwargs):
        command = self.commands.get(command_name, {}).get("callback")

        if not command:
            self.log_error("A command named %s is not registered with Tank in this environment." % command_name)
            return False
        else:
            command(*args, **kwargs)
        return True

    def interact(self, *args, **kwargs):
        """
        Opens a python interactive shell with commands registered with the engine and 
        arguments passed on the command line available in the environment.
        """

        symbol_table = globals()
        symbol_table.update(locals())
        # give access to list of commands
        symbol_table["command_names"] = self.commands.keys()
        # put commands into locals
        for name, value in self.commands.items():
            symbol_table[name] = value["callback"]

        # put kwargs into locals
        symbol_table.update(kwargs)
        
        banner =  "Entering Tank interactive mode.\n"
        banner += "See 'command_names' variable for a list of app commands registered with this engine."
        banner += "See 'args' variable for aruments, see 'kwargs' variable for keyword arguments."
        code.interact(local=symbol_table, banner=banner)
        return True

    @property
    def has_ui(self):
        """
        The shell engine never has a UI
        """
        return False
    

    ##########################################################################################
    # logging interfaces

    def log_debug(self, msg):
        if self.get_setting("debug_logging", False):
            sys.stdout.write("DEBUG: %s\n" % msg)
    
    def log_info(self, msg):
        sys.stdout.write("%s\n" % msg)
        
    def log_warning(self, msg):
        sys.stderr.write("WARNING: %s\n" % msg)
    
    def log_error(self, msg):
        sys.stderr.write("ERROR: %s\n" % msg)


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
        
        # create queue
        self._queue = []
        
                
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

class TankProgressWrapper(object):
    """
    A progressbar wrapper.
    """
    def __init__(self, title):
        self.__title = title
    
    def set_progress(self, percent):
        """Prints current progress."""
        print("TANK_PROGRESS Task:%s Progress:%d%%" % (self.__title, percent))
    
    ##########################################################################################
    # queue implementation
    
    def add_to_queue(self, name, method, args):
        """
        Terminal implementation of the engine synchronous queue. Adds an item to the queue.
        """
        qi = {}
        qi["name"] = name
        qi["method"] = method
        qi["args"] = args
        self._queue.append(qi)
    
    def report_progress(self, percent):
        """
        Callback function part of the engine queue. This is being passed into the methods
        that are executing in the queue so that they can report progress back if they like
        """
        self._current_queue_item["progress_obj"].set_progress(percent)
    
    def execute_queue(self):
        """
        Executes all items in the queue, one by one, in a controlled fashion
        """
        # create progress items for all queue items
        for x in self._queue:
            x["progress_obj"] = TankProgressWrapper(x["name"])

        # execute one after the other syncronously
        while len(self._queue) > 0:
            
            # take one item off
            self._current_queue_item = self._queue.pop(0)
            
            # process it
            try:
                kwargs = self._current_queue_item["args"]
                # force add a progress_callback arg - this is by convention
                kwargs["progress_callback"] = self.report_progress
                # execute
                self._current_queue_item["method"](**kwargs)
            except:
                # error and continue
                # todo: may want to abort here - or clear the queue? not sure.
                self.log_exception("Error while processing callback %s" % self._current_queue_item)
            finally:
                self._current_queue_item["progress"].close()
        

            
            
            
    

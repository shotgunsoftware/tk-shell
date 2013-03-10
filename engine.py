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
        self._has_ui = False
        self._qt_application = None
        self._init_pyside()
        
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
        return self._has_ui
    

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

    ##########################################################################################
    # pyside
    
    def _init_pyside(self):
        """
        Handles the pyside init
        """
        
        # first see if pyside is already present - in that case skip!
        try:
            from PySide import QtGui
        except:
            # fine, we don't expect pyside to be present just yet
            self.log_debug("PySide not detected - This instance of tk-shell cannot run UI apps.")
        else:
            # looks like pyside is already working! No need to do anything
            self.log_debug("PySide detected - Tank will use the version in %s." % QtGui.__file__)
            self._has_ui = True
        
    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a non-modal dialog window in a way suitable for this engine. 
        The engine will attempt to parent the dialog nicely to the host application.
        
        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.
        
        Additional parameters specified will be passed through to the widget_class constructor.
        
        :returns: the created widget_class instance
        """
        if not self._has_ui:
            self.log_error("Cannot show dialog! No pyside appears to be installed.")
        
        start_app_loop = False
        if not self._qt_running:
            self._qt_application = QtGui.QApplication()
            start_app_loop = True
            
        obj = Engine.show_dialog(self, title, bundle, widget_class, *args, **kwargs)
        if start_app_loop:
            self._qt_application.exec_()
            # this is a bit weird - we are not returning the dialog object because
            # at this point the application has already exited
            return None
        else:
            # a dialog was called by a signal or slot
            # in the qt message world. return its handle
            return obj
    
    def show_modal(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a modal dialog window in a way suitable for this engine. The engine will attempt to
        integrate it as seamlessly as possible into the host application. This call is blocking 
        until the user closes the dialog.
        
        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.
        
        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: (a standard QT dialog status return code, the created widget_class instance)
        """
        if not self._has_ui:
            self.log_error("Cannot show dialog! No pyside appears to be installed.")

        if not self._qt_running:
            # qt is not running - meaning there are no other dialogs
            # this is a chicken and egg thing - need to handle this dialog
            # as a non-modal becuase of dialog.exec() and app.exec()
            return self.show_modal(title, bundle, widget_class, *args, **kwargs)
        else:
            # qt is running! Just use std base class implementation
            return Engine.show_modal(self, title, bundle, widget_class, *args, **kwargs)


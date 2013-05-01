"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Implements the Terminal Engine in Tank, e.g the a way to run apps inside of a standard python
terminal session.
"""

import sys
import os
import code

import tank
import inspect
import logging

from tank.platform import Engine
from tank import TankError

class ShellEngine(Engine):
    """
    An engine for a terminal.    
    """
    def __init__(self, *args, **kwargs):
        # passthrough so we can init stuff
        self._has_ui = False
        self._ui_created = False
        
        # set up a very basic logger, assuming it will be overridden
        self._log = logging.getLogger("tank.tk-shell")
        self._log.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        formatter = logging.Formatter()
        ch.setFormatter(formatter)
        self._log.addHandler(ch)
        
        if len(args) > 0 and isinstance(args[0], tank.Tank):
            if hasattr(args[0], "log"):
                # there is a tank.log on the API instance.
                # hook this up with our logging
                self._log = args[0].log
        
        super(ShellEngine, self).__init__(*args, **kwargs)
    

    def init_engine(self):
        """
        Init
        """

    @property
    def has_ui(self):
        return self._has_ui

    def has_received_ui_creation_requests(self):
        """
        returns true if one or more windows have been requested
        via the show_dialog methods
        """
        return self._ui_created

    ##########################################################################################
    # command handling

    def execute_command(self, cmd_key, args):
        """
        Executes a given command.
        """
        cb = self.commands[cmd_key]["callback"]
        
        # make sure the number of parameters to the command are correct
        cb_arg_list = inspect.getargspec(cb)[0]
        if len(cb_arg_list) > 0 and  cb_arg_list[0] == 'self':
            cb_arg_list = cb_arg_list[1:]
            
        if len(args) != len(cb_arg_list):
            raise TankError("Cannot run command! Expected command arguments %s" % cb_arg_list)
        
        if not self.has_ui:
            # QT not available - just run the command straight
            return cb(*args)
        else:
            from tank.platform.qt import QtCore, QtGui
            
            # we got QT capabilities. Start a QT app and fire the command into the app
            tk_shell = self.import_module("tk_shell")
            t = tk_shell.Task(self, cb, args)
            
            # start up our QApp now
            QtGui.QApplication.setStyle("cleanlooks")
            qt_application = QtGui.QApplication([])
            css_file = os.path.join(self.disk_location, "resources", "dark.css")
            f = open(css_file)
            css = f.read()
            f.close()
            qt_application.setStyleSheet(css) 
            
            # when the QApp starts, initialize our task code 
            QtCore.QTimer.singleShot(0, t, QtCore.SLOT('run_command()'))
               
            # and ask the main app to exit when the task emits its finished signal
            t.finished.connect(qt_application.quit )
               
            # start the application loop. This will block the process until the task
            # has completed - this is either triggered by a main window closing or
            # byt the finished signal being called from the task class above.
            qt_application.exec_()
            


    ##########################################################################################
    # logging interfaces

    def log_debug(self, msg):
        self._log.debug(msg)
    
    def log_info(self, msg):
        self._log.info(msg)
        
    def log_warning(self, msg):
        self._log.warning(msg)
    
    def log_error(self, msg):
        self._log.error(msg)

    ##########################################################################################
    # pyside / qt
    
    def _define_qt_base(self):
        """
        check for pyside then pyqt
        """
        base = {"qt_core": None, "qt_gui": None, "dialog_base": None}
        self._has_ui = False
        
        if not self._has_ui:
            try:
                from PySide import QtCore, QtGui
                import PySide

                # a simple dialog proxy that pushes the window forward
                class ProxyDialogPySide(QtGui.QDialog):
                    def show(self):
                        QtGui.QDialog.show(self)
                        self.activateWindow()
                        self.raise_()

                    def exec_(self):
                        self.activateWindow()
                        self.raise_()
                        # the trick of activating + raising does not seem to be enough for
                        # modal dialogs. So force put them on top as well.
                        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
                        QtGui.QDialog.exec_(self)
                        
                
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPySide
                self.log_debug("Successfully initialized PySide %s located in %s." % (PySide.__version__, PySide.__file__))
                self._has_ui = True
            except ImportError:
                pass
            except Exception, e:
                self.log_warning("Error setting up pyside. Pyside based UI support will not "
                                 "be available: %s" % e)
        
        if not self._has_ui:
            try:
                from PyQt4 import QtCore, QtGui
                import PyQt4
                
                # a simple dialog proxy that pushes the window forward
                class ProxyDialogPyQt(QtGui.QDialog):
                    def show(self):
                        QtGui.QDialog.show(self)
                        self.activateWindow()
                        self.raise_()
                
                    def exec_(self):
                        self.activateWindow()
                        self.raise_()
                        # the trick of activating + raising does not seem to be enough for
                        # modal dialogs. So force put them on top as well.                        
                        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
                        QtGui.QDialog.exec_(self)
                
                
                # hot patch the library to make it work with pyside code
                QtCore.Signal = QtCore.pyqtSignal                
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPyQt
                self.log_debug("Successfully initialized PyQt located in %s." % PyQt4.__file__)
                self._has_ui = True
            except ImportError:
                pass
            except Exception, e:
                self.log_warning("Error setting up PyQt. PyQt based UI support will not "
                                 "be available: %s" % e)
        
        return base
        
        
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
            self.log_error("Cannot show dialog %s! No QT support appears to exist in this engine. "
                           "In order for the shell engine to run UI based apps, either pyside "
                           "or PyQt needs to be installed in your system." % title)
            return
        
        self._ui_created = True
        
        return Engine.show_dialog(self, title, bundle, widget_class, *args, **kwargs)    
    
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
            self.log_error("Cannot show dialog %s! No QT support appears to exist in this engine. "
                           "In order for the shell engine to run UI based apps, either pyside "
                           "or PyQt needs to be installed in your system." % title)
            return

        self._ui_created = True
        
        return Engine.show_modal(self, title, bundle, widget_class, *args, **kwargs)




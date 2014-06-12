# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Implements the Terminal Engine in Tank, e.g the a way to run apps inside of a standard python
terminal session.
"""

import sys
import os
import code

import tank
import types
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
        cb_arg_spec = inspect.getargspec(cb)
        cb_arg_list = cb_arg_spec[0]
        cb_var_args = cb_arg_spec[1]
        
        if hasattr(cb, "__self__"):
            # first argument to cb will be class instance:
            cb_arg_list = cb_arg_list[1:]

        # ensure the correct/minimum number of arguments have been passed:
        have_expected_args = False
        if cb_var_args:
            have_expected_args = (len(args) >= len(cb_arg_list))
        else:
            have_expected_args = (len(args) == len(cb_arg_list)) 
        
        if not have_expected_args:
            expected_args = list(cb_arg_list)
            if cb_var_args:
                expected_args.append("*%s" % cb_var_args)
            raise TankError("Cannot run command! Expected command arguments (%s)" % ", ".join(expected_args))
        
        if not self.has_ui:
            # QT not available - just run the command straight
            return cb(*args)
        else:
            from tank.platform.qt import QtCore, QtGui
            
            # we got QT capabilities. Start a QT app and fire the command into the app
            tk_shell = self.import_module("tk_shell")
            t = tk_shell.Task(self, cb, args)
            
            # start up our QApp now
            qt_application = QtGui.QApplication([])
            qt_application.setWindowIcon(QtGui.QIcon(self.icon_256))
            self._initialize_dark_look_and_feel()
            
            # when the QApp starts, initialize our task code 
            QtCore.QTimer.singleShot(0, t.run_command )
               
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
        # proxy class used when QT does not exist on the system.
        # this will raise an exception when any QT code tries to use it
        class QTProxy(object):                        
            def __getattr__(self, name):
                raise tank.TankError("Looks like you are trying to run an App that uses a QT "
                                     "based UI, however the Shell engine could not find a PyQt "
                                     "or PySide installation in your python system path. We " 
                                     "recommend that you install PySide if you want to "
                                     "run UI applications from the Shell.")
        
        base = {"qt_core": QTProxy(), "qt_gui": QTProxy(), "dialog_base": None}
        self._has_ui = False
        
        if not self._has_ui:
            try:
                from PySide import QtCore, QtGui
                import PySide

                # Some old versions of PySide don't include version information
                # so add something here so that we can use PySide.__version__ 
                # later without having to check!
                if not hasattr(PySide, "__version__"):
                    PySide.__version__ = "<unknown>"

                # tell QT to interpret C strings as utf-8
                utf8 = QtCore.QTextCodec.codecForName("utf-8")
                QtCore.QTextCodec.setCodecForCStrings(utf8)

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
                self.log_debug("Successfully initialized PySide '%s' located in %s." 
                               % (PySide.__version__, PySide.__file__))
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
                
                # tell QT to interpret C strings as utf-8
                utf8 = QtCore.QTextCodec.codecForName("utf-8")
                QtCore.QTextCodec.setCodecForCStrings(utf8)                
                
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
                QtCore.Slot = QtCore.pyqtSlot
                QtCore.Property = QtCore.pyqtProperty             
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPyQt
                self.log_debug("Successfully initialized PyQt '%s' located in %s." 
                               % (QtCore.PYQT_VERSION_STR, PyQt4.__file__))
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




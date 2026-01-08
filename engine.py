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
Implements the Terminal Engine in Tank, e.g the a way to run apps inside of a
standard python terminal session.
"""

import tank
import inspect
import logging
import sys
import os
import platform

from tank.platform import Engine
from tank import TankError


class ShellEngine(Engine):
    """
    An engine for a terminal.
    """

    def __init__(self, *args, **kwargs):
        # passthrough so we can init stuff

        # the has_qt flag indicates that the QT subsystem is present and can be started
        self._has_qt = False

        self._ui_created = False

        self._log = None
        self._stream_handler = None

        # Check if the Toolkit instance has a log and if so, we'll use it.
        if len(args) > 0 and isinstance(args[0], tank.Tank):
            if hasattr(args[0], "log"):
                # there is a tank.log on the API instance.
                # hook this up with our logging
                self._log = args[0].log

        # If no log was found, we'll install our own handler so things
        # get printed to the console.
        if self._log is None:
            # set up a very basic logger, assuming it will be overridden
            self._log = logging.getLogger("tank.tk-shell")
            self._log.setLevel(logging.INFO)
            self._stream_handler = logging.StreamHandler()
            formatter = logging.Formatter()
            self._stream_handler.setFormatter(formatter)
            self._log.addHandler(self._stream_handler)

        super().__init__(*args, **kwargs)

    def init_engine(self):
        """
        Init
        """

    def destroy_engine(self):
        """
        Called when engine is destroyed.

        This will remove the logger.
        """
        self._cleanup_logger()

    def __del__(self):
        """
        Called when the object is garbaged-collected.
        """
        # If the destroy_engine has not been called (in a failed test for example), we still
        # need to remove the stream logger if available. Otherwise subsequent tests will
        # have more and more loggers added to tank.tk-shell.
        self._cleanup_logger()

    def _cleanup_logger(self):
        """
        Removes the stream handler if it exists from the current logger.
        """
        if self._stream_handler is not None:
            self._log.removeHandler(self._stream_handler)
            self._stream_handler = None

    @property
    def has_ui(self):
        """
        Indicates if this engine has a UI. The shell engine will have one only if
        QApplication has been instantiated.

        :returns: True if UI is available, False otherwise.
        """
        # Testing for UI this way allows the tank shell command to show UIs afte45

        # a QApplication has been created.
        if self._has_qt:
            from tank.platform.qt import QtGui

            return QtGui.QApplication.instance() is not None
        else:
            return False

    def has_received_ui_creation_requests(self):
        """
        returns true if one or more windows have been requested
        via the show_dialog methods
        """
        return self._ui_created

    ###################################################################################
    # properties

    @property
    def context_change_allowed(self):
        """
        Allows on-the-fly context changing.
        """
        return True

    ###################################################################################
    # command handling

    def execute_command(self, cmd_key, args):
        """
        Executes a given command.
        """
        cb = self.commands[cmd_key]["callback"]

        # make sure the number of parameters to the command are correct
        cb_arg_spec = inspect.getfullargspec(cb)
        cb_arg_list = cb_arg_spec[0]
        cb_var_args = cb_arg_spec[1]

        if hasattr(cb, "__self__"):
            # first argument to cb will be class instance:
            cb_arg_list = cb_arg_list[1:]

        # ensure the correct/minimum number of arguments have been passed:
        have_expected_args = False
        if cb_var_args:
            have_expected_args = len(args) >= len(cb_arg_list)
        else:
            have_expected_args = len(args) == len(cb_arg_list)

        if not have_expected_args:
            expected_args = list(cb_arg_list)
            if cb_var_args:
                expected_args.append("*%s" % cb_var_args)
            raise TankError(
                "Cannot run command! Expected command arguments (%s)"
                % ", ".join(expected_args)
            )

        if not self._has_qt:
            # QT not available - just run the command straight
            return cb(*args)
        else:
            from sgtk.platform.qt import QtCore, QtGui

            # we got QT capabilities. Start a QT app and fire the command into the app
            tk_shell = self.import_module("tk_shell")
            t = tk_shell.Task(self, cb, args)

            # start up our QApp now, if none is already running
            qt_application = None
            if not QtGui.QApplication.instance():
                qt_application = QtGui.QApplication([])
                qt_application.setWindowIcon(QtGui.QIcon(self.icon_256))
                self._initialize_dark_look_and_feel()

            # if we didn't start the QApplication here, leave the responsibility
            # to run the exec loop and quit to the initial creator of the QApplication
            if qt_application:
                # when the QApp starts, initialize our task code
                QtCore.QTimer.singleShot(0, t.run_command)
                # and ask the main app to exit when the task emits its finished signal
                t.finished.connect(qt_application.quit)

                # start the application loop. This will block the process until the task
                # has completed - this is either triggered by a main window closing or
                # byt the finished signal being called from the task class above.
                qt_application.exec()
            else:
                # we can run the command now, as the QApp is already started
                t.run_command()

    ###################################################################################
    # logging interfaces

    def log_debug(self, msg):
        self._log.debug(msg)

    def log_info(self, msg):
        self._log.info(msg)

    def log_warning(self, msg):
        self._log.warning(msg)

    def log_error(self, msg):
        self._log.error(msg)

    ###################################################################################
    # metrics

    @property
    def host_info(self):
        """
        Returns information about the application hosting this engine.

        :returns: A {"name": "Python", "version": Python version} dictionary.
        """
        return {
            "name": "Python",
            "version": platform.python_version(),
        }

    ##########################################################################################
    # PySide / QT

    def _define_qt_base(self):
        """
        Define the QT environment.
        """
        base = super()._define_qt_base()

        if not base["qt_gui"]:
            self._has_qt = False

            # proxy class used when QT does not exist on the system.
            # this will raise an exception when any QT code tries to use it
            class QTProxy(object):
                def __getattr__(self, name):
                    raise tank.TankError(
                        "The Flow Production Tracking App you are trying to execute "
                        "requires a full QT environment in order to render its UI. A valid "
                        "PySide2/PySide6 installation could not be found in your python "
                        "system path."
                    )

            base = {"qt_core": QTProxy(), "qt_gui": QTProxy(), "dialog_base": None}

        else:
            self._has_qt = True
            QtCore = base["qt_core"]
            QtGui = base["qt_gui"]

            # Tell QT4 to interpret C strings as utf-8.
            # On PySide2 we patch QTextCodec with a do-nothing stub
            # for setCodecForCStrings(), so this will have no effect.
            utf8 = QtCore.QTextCodec.codecForName("utf-8")
            QtCore.QTextCodec.setCodecForCStrings(utf8)

            # a simple dialog proxy that pushes the window forward
            class ProxyDialogPyQt(QtGui.QDialog):
                def show(self):
                    QtGui.QDialog.show(self)
                    self.activateWindow()
                    self.raise_()

                def exec(self):
                    self.activateWindow()
                    self.raise_()
                    # the trick of activating + raising does not seem to be enough for
                    # modal dialogs. So force put them on top as well.
                    self.setWindowFlags(
                        QtCore.Qt.WindowStaysOnTopHint | self.windowFlags()
                    )
                    return QtGui.QDialog.exec(self)

            base["dialog_base"] = ProxyDialogPyQt

            # also figure out if qt is already running
            if QtGui.QApplication.instance():
                self._has_ui = True

        return base

    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a non-modal dialog window in a way suitable for this engine.
        The engine will attempt to parent the dialog nicely to the host application.

        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with
            this window
        :param widget_class: The class of the UI to be constructed. This must derive
            from QWidget.

        Additional parameters specified will be passed through to the widget_class
            constructor.

        :returns: the created widget_class instance
        """
        if not self._has_qt:
            self.log_error(
                "Cannot show dialog %s! No QT support appears to exist in this engine. "
                "In order for the shell engine to run UI based apps, either pyside "
                "or PyQt needs to be installed in your system." % title
            )
            return

        self._ui_created = True

        return Engine.show_dialog(self, title, bundle, widget_class, *args, **kwargs)

    def show_modal(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a modal dialog window in a way suitable for this engine. The engine
        will attempt to integrate it as seamlessly as possible into the host
        application. This call is blocking until the user closes the dialog.

        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with
            this window
        :param widget_class: The class of the UI to be constructed. This must derive
            from QWidget.

        Additional parameters specified will be passed through to the widget_class
            constructor.

        :returns: (a standard QT dialog status return code, the created widget_class
            instance)
        """
        if not self._has_qt:
            self.log_error(
                "Cannot show dialog %s! No QT support appears to exist in this engine. "
                "In order for the shell engine to run UI based apps, either pyside "
                "or PyQt needs to be installed in your system." % title
            )
            return

        self._ui_created = True

        return Engine.show_modal(self, title, bundle, widget_class, *args, **kwargs)

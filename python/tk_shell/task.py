# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import tank

from tank.platform.qt import QtCore


class Task(QtCore.QObject):
    """
    This is a wrapper class which allows us to run tank commands
    inside the QT universe. This approach is handy when an engine needs
    to start up a qt event loop as part of its initailization.
    """

    finished = QtCore.Signal()

    def __init__(self, engine, callback, args):
        QtCore.QObject.__init__(self)
        self._callback = callback
        self._args = args
        self._engine = engine

    def run_command(self):

        try:
            # execute the callback
            self._callback(*self._args)

        except tank.TankError as e:
            self._engine.log_error(str(e))

        except KeyboardInterrupt:
            self._engine.log_info("The operation was cancelled by the user.")

        except Exception:
            self._engine.log_exception("A general error was reported.")

        finally:
            # broadcast that we have finished this command
            if not self._engine.has_received_ui_creation_requests():
                # while the app has been doing its thing, no UIs were
                # created (at least not any tank UIs) - assume it is a
                # console style app and that the end of its callback
                # execution means that it is complete and that we should return
                self.finished.emit()

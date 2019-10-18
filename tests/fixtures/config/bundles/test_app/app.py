# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
A simple app to support unit tests.
"""

import sgtk


class TestApp(sgtk.platform.Application):
    """
    Test app with a single action that displays a dialog with a button
    that closes the window.

    You can close the dialog by doing
    ``engine.apps["test_app"].dismiss_button.click()``
    """

    def init_app(self):
        self.dismiss_button = None
        if not self.engine.has_ui:
            return

        self.engine.register_command("test_app", self._show_app)

    def _show_app(self, auto_dismiss):
        """
        Shows an app with a button in it.
        """

        class AppDialog(sgtk.platform.qt.QtGui.QWidget):
            def __init__(self, parent=None):
                super(AppDialog, self).__init__(parent)
                self._layout = sgtk.platform.qt.QtGui.QVBoxLayout(self)
                self.button = sgtk.platform.qt.QtGui.QPushButton("Close", parent=self)
                self.button.clicked.connect(self.close)
                self._layout.addWidget(self.button)

        widget = self.engine.show_dialog("Simple Test App", self, AppDialog)

        if auto_dismiss:
            sgtk.platform.qt.QtCore.QTimer.singleShot(500, widget.button.click)

        self.dismiss_button = widget.button

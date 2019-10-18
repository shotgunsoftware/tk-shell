# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys

import sgtk

from tank_test.tank_test_base import TankTestBase
from tank_test.tank_test_base import setUpModule  # noqa


class TestShowDialog(TankTestBase):
    """
    Tests the engine.show_dialog method.
    """

    def setUp(self):
        """
        Prepares the engine and makes sure Qt is ready.
        """
        super(TestShowDialog, self).setUp()
        self.setup_fixtures()

        context = sgtk.Context(self.tk)
        self.engine = sgtk.platform.start_engine("tk-shell", self.tk, context)

        self._dialog_dimissed = False

    def tearDown(self):
        self.engine.destroy()
        super(TestShowDialog, self).tearDown()

    def test_01_execute_command_when_qt_not_initialized(self):
        self.assertIsNone(
            sgtk.platform.qt.QtGui.QApplication.instance(),
            "This should always run first.",
        )
        self.engine.execute_command("test_app", [True])

    def test_02_execute_command_when_qt_init(self):
        self.engine.execute_command("test_app", [False])
        # Process events
        sgtk.platform.qt.QtGui.QApplication.instance().processEvents()
        # Click the dismiss button
        self.engine.apps["test_app"].dismiss_button.click()
        # Process the remaining events.
        sgtk.platform.qt.QtGui.QApplication.instance().processEvents()

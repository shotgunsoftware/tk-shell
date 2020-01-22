# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

from tank_test.tank_test_base import TankTestBase
from tank_test.tank_test_base import setUpModule  # noqa


class TestShowDialog(TankTestBase):
    """
    Tests the engine.execute_command method.
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
        """
        Tears down the engine and everything else from the base class.
        """
        self.engine.destroy()
        super(TestShowDialog, self).tearDown()

    def test_01_execute_command_when_qt_not_initialized(self):
        """
        Ensure execute_command works when QApplication is missing.
        """
        self.assertIsNone(
            sgtk.platform.qt.QtGui.QApplication.instance(),
            "This should always run first.",
        )
        # Calls execute_command. Note that since tests are sorted
        # alphabetically, test_01 will run first, which means there
        # is no QApplication yet.
        #
        # This is important because execute_command behaves differently
        # if QApplication is instantiated or not. If it is not
        # instantiated, it will block. We can't fire a single shot timer
        # that would find and close the dialog, because we can't queue it
        # yet, as there is no message loop yet.
        #
        # Because of this, the test app receives a flag that tells it to
        # auto-close itself.
        self.engine.execute_command("test_app", [True])

    def test_02_execute_command_when_qt_init(self):
        """
        Ensure execute_command works when QApplication is instantiated.
        """
        # We're the second test now, so we're guaranteed QApplication is set.
        self.assertIsNotNone(
            sgtk.platform.qt.QtGui.QApplication.instance(),
            "This should never run first.",
        )
        # Run the app and don't auto-close, we'll click the button ourselves.
        self.engine.execute_command("test_app", [False])
        # Process events
        sgtk.platform.qt.QtGui.QApplication.instance().processEvents()
        # Click the dismiss button
        self.engine.apps["test_app"].dismiss_button.click()
        # Process the remaining events.
        sgtk.platform.qt.QtGui.QApplication.instance().processEvents()

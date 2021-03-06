#-*- coding: utf-8 -*-
#
# Copyright (c) 2015 blackPanther OS - Charles Barcza
# GPL
#
from smart.interfaces.qt5.interface import QtInterface
from smart.interfaces.qt5 import getPixmap, centerWindow
from smart import *
import time, sys
from PyQt5 import *

#import PyQt4 

class QtCommandInterface(QtInterface):

    def __init__(self, ctrl, argv=None):
        QtInterface.__init__(self, ctrl, argv)
        self._status = QtStatus()

    def showStatus(self, msg):
        self._status.show(msg)
        while QtCore.QEventLoop().isRunning():
            QtGui.QCoreApplication.eventLoop().processEvents(QtGui.QEventLoop.AllEvents)

    def hideStatus(self):
        self._status.hide()
        while QtCore.QEventLoop().isRunning():
            QtGui.QCoreApplication.eventLoop().processEvents(QtGui.QEventLoop.AllEvents)

    def run(self, command=None, argv=None):
        result = QtInterface.run(self, command, argv)        
        self._status.wait()
        while self._log.isVisible():
            time.sleep(0.1)
            while QtCore.QEventLoop().isRunning():
                QtGui.QCoreApplication.eventLoop().processEvents(QtGui.QEventLoop.AllEvents)
        return result

class QtStatus(object):

    def __init__(self):
        self._window = QtGui.QDialog()
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Status"))
        self._window.setModal(True)
        self._vbox = QtGui.QWidget(self._window)
        #self._vbox.setMargin(20)
        #self._vbox.setMargin(0)
        #self._vbox.setSpacing(5)

        self._label = QtGui.QLabel(self._vbox)
        self._label.show()

        self._lastshown = 0

    def show(self, msg):
        self._label.setText(msg)
        self._vbox.adjustSize()
        self._window.adjustSize()
        self._window.show()
        centerWindow(self._window)
        self._lastshown = time.time()
        while QtCore.QEventLoop().isRunning():
            QtCore.QEventLoop().processEvents(QtGui.QEventLoop.AllEvents)

    def hide(self):
        self._window.hide()

    def isVisible(self):
        return self._window.isVisible()

    def wait(self):
        while self.isVisible() and self._lastshown+3 > time.time():
            time.sleep(0.3)
            while QtCore.QEventLoop().isRunning():
                QtCore.QEventLoop().processEvents(QtGui.QEventLoop.AllEvents)



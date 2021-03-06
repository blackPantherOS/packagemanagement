#-*- coding: utf-8 -*-
#
# Copyright (c) 2015 blackPanther OS - Charles Barcza
# GPL
#
from smart.interfaces.qt5 import getPixmap, centerWindow
from smart.util.strtools import strToBool
from smart.const import NEVER
from smart.channel import *
from smart import *
from PyQt5 import QtGui as QtGui, QtWidgets

from PyQt5 import QtCore as QtCore, QtWidgets

import textwrap
import os

class RadioAction(QtWidgets.QAction):

    def __init__(self, radio, name, label=None):
        QtWidgets.QAction.__init__(self, name, radio)
        self._radio = radio
    
    def connect(self, object, field, userdata):
        self._object = object
        self._field = field
        self._userdata = userdata
        signal = "toggled(bool)"
        # FIXME Ambiguous syntax for this signal connection, can't refactor it.
        QtCore.QObject.connect(self._radio, QtCore.SIGNAL(signal), self.slot)
    
    def slot(self, state):
        if state:
            setattr(self._object, self._field, self._userdata)
         
class QtChannels(object):

    def __init__(self, parent=None):

        self._changed = False

        self._window = QtWidgets.QDialog(None)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Channels"))
        self._window.setModal(True)

        self._window.setMinimumSize(580, 350)

        vbox = QtWidgets.QWidget(self._window)
        layout = QtWidgets.QVBoxLayout(vbox) 
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        #vbox = QtGui.QVBox(self._window)
        layout.setContentsMargins(1, 0, 1, 0, 1, 0, 1, 0)
        layout.setSpacing(10)
        vbox.show()

        self._vbox = vbox

        self._treeview = QtWidgets.QTreeWidget(vbox)
        self._treeview.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        self._treeview.setMinimumSize(570, 320)
        #QTreeView.expandAll(self._treeview)
        #self._treeview.setAllColumnsShowFocus(True)
        #self._treeview.setSelectionMode(QtGui.QListView.Single)
        self._treeview.show()
        layout.addWidget(self._treeview)

        self._treeview.itemSelectionChanged .connect(self.selectionChanged)
        self._treeview.itemDoubleClicked [QTableWidgetItem].connect(self.doubleClicked)

        #self._treeview.addColumn("")
        #self._treeview.addColumn(_("Pri"))
        #self._treeview.addColumn(_("Alias"))
        #self._treeview.addColumn(_("Type"))
        #self._treeview.addColumn(_("Name"))
        self._treeview.setHeaderLabels(["", _("Pri"), _("Alias"), _("Type"), _("Name")])
        
        #bbox = QtGui.QHBox(vbox)
        bbox = QtWidgets.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtWidgets.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtWidgets.QPushButton(_("New"), bbox)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-add")))
        button.show()
        button.clicked[()].connect(self.newChannel)
        self._newchannel = button
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("Delete"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-delete")))
        button.show()
        button.clicked[()].connect(self.delChannel)
        self._delchannel = button
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("Edit"), bbox)
        button.setEnabled(False)
        button.setIcon(QtGui.QIcon(getPixmap("crystal-edit")))
        button.show()
        button.clicked[()].connect(self.editChannel)
        self._editchannel = button
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("Close"), bbox)
        button.clicked[()].connect(self._window.accept)
        layout.addWidget(button)

        button.setDefault(True)
        vbox.adjustSize()

    def fill(self):
        self._treeview.clear()
        channels = sysconf.get("channels", {})
        aliases = channels.keys()
        aliases.sort()
        for alias in aliases:
            channel = channels[alias]
            #item = QtGui.QCheckListItem(self._treeview, "", QtGui.QCheckListItem.CheckBoxController)
            item = QtWidgets.QTreeWidgetItem(self._treeview)
            item.setCheckState(0, not strToBool(channel.get("disabled")) and QtCore.Qt.Checked or QtCore.Qt.Unchecked)
            item.setText(1, str(channel.get("priority", 0)))
            item.setText(2, alias)
            item.setText(3, channel.get("type", ""))
            item.setText(4, channel.get("name", ""))

    def enableDisable(self):
        iter = 0
        while iter < self._treeview.topLevelItemCount():
            item = self._treeview.topLevelItem(iter)
            disabled = strToBool(sysconf.get(("channels", str(item.text(2)), "disabled")))
            if item.checkState(0) == QtCore.Qt.Checked:
                if disabled:
                    sysconf.remove(("channels", str(item.text(1)), "disabled"))
                    self._changed = True
            else:
                if not disabled:
                    sysconf.set(("channels", str(item.text(1)), "disabled"), True)
                    self._changed = True
            iter += 1
            
    def show(self):
        self.fill()
        self._vbox.adjustSize()
        self._window.show()
        centerWindow(self._window)
        self._window.raise_()
        self._window.activateWindow()
        self._window.exec_()
        self._window.hide()
        self.enableDisable()
        return self._changed

    def newChannel(self):
        self.enableDisable()

        method = MethodSelector(self._window).show()
        if not method:
            return

        editor = ChannelEditor(self._window)

        path = None
        removable = []

        if method == "manual":

            type = TypeSelector(self._window).show()
            if not type:
                return

            newchannel = {"type": type}
            if editor.show(None, newchannel, editalias=True):
                alias = newchannel["alias"]
                del newchannel["alias"]
                sysconf.set(("channels", alias),
                            parseChannelData(newchannel))
                self._changed = True
                if newchannel.get("removable"):
                    removable.append(alias)

        elif method in ("descriptionpath", "descriptionurl"):

            if method == "descriptionpath":
                filename = QtWidgets.QFileDialog.getOpenFileName[0](self._window,
                    _("Select Channel Description"), "", "", "")
                if not filename:
                    return
                if not os.path.isfile(filename):
                    iface.error(_("File not found: %s") % filename)
                    return
                file = open(filename)
                data = file.read()
                file.close()
            elif method == "descriptionurl":
                url = iface.askInput(_("Description URL"))
                if not url:
                    return
                ctrl = iface.getControl()
                succ, fail = ctrl.downloadURLs([url], _("channel description"))
                if fail:
                    iface.error(_("Unable to fetch channel description: %s")
                                % fail[url])
                    return
                file = open(succ[url])
                data = file.read()
                file.close()
                if succ[url].startswith(sysconf.get("data-dir")):
                    os.unlink(succ[url])
            
            newchannels = parseChannelsDescription(data)
            for alias in newchannels:
                newchannel = newchannels[alias]
                if editor.show(alias, newchannel, editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias),
                                parseChannelData(newchannel))
                    self._changed = True
                    if newchannel.get("removable"):
                        removable.append(alias)

        elif method in ("detectmedia", "detectpath"):

            if method == "detectmedia":
                path = MountPointSelector().show()
                if not path:
                    return
            elif method == "detectpath":
                path = QtWidgets.QFileDialog.getExistingDirectory(self._window,
                     _("Select Path"), "", QtWidgets.QFileDialog.ShowDirsOnly)
                if not path:
                    return
                if not os.path.isdir(path):
                    iface.error(_("Directory not found: %s") % path)
                    return

            sysconf.set("default-localmedia", path, soft=True)

            foundchannel = False
            for newchannel in detectLocalChannels(path):
                foundchannel = True
                if editor.show(newchannel.get("alias"), newchannel,
                               editalias=True):
                    alias = newchannel["alias"]
                    del newchannel["alias"]
                    sysconf.set(("channels", alias),
                                parseChannelData(newchannel))
                    self._changed = True
                    if newchannel.get("removable"):
                        removable.append(alias)
            
            if not foundchannel:
                iface.error(_("No channels detected!"))
                return

        if removable:
            ctrl = iface.getControl()
            ctrl.rebuildSysConfChannels()
            channels = [x for x in ctrl.getChannels()
                        if x.getAlias() in removable]
            iface.updateChannels(channels=channels)

        if path:
            sysconf.remove("default-localmedia", soft=True)

        if self._changed:
            self.fill()

    def editChannel(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            alias = str(item.text(2))
        else:
            return
        self.enableDisable()
        channel = sysconf.get(("channels", alias), {})
        editor = ChannelEditor(self._window)
        if editor.show(alias, channel):
            sysconf.set(("channels", alias),
                        parseChannelData(channel))
            self._changed = True
            self.fill()

    def delChannel(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            alias = item.text(2)
        else:
            return
        if sysconf.remove(("channels", alias)):
            self._changed = True
            self.fill()

    def selectionChanged(self):
        item = self._treeview.selectedItems()
        if item:
            item = item[0]
            self._editchannel.setEnabled(True)
            self._delchannel.setEnabled(True)
        else:
            self._editchannel.setEnabled(False)
            self._delchannel.setEnabled(False)

    def doubleClicked(self, item):
        self.editChannel()

class QtChannelSelector(object):

    def __init__(self, parent=None):

        self._window = QtWidgets.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Select Channels"))
        self._window.setModal(True)

        self._window.setMinimumSize(600, 400)

        layout = QtWidgets.QVBoxLayout(self._window) 
        #layout.setResizeMode(QtGui.QLayout.FreeResize)
        
        #vbox = QtGui.QVBox(self._window)
        vbox = QtWidgets.QWidget(self._window)
        layout.addWidget(vbox)
        layout = QtWidgets.QVBoxLayout(vbox)
        layout.setContentsMargins(1, 0, 1, 0, 1, 0, 1, 0)
        layout.setSpacing(10)
        vbox.show()

        self._treeview = QtWidgets.QTableWidget(vbox)
        self._treeview.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        #self._treeview.setAllColumnsShowFocus(True)
        self._treeview.show()
        layout.addWidget(self._treeview)

        #self._treeview.addColumn("")
        #self._treeview.addColumn(_("Alias"))
        #self._treeview.addColumn(_("Type"))
        #self._treeview.addColumn(_("Name"))
        self._treeview.setHorizontalHeaderLabels(["", _("Alias"), _("Type"), _("Name")])

        ## temporary
        self.imagesTable = QtWidgets.QTableWidget()
        self.imagesTable.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        #self.imagesTable.setItemDelegate(ImageDelegate(self))

        self.imagesTable.horizontalHeader().setDefaultSectionSize(90)
        self.imagesTable.setColumnCount(3)
        self.imagesTable.setHorizontalHeaderLabels(("Image", "Mode", "State"))
        self.imagesTable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.imagesTable.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.imagesTable.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.imagesTable.verticalHeader().hide()


        bbox = QtWidgets.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtWidgets.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtWidgets.QPushButton(_("Cancel"), bbox)
        button.clicked[()].connect(self._window.reject)
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("OK"), bbox)
        button.clicked[()].connect(self._window.accept)
        layout.addWidget(button)

        button.setDefault(True)

    def fill(self):
        self._treeview.clear()
        channels = sysconf.get("channels", {})
        aliases = channels.keys()
        aliases.sort()

        for alias in aliases:
            channel = channels[alias]
            
            if not channel.get("disabled"):
                row = self._treeview.rowCount()
        	self._treeview.setRowCount(row +1)
                # OLD method in Qt3 item = QtGui.QCheckListItem(self._treeview, "", QtCore.QCheckListItem.CheckBox)
                item0 = QtWidgets.QTableWidgetItem()
                #item.setOn(False)
                self._treeview.setItem(row, 0, item0)
                #item0.setCheckState(QtCore.Qt.Unchecked)
                
                item1 = QtWidgets.QTableWidgetItem()
                item1.setText(str(alias))
                self._treeview.setItem(row, 1, item1)
                
                item2 = QtWidgets.QTableWidgetItem()
                item2.setText(channel.get("type", ""))
                self._treeview.setItem(row, 2, item2)
                
                item3 = QtWidgets.QTableWidgetItem()
                item3.setText(channel.get("name", ""))
                self._treeview.setItem(row, 3, item3)
        	print "Enabled: ", channel

        
        print "vector DEF FILL"



    def show(self):
        self.fill()
        self._result = False
        self._treeview.adjustSize()
        self._window.show()
        centerWindow(self._window)
        #self._window.activateWindow()
        self._window.raise_()
        self._result = self._window.exec_()
        self._window.hide()

        result = []
        if self._result == QtWidgets.QDialog.Accepted:
            iter = 0
            while iter < self._treeview.rowCount():
                item = self._treeview.itemAt(iter, 0)
                print "ITEM:",item
                if item.checkState() == QtCore.Qt.Checked:
            	    result.append(item.text(1)) 
                iter += 1

        return result

class ChannelEditor(object):

    def __init__(self, parent=None):

        self._fields = {}
        self._fieldn = 0

        self._window = QtWidgets.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("Edit Channel"))
        self._window.setModal(True)

        layout = QtWidgets.QVBoxLayout(self._window)
        #layout.setResizeMode(QtGui.QLayout.FreeResize)

        vbox = QtWidgets.QWidget(self._window)
        layout.addWidget(vbox)
        layout = QtWidgets.QVBoxLayout(vbox) 
        layout.setContentsMargins(1, 0, 1, 0, 1, 0, 1, 0)
        layout.setSpacing(10)
        vbox.show()

        #layout.addWidget(vbox)
        self._vbox = vbox

        #self._table = QtGui.QGrid(2, vbox)
        self._table = QtWidgets.QWidget(vbox)
        QtWidgets.QGridLayout(self._table)
        self._table.layout().setSpacing(10)
        self._table.show()
        layout.addWidget(self._table)

        sep = QtWidgets.QFrame(vbox)
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        sep.show()
        layout.addWidget(sep)

        #bbox = QtGui.QHBox(vbox)
        bbox = QtWidgets.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtWidgets.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtWidgets.QPushButton(_("Cancel"), bbox)
        button.clicked[()].connect(self._window.reject)
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("OK"), bbox)
        button.clicked[()].connect(self._window.accept)
        layout.addWidget(button)

        button.setDefault(True)

    def addField(self, key, label, value, ftype,
                 editable=True, tip=None, needed=False):

        row = self._table.layout().rowCount()
        if ftype is bool:
            spacer = QtWidgets.QWidget(self._table)
            spacer.show()
            self._table.layout().addWidget(spacer, row, 0)
            widget = QtWidgets.QCheckBox(label, self._table)
            widget.setChecked(value)
        else:
            _label = QtWidgets.QLabel("%s:" % label, self._table)
            _label.show()
            if tip:
                _label.setToolTip(tip)
            self._table.layout().addWidget(_label, row, 0)
            if ftype is int:
                widget = QtWidgets.QSpinBox(self._table)
                widget.setSingleStep(1)
                widget.setRange(-100000,+100000)
                widget.setValue(value)
            elif ftype is str:
                widget = QtWidgets.QLineEdit(self._table)
                widget.setText(value)
                if key in ("alias", "type"):
                    #widget.setMaxLength(20)
                    pass # "usually enough for about 15 to 20 characters"
                else:
                    widget.resize(QtCore.QSize(widget.sizeHint().width()*2,
                                               widget.sizeHint().height()))
            else:
                raise Error, _("Don't know how to handle %s fields") % ftype

        widget.show()
        self._table.layout().addWidget(widget, row, 1)

        widget.setEnabled(bool(editable))
        if tip:
            widget.setToolTip(tip)

        self._fields[key] = widget
        self._fieldn += 1

    def show(self, alias, oldchannel, editalias=False):
        # reset the dialog fields
        for item in self._table.children():
            if isinstance(item, QtWidgets.QWidget): 
                self._table.removeChild(item)
                del item
        
        self._fieldn = 0

        if len(oldchannel) > 1:
            # This won't be needed once old format channels
            # are converted.
            channel = parseChannelData(oldchannel)
        else:
            channel = oldchannel.copy()

        info = getChannelInfo(channel.get("type"))

        for key, label, ftype, default, descr in info.fields:
            if key == "type" or (key == "alias" and not editalias):
                editable = False
            else:
                editable = True
            if key == "alias":
                value = alias
            else:
                value = channel.get(key, default)
            if value is None:
                value = ftype()
            tip = "\n".join(textwrap.wrap(text=descr, width=40))
            self.addField(key, label, value, ftype, editable, tip)

        self._vbox.adjustSize()
        self._window.adjustSize()

        self._window.show()
        self._window.raise_()

        while True:
            self._result = self._window.exec_()
            if self._result == QtWidgets.QDialog.Accepted:
                newchannel = {}
                for key, label, ftype, default, descr in info.fields:
                    widget = self._fields[key]
                    if ftype == str:
                        newchannel[key] = str(widget.text()).strip()
                    elif ftype == int:
                        newchannel[key] = int(str(widget.text()))
                    elif ftype == bool:
                        newchannel[key] = widget.isChecked()
                    else:
                        raise Error, _("Don't know how to handle %s fields") %\
                                     ftype
                try:
                    if editalias:
                        value = newchannel["alias"]
                        if not value:
                            raise Error, _("Invalid alias!")
                        if (value != alias and 
                            sysconf.has(("channels", value))):
                            raise Error, _("Alias already in use!")
                        if not alias:
                            alias = value
                    createChannel(alias, newchannel)
                except Error, e:
                    self._result == QtWidgets.QDialog.Rejected
                    iface.error(unicode(e))
                    continue
                else:
                    oldchannel.clear()
                    oldchannel.update(newchannel)
            break

        self._window.hide()

        return self._result

class TypeSelector(object):

    def __init__(self, parent=None):

        self._window = QtWidgets.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Channel"))
        self._window.setModal(True)

        layout = QtWidgets.QVBoxLayout(self._window) 
        
        #vbox = QtGui.QVBox(self._window)
        vbox = QtWidgets.QWidget(self._window)
        layout.addWidget(vbox)
        layout = QtWidgets.QVBoxLayout(vbox) 
        layout.setContentsMargins(1, 0, 1, 0, 1, 0, 1, 0)
        layout.setSpacing(10)
        vbox.show()
        self._vbox = vbox

        #table = QtGui.QGrid(2, vbox)
        table = QtWidgets.QWidget(vbox)
        layout.addWidget(table)
        QtWidgets.QGridLayout(table)
        table.layout().setSpacing(10)
        table.show()
        self._table = table
        
        label = QtWidgets.QLabel(_("Type:"), table)
        table.layout().addWidget(label)

        self._typevbox = QtWidgets.QGroupBox(table)
        QtWidgets.QVBoxLayout(self._typevbox)
        #self._typevbox.setFrameStyle(QtGui.QFrame.NoFrame)
        self._typevbox.show()
        table.layout().addWidget(self._typevbox)

        sep = QtWidgets.QFrame(vbox)
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        sep.show()
        layout.addWidget(sep)

        #bbox = QtGui.QHBox(vbox)
        bbox = QtWidgets.QWidget(vbox)
        layout.addWidget(bbox)
        layout = QtWidgets.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtWidgets.QPushButton(_("Cancel"), bbox)
        button.clicked[()].connect(self._window.reject)
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("OK"), bbox)
        button.clicked[()].connect(self._window.accept)
        layout.addWidget(button)

        self._ok = button
        self._ok.setEnabled(False)

    def show(self):
        for item in self._typevbox.children():
            if isinstance(item, QtWidgets.QWidget): 
                self._typevbox.removeChild(item)
                del item
        self._type = None

        infos = [(info.name, type) for type, info in
                 getAllChannelInfos().items()]
        infos.sort()
        for name, type in infos:
            if not self._type:
                self._type = type
            radio = QtWidgets.QRadioButton(name, self._typevbox)
            radio.setObjectName(type)
            self._typevbox.layout().addWidget(radio)
            radio.clicked[()].connect(self.ok)
            act = RadioAction(radio, type, name)
            act.connect(self, "_type", type)
            radio.show()

        self._typevbox.adjustSize()
        self._table.adjustSize()
        self._vbox.adjustSize()
        self._window.adjustSize()

        self._window.show()
        self._window.raise_()

        type = None
        while True:
            self._result = self._window.exec_()
            if self._result == QtWidgets.QDialog.Accepted:
                type = self._type
                break
            type = None
            break

        self._window.hide()

        return type

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

class MethodSelector(object):

    def __init__(self, parent=None):

        self._window = QtWidgets.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Channel"))
        self._window.setModal(True)

        vbox = QtWidgets.QWidget(self._window)
        layout = QtWidgets.QVBoxLayout(vbox) 
        vbox.layout().setMargin(10)
        vbox.layout().setSpacing(10)
        vbox.show()

        table = QtWidgets.QWidget(vbox)
        QtWidgets.QGridLayout(table) 
        table.layout().setSpacing(10)
        table.show()
        layout.addWidget(table)
        
        label = QtWidgets.QLabel(_("Method:"), table)
        table.layout().addWidget(label)
 
        methodvbox = QtWidgets.QGroupBox(table)
        QtWidgets.QVBoxLayout(methodvbox) 
        methodvbox.show()
        table.layout().addWidget(methodvbox)
 
        sep = QtWidgets.QFrame(vbox)
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        sep.show()
        vbox.layout().addWidget(sep)

        bbox = QtWidgets.QWidget(vbox)
        layout = QtWidgets.QHBoxLayout(bbox)
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()
        vbox.layout().addWidget(bbox)

        button = QtWidgets.QPushButton(_("Cancel"), bbox)
        button.clicked[()].connect(self._window.reject)
        layout.addWidget(button)

        button = QtWidgets.QPushButton(_("OK"), bbox)
        button.clicked[()].connect(self._window.accept)
        layout.addWidget(button)

        self._ok = button
        self._ok.setEnabled(False)
        
        self._method = None
        #group = QtGui.QButtonGroup(methodvbox)
        for method, descr in [("manual",
                               _("Provide channel information")),
                              ("descriptionpath",
                               _("Read channel description from local path")),
                              ("descriptionurl",
                               _("Read channel description from URL")),
                              ("detectmedia",
                               _("Detect channel in media (CDROM, DVD, etc)")),
                              ("detectpath",
                               _("Detect channel in local path"))]:
            if not self._method:
                self._method = method
            radio = QtWidgets.QRadioButton(method, methodvbox)
            radio.setText(descr)
            methodvbox.layout().addWidget(radio)
            #group.addButton(radio)
            radio.clicked[()].connect(self.ok)
            act = RadioAction(radio, method, descr)
            act.connect(self, "_method", method)
            radio.show()
        
        methodvbox.adjustSize()
        vbox.adjustSize()
        self._window.adjustSize()

    def show(self):

        self._window.show()
        self._window.raise_()

        method = None
        while True:
            self._result = self._window.exec_()
            if self._result == QtWidgets.QDialog.Accepted:
                method = self._method
                break
            method = None
            break

        self._window.hide()

        return method

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))

class MountPointSelector(object):

    def __init__(self, parent=None):

        self._window = QtWidgets.QDialog(parent)
        self._window.setWindowIcon(QtGui.QIcon(getPixmap("smart")))
        self._window.setWindowTitle(_("New Channel"))
        self._window.setModal(True)

        vbox = QtGui.QVBox(self._window)
        vbox.setMargin(10)
        vbox.setSpacing(10)
        vbox.show()

        table = QtWidgets.QWidget(vbox)
        QtWidgets.QGridLayout(table) 
        table.layout().setSpacing(10)
        table.show()
        
        label = QtWidgets.QLabel(_("Media path:"), table)

        self._mpvbox = QtWidgets.QWidget(table)
        QtWidgets.QVBoxLayout(self._mpvbox) 
        self._mpvbox.layout().setSpacing(10)
        self._mpvbox.show()

        sep = QtWidgets.QFrame(vbox)
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        sep.show()

        bbox = QtWidgets.QWidget(vbox)
        QtWidgets.QHBoxLayout(bbox) 
        bbox.layout().setSpacing(10)
        bbox.layout().addStretch(1)
        bbox.show()

        button = QtWidgets.QPushButton(_("OK"), bbox)
        button.clicked[()].connect(self._window.accept)
        bbox.layout().addWidget(button)

        button = QtWidgets.QPushButton(_("Cancel"), bbox)
        button.clicked[()].connect(self._window.reject)
        bbox.layout().addWidget(button)

    def show(self):
        for item in self._mpvbox.children():
            if isinstance(item, QtWidgets.QWidget): 
                self._mpvbox.removeChild(item)
                del item
        self._mp = None

        group = QtWidgets.QButtonGroup(None, "mp")
        n = 0
        for media in iface.getControl().getMediaSet():
            mp = media.getMountPoint()
            if not self._mp:
                self._mp = mp
            radio.clicked[()].connect(self.ok)
            radio = QtWidgets.QRadioButton(mp, self._mpvbox)
            group.insert(radio)
            act = RadioAction(radio, mp)
            act.connect(self, "_mp", mp)
            radio.show()
            n += 1

        if n == 0:
            iface.error(_("No local media found!"))
            return None
        elif n == 1:
            return self._mp

        self._window.show()
        self._window.raise_()

        mp = None
        while True:
            self._result = self._window.exec_()
            if self._result == QtWidgets.QDialog.Accepted:
                mp = self._mp
                break
            mp = None
            break

        self._window.hide()

        return mp

    def ok(self):
        self._ok.setEnabled(True)
        self._ok.setDefault((True))



#!/usr/bin/env python
# -*- coding: iso-8859-2 -*-

import string
import copy
import os
import gzip
import gtk
import commands

try:
    from backports import lzma
except ImportError:
    from lzma import LZMAFile as lzma

import singletons
from common import *
import common; _ = common._
from Source import *
from Package import *
from Category import *

def czfind(istr):
    l = len(istr)
    i = 0
    word = ''
    flag = False
    while i < l:
      if istr[i] == '\n':
        if flag:
          flag = False
        else:
          break
        word = ''
      elif istr[i] == ' ':
        flag = True
      else:
        word += istr[i]
      i += 1
    return word

class PackagePool:
    """This class retrieves and structures every packages that are accessible
        from the system."""
        
    HASHED_LEN = 2  # used by GetUpgradeableState
        
    def __init__(self):
        self.initialized = False
    
    def Init(self):
        """Reinitialize the inner state of the package pool.  Must be called
            in case of manipulating the package registry."""
        self.initialized = False
        self.all_packages = []
        self.package_name_pool = {}
        self.installed_package_names = {}
        singletons.application.DisplayProgress(_('Reading package sources'))
        self.RegisterUpgradablePackages()
        self.all_sources = self.GetSources()
        singletons.application.DisplayProgress(_('Querying installed packages'))
        self.RegisterInstalledPackages()
        self.RegisterInstallablePackages()
        self.initialized = True
    
    def GetSources(self):
        """Retrieve and return the Source objects containted in urpmi.cfg."""
        
        def get_source_name(line):
            """Extract the source name from the line of the file."""
            prev_chr = line[0]
            name = line[0]
            for c in line[1:-1]:
                if c == ' ':
                    if prev_chr == '\\':
                        name += ' '
                    else:
                        break
                elif c != '\\':
                    name += c
                prev_chr = c
            return name
        
        file = open('/etc/urpmi/urpmi.cfg')
        sources = []
        word = ''
        flag0 = False
        flag1 = False
        name_flag = False
        while 1:
          c = file.read(1)
          if c == '':
              break
          elif c == '{':
              if flag0 == False:
                 flag0 = True
              else:
                 name_flag = False
                 name = get_source_name(word)
                 source = Source(name)
                 source.hdlist = czfind(commands.getoutput('find /var/lib/urpmi/ | grep cz | grep ' + name))
                 print 'HL:', source.hdlist
                 if source.hdlist != '':
                     sources.append(source)
                 word = ''
          elif c == '}':
              if flag1 == False:
                 flag1 = True
                 name_flag = True
              else:
                 name_flag = True
          elif name_flag == True and c not in ['\\', '\n']:
              word += c
        return sources
    
    def GetActiveSources(self, new=False):
        """Return the active Source objects."""
        if new:
            all_sources = self.GetSources()
        else:
            all_sources = self.all_sources
        return [source for source in all_sources if not source.ignore]

    def RegisterInstalledPackages(self):
        """Retrieve a dictionary containing every installed packages on the system."""
        file = os.popen('rpmquery --all "--queryformat=%{name}-%{version}-%{release}.%{arch}:%{size}:%{group}:%{installtime}\n"')
        for line in file:
            fields = line.strip().split(':')
            name = fields[0]
            size = int(fields[1])
            category = fields[2]
            btime = int(fields[3])
            self.AddPackage(name, size, category, time=btime)

    def RegisterInstallablePackages(self):
        """Get the list of every packages that are installable on the system."""
        for source in self.GetActiveSources():
            #disable gzip file = gzip.open(source.hdlist)
#            print "DEBUG " + lzma.open(source.hdlist).read()
            file = lzma(source.hdlist)
            for line in file:
                if line[:6] != '@info@':
                    continue
                fields = line.strip()[7:].split('@')
                longname = fields[0]
                size = int(fields[2])
                category = fields[3]
                self.AddPackage(longname, size, category, source)

    def RegisterUpgradablePackages(self):
        upl  = commands.getoutput('urpmq --auto-select --whatrequires').split()
        l = len (upl)
        i = 0
        self.upgradable_packages = []
        self.upgradable_packages_long = []
        while i < l:
          self.upgradable_packages.append(self.generate_shortname(upl[i])) 
          self.upgradable_packages_long.append(upl[i])
          i += 1

    def generate_shortname(self, longname):
        """Generate shortname from a longname. This is a workaround if association failed."""
        print("LONGN:", longname)
        pos1 = longname.rfind("-")
        if pos1 > 0:
            pos2 = longname[:pos1].rfind("-")
            return longname[:pos2]
        else:
            return ""
    
    def RegisterCategory(self, category_str, package):
        """Register category 'category' in the category tree."""
        category_path = category_str.split('/')
        current_category = self.category_tree
        for subcategory_name in category_path:
            current_category = current_category.GetSubCategory(subcategory_name)
        current_category.AddPackage(package)

    def AddPackage(self, longname, size, category, source=None, time=-1):
        """Add package to the registry."""
        if self.package_name_pool.has_key(longname):
            self.package_name_pool[longname].AddSource(source)
            return        
        package = Package()
        package.longname = longname
        package.shortname = self.generate_shortname(longname) ### Ezt raktam be !!!
        package.size = size
        package.category = category
        if source:
            package.AddSource(source)
            package.is_installed = False
        else:
            package.is_installed = True
        package.time = time
        if len(package.longname) >= 3:
            if package.longname.lower().find('lib') != -1:
                package.is_library = True
            else:
                package.is_library = False
        else:
            package.is_library = False
        if package.shortname in self.upgradable_packages and package.is_installed:
          package.is_upgradable = True
        else:
          package.is_upgradable = False
        self.package_name_pool[longname] = package
        self.all_packages.append(package)

    def GetPackagesContainingDescription(self, text):
        """Get the list of every packages that are installable on the system."""
        active_sources = self.GetActiveSources()  #[source for source in self.all_sources if not source.ignore]   
        containing_longnames = {}
        for source in active_sources:
            file = lzma.open(source.hdlist)
            for line in file:
                if line[:9] == '@summary@':
                    fields = line.strip().split('@')
                    description = fields[2]
                elif line[:6] == '@info@':
                    fields = line.strip().split('@')
                    longname = fields[2]
                    if description.lower().find(text) != -1:
                        containing_longnames[longname] = True
        return containing_longnames

    FILTER_PACKAGENAME = 0
    FILTER_DESCRIPTION = 1
    FILTER_FILENAME = 2
    
    def GetPackagesContainingFiles(self, search_text):
        pass
#        active_sources = self.GetActiveSources()
#        active_source_paths = ''
#        containing_longnames = {}
#        for source in active_sources:
#            active_source_paths += escape(source.hdlist) + ' '
#        command = 'parsehdlist --fileswinfo ' + active_source_paths + ' | grep ".*:files:.*'+escape(search_text)+'.*"'
#        file = os.popen(command)
#        for line in file:
#            containing_longnames[ line.split(':')[0] ] = True
#        return containing_longnames
    
    def Filter(self, application, library, installed, noninstalled, search_mode, search_text):
        """Filter packages."""
        # reset pacage registry
        self.packages = []
        self.category_tree = Category('root')
        search_text = search_text.lower()
        if search_mode == self.FILTER_DESCRIPTION:
            containing_longnames = self.GetPackagesContainingDescription(search_text)
        elif search_mode == self.FILTER_FILENAME:
            containing_longnames = self.GetPackagesContainingFiles(search_text)
        for source in self.all_sources:
            source.packages = []
        for package in self.all_packages:
            inst = (package.is_installed and installed) or (not package.is_installed and noninstalled)
            ptype = (package.is_library and library) or (not package.is_library and application)
            if search_mode == self.FILTER_PACKAGENAME:
                search_inc = package.longname.lower().find(search_text)!=-1
            elif search_mode == self.FILTER_DESCRIPTION:
                search_inc = containing_longnames.has_key(package.longname)
            elif search_mode == self.FILTER_FILENAME:
                search_inc = containing_longnames.has_key(package.shortname)
            else:
                search_inc = True
            included = inst and ptype and search_inc
            if included:
                for source in package.sources:
                    source.AddPackage(package)
                self.RegisterCategory(package.category, package)
                self.packages.append(package)

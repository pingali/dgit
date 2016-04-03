#!/usr/bin/env python

import os, sys, pkg_resources
import json
from collections import namedtuple
from functools import partial
import html5lib
from ..vendor.pluginbase.pluginbase import PluginBase

Key = namedtuple("Key", ["name","version"])

__all__ = ['plugins_get_mgr', 'plugins_load',
           'plugins_show', 'plugins_close']

class PluginManager(object):
    """
    Manage the various plugins in the project
    """

    def __init__(self, paths=[]):

        self.order = ['backend', 'repomanager', 'metadata',
                      'validator', 'transformer',
                      'instrumentation']
        self.plugins = {
            'backend': {},
            'instrumentation': {},
            'repomanager': {},
            'metadata': {},
            'validator': {},
            'transformer': {},
        }
        self.sources = {}



        thisdir = os.path.abspath(os.path.dirname(__file__))
        def get_path(p):
            return os.path.abspath(os.path.join(thisdir,
                                                "../contrib",
                                                p))

        allplugins = [
            {
                'package': 'backend',
                'base': get_path('backends'),
            },
            {
                'package': 'instrumentation',
                'base': get_path('instrumentations'),
            },
            {
                'package': 'repomanager',
                'base': get_path('repomanagers'),
            },
            {
                'package': 'metadata',
                'base': get_path('metadata'),
            },
            {
                'package': 'validator',
                'base': get_path('validators'),
            },
            {
                'package': 'transformer',
                'base': get_path('transformers'),
            },
        ]

        for p in allplugins:

            plugin_base = PluginBase(package=p['package'],
                                     searchpath=[p['base']])


            source = plugin_base.make_plugin_source(
                searchpath=[],
                identifier="Plugin Manager")
	
            for plugin_name in source.list_plugins():
                # print("Loading plugin", p['base'], plugin_name)
                plugin = source.load_plugin(plugin_name)
                plugin.setup(self)

            self.sources[p['package']] = source

        self.discover_all_plugins()

    def discover_all_plugins(self):
        """
        Load all plugins from dgit extension
        """
        for v in pkg_resources.iter_entry_points('dgit.plugins'):
            m = v.load()
            m.setup(self)

    def register(self, what, obj):
        """
        Registering a plugin

        Params
        ------
        what: Nature of the plugin (backend, instrumentation, repo)
        obj: Instance of the plugin
        """
        # print("Registering pattern", name, pattern)
        name = obj.name
        version = obj.version
        enable = obj.enable
        if enable == 'n':
            return

        key = Key(name, version)
        self.plugins[what][key] = obj

    def search(self, what, name=None, version=None):
        """
        Search for a plugin
        """
        filtered = {}

        # The search may for a scan (what is None) or
        if what is None:
            whats = list(self.plugins.keys())
        elif what is not None:
            if what not in self.plugins:
                raise Exception("Unknown class of plugins")
            whats = [what]
        for what in whats:
            if what not in filtered:
                filtered[what] = []
            for key in self.plugins[what].keys():
                (k_name, k_version) = key
                if name is not None and k_name != name:
                    continue
                if version is not None and k_version != version:
                    continue
                if self.plugins[what][key].enable == 'n':
                    continue
                filtered[what].append(key)

        # print(filtered)
        return filtered

    def gather_configs(self):
        """
        Gather configuration requirements of all plugins
        """
        configs = []
        for what in self.order:
            for key in self.plugins[what]:
                mgr = self.plugins[what][key]
                c = mgr.config(what='get')
                if c is not None:
                    c.update({
                        'description': mgr.description
                    })
                    print("Gathering configuration from ", c)
                    configs.append(c)
        return configs

    def update_configs(self, config):
        """
        Gather configuration requirements of all plugins
        """
        for what in self.plugins:  # backend, repo etc.
            for key in self.plugins[what]: # s3, filesystem etc.
                # print("Updating configuration of", what, key)
                self.plugins[what][key].config(what='set', params=config)
        return

    def show(self, what, name, version, details):

        filtered = self.search(what, name, version)
        if len(filtered) > 0:
            for what in self.order:
                print("========")
                print(what)
                print("========")
                if len(filtered[what]) == 0:
                    print("None\n")
                    continue
                for k in filtered[what]:
                    obj = self.plugins[what][k]
                    print("%s (%s) :" % k,
                          obj.description)
                    if details:
                        print("   Supp:", obj.support)
                print("")
        else:
            print("No backends found")

    def get_by_key(self, what, key):
        return self.plugins[what][key]

    def get_by_repo(self, username, dataset):

        keys = list(self.plugins['repomanager'].keys())
        for k in keys:
            try:
                repomanager = self.plugins['repomanager'][k]
                repokey = repomanager.find(username, dataset)
                break
            except:
                repomanager = None
                repokey = None
        return (repomanager, repokey)

    def get(self, what, name):
        filtered = self.search(what, name)
        filtered = filtered[what]
        if len(filtered) > 0:
            return self.plugins[what][filtered[0]]
        else:
            return None

    def shutdown(self):
        for what in self.sources:
            self.sources[what].cleanup()

pluginmgr = None

def plugins_load():
    """
    Load plugins from various sources:

    - dgit/plugins
    - dgit_extensions package

    """
    global pluginmgr

    # Auto clone if they have not been already shutdown
    if pluginmgr is not None:
        plugins_close()

    pluginmgr = PluginManager([])
    # pluginmgr.show()

def plugins_close():
    global pluginmgr
    pluginmgr.shutdown()
    pluginmgr = None

def plugins_show(what=None, name=None, version=None, details=False):
    """
    Show details of available plugins

    Parameters
    ----------
    what: Class of plugins e.g., backend
    name: Name of the plugin e.g., s3
    version: Version of the plugin
    details: Show details be shown?

    """
    global pluginmgr
    return pluginmgr.show(what, name, version, details)

def plugins_get_mgr():
    """
    Get the global plugin manager
    """
    global pluginmgr
    return pluginmgr

def  plugins_get_config():

    global pluginmgr
    return pluginmgr.config()

if __name__ == '__main__':
    plugins_load()
    plugins_show()
    plugins_close()

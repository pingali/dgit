#!/usr/bin/env python 

import os, sys
import json
from collections import namedtuple

Key = namedtuple("Key", ["name","version"])

class RepoManagerHelper: 
    """
    Miscellaneous helper functions useful for evaluation
    """
    pass 

class RepoManagerBase(object):
    """Various repository backends including simple local filesystem,
    git, and in future instabase.

    """
    def __init__(self, name, version, description, supported=[]):
        self.name = name
        self.version = version        
        self.description = description  
        self.support = supported + [name]
        self.enabled = 'y'
        self.initialize() 
        self.repos = {} 

    def initialize(self):
        pass 

    def enabled(self): 
        return self.enabled.lower() != 'n'

    def get_repos(self): 
        return list(self.repos.keys())

    def is_my_repo(self, username, reponame): 

        rootdir = os.path.join(self.workspace, 'datasets')  
        metadatadir = os.path.join(rootdir, username, 
                                   reponame, 
                                   self.metadatadir)
        if os.path.exists(metadatadir): 
            return True 
        else: 
            return False 

    def init(self, username, reponame, force): 
        """
        Initialize a repo (may be fs/git/.. backed)
        """
        pass

    def key(self, username, reponame):
        return (username, reponame) 

    def find(self, username=None, reponame=None):
        """
        Find the key corresponding to this repo if exists 
        """
        key = (username, reponame) 
        if key not in self.repos: 
            raise Exception("Unknown repository") 
        return key 

    def lookup(self, username=None, reponame=None, 
               key=None): 
        """
        Lookup all available repos 
        """
        if key is None: 
            key = self.find(username, reponame) 
        if key not in self.repos: 
            raise Exception("Unknown repository") 

        return self.repos[key]

    def users(self):         
        """
        Find users 
        """
        return os.listdir(os.path.join(self.workspace, 'datasets'))

    def repos(self, username):         
        return os.listdir(os.path.join(self.workspace, 'datasets', username))

    def server_rootdir(self,  username, reponame, create=True): 
        """
        Working directory for the repo 
        """
        path = os.path.join(self.workspace,
                            'git', 
                            username, 
                            reponame + ".git") 
        if create: 
            try: 
                os.makedirs(path)
            except:
                pass 

        return path 

    def rootdir(self,  username, reponame, create=True): 
        """
        Working directory for the repo 
        """
        path = os.path.join(self.workspace,
                            'datasets', 
                            username, 
                            reponame) 
        if create: 
            try: 
                os.makedirs(path)
            except:
                pass 

        return path 

        

    def add(self, username, reponame, repo): 
        """
        Add repo to the internal lookup table...
        """
        key = self.key(username, reponame) 
        self.repos[key] = repo 
        return key 

    def push(self, key): 
        pass 

    def status(self, key): 
        pass 

    def stash(self, key): 
        pass 
        
    def commit(self, key, message): 
        pass 

    def add_raw(self, key, files): 
        pass 

    def add_files(self, key, files): 
        """
        Files is a list with simple structure 
        {
           'relativepath': <path-in-repo>,
           'fullpath': <actual path> 
        }
        """
        pass 

    def clone(self, key, newusername, newreponame):
        """
        Clone repo 
        """

    def config(self, what='get', params=None): 
        return 

#!/usr/bin/env python 

import os, sys
import json
from collections import namedtuple

Key = namedtuple("Key", ["name","version"])

class Repo: 
    """
    Class to track each repo 
    """
    def __init__(self, username, reponame):
        self.username = username
        self.reponame = reponame 
        self.package = None
        self.manager = None 
        self.rootdir = None
        self.options = {} 
        self.key = None 
        self.remoteurl = None

    def find_matching_files(self, includes): 
        """
        For various actions we need files that match patterns 
        """
        
        files = [f['relativepath'] for f in self.package['resources']]
        includes = r'|'.join([fnmatch.translate(x) for x in includes])
        files = [f for f in files if re.match(includes, os.path.basename(f))]
        return files 
    
    def find_include_files(self, pattern_name): 
        
        if 'metadata-management' not in self.options:
            return [] 

        if pattern_name not in ['include-preview',
                                'include-schema',
                                'include-tab-diffs',
                                
                            ]: 
            return []

        metadata = self.options['metadata-management']
        patterns = metadata.get(pattern_name,[])
        return self.find_include_files(patterns) 
        
    def __str__(self): 
        return "[{}] {}/{}".format(self.manager.name,
                                   self.username,
                                   self.reponame)
    def run(self, cmd, *args): 
        """
        Run a specific command using the manager 
        """
        if self.manager is None: 
            raise Exception("Fatal internal error: Missing repository manager")
        if cmd not in dir(self.manager):
            raise Exception("Fatal internal error: Invalid command {} being run".format(cmd))
        func = getattr(self.manager, cmd)
        repo = self 
        return func(repo, *args)

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

    def get_repo_list(self): 
        return list(self.repos.keys())

    def get_repo_details(self, key): 
        return self.repos[key]

    def search(self, username, reponame): 
        matches = []

        for k in list(self.repos.keys()): 
            if username is not None and k[0] != username: 
                continue
            if reponame is not None and k[1] != reponame: 
                continue
            matches.append(k)
        return matches 
            
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

    def lookup(self, username=None, reponame=None, key=None): 
        """
        Lookup all available repos 
        """
        if key is None: 
            key = self.key(username, reponame) 
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

    def server_rootdir_from_repo(self,  repo, create=True): 
        return self.server_rootdir(repo.username, 
                                   repo.reponame, 
                                   create)

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

        

    def add(self, repo): 
        """
        Add repo to the internal lookup table...
        """
        key = self.key(repo.username, repo.reponame) 
        repo.key = key 
        self.repos[key] = repo 
        return key 

    def drop(self, repo): 
        pass 

    def push(self, repo): 
        pass 

    def status(self, repo): 
        pass 

    def stash(self, repo): 
        pass 
        
    def commit(self, repo, message): 
        pass 

    def add_raw(self, repo, files): 
        pass 

    def add_files(self, repo, files): 
        """
        Files is a list with simple structure 
        {
           'relativepath': <path-in-repo>,
           'fullpath': <actual path> 
        }
        """
        pass 

    def clone(self, repo, newusername, newreponame):
        """
        Clone repo 
        """
        pass 

    def config(self, what='get', params=None): 
        return 

#!/usr/bin/env python

import os, sys
import json
import fnmatch, re
from collections import namedtuple
from ..helper import slugify
from ..exceptions import *

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

        # Match both the file name as well the path..
        files = [f for f in files if re.match(includes, os.path.basename(f))] + \
                [f for f in files if re.match(includes, f)]
        files = list(set(files))

        return files

    # Cache for partially computed information
    def cache_path(self, prefix, objname, ext=""):

        path = os.path.join('.dgit',
                            prefix,
                            slugify(objname))
        if ext != "":
            ext = slugify(ext) # clean this up as well
            path += ".{}".format(ext)

        return {
            'relative': path,
            'full': os.path.join(self.rootdir, path)
            }

    def cache_check(self, cachepath):
        return os.path.exists(cachepath['full'])

    def cache_read(self, cachepath):
        return open(cachepath['full']).read()

    def cache_write(self, cachepath, content):
        path = cachepath['full']
        try:
            os.makedirs(os.path.dirname(path))
        except:
            pass

        flag = "wb" if isinstance(content, bytes) else "w"
        with open(path, flag) as fd:
            fd.write(content)
            print("Updated", os.path.relpath(path, self.rootdir))

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


    def get_resource(self, p):
        """
        Get metadata for a given file
        """
        for r in self.package['resources']:
            if r['relativepath'] == p:
                r['localfullpath'] = os.path.join(self.rootdir, p)
                return r

        raise Exception("Invalid path")


class RepoManagerBase(object):
    """Repository manager handles the specifics of the version control
    system. Currently only git manager is supported.
    """
    def __init__(self, name, version, description, supported=[]):
        self.enable = 'y'
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
            raise UnknownRepository()

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
        """
        Drop repository
        """
        key = repo.key
        del self.repos[key]


    def push(self, repo, args):
        pass

    def status(self, repo, args):
        pass

    def show(self, repo, args):
        pass

    def stash(self, repo, args):
        pass

    def commit(self, repo, message):
        pass

    def notes(self, repo, args):
        pass

    def add_raw(self, repo, files):
        pass

    def add_files(self, repo, files):
        """
        Files is a list with simple dict structure with relativepath and fullpath
        """
        pass

    def clone(self, repo, newusername, newreponame):
        """
        Clone repo
        """
        pass

    def config(self, what='get', params=None):
        return

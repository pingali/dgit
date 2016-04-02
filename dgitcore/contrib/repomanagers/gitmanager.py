#!/usr/bin/env python
"""
GitManager provides the high level interface to git command line

GitManager does not have independent variables but it inherits attributes from 'Local' backend and 'User' definition

* workspace: (from Local) Directory used by gitmanager to store dataset repositories
* username: (from User) Name of the user
* email: (from User) Email of the user

"""
import os, sys, json, subprocess, re, json
import pipes, collections
import shutil
from sh import git
from dgitcore.plugins.repomanager import RepoManagerBase, Repo
from dgitcore.helper import cd
from dgitcore.exceptions import *

class GitRepoManager(RepoManagerBase):
    """
    Git-based versioning service. This implements the RepoManagerBase class.
    """

    def __init__(self):
        self.username = None

        self.workspace = None
        self.metadatadir = '.git'
        self.repos = {}
        self.enable = True
        super(GitRepoManager, self).__init__('git',
                                             'v0',
                                             "Git-based Repository Manager")

    # =>  Helper functions
    def _run(self, cmd):
        """
        Helper function to run commands

        Parameters
        ----------
        cmd : list
              Arguments to git command
        """

        # This is here in case the .gitconfig is not accessible for
        # some reason. 
        environ = os.environ.copy() 

        environ['GIT_COMMITTER_NAME'] = self.fullname
        environ['GIT_COMMITTER_EMAIL'] = self.email 
        environ['GIT_AUTHOR_NAME'] = self.fullname
        environ['GIT_AUTHOR_EMAIL'] = self.email 

        cmd = [pipes.quote(c) for c in cmd]
        cmd = " ".join(['/usr/bin/git'] + cmd)
        cmd += "; exit 0"
        #print("Running cmd", cmd)
        try:
            output = subprocess.check_output(cmd,
                                             stderr=subprocess.STDOUT,
                                             shell=True,
                                             env=environ)
        except subprocess.CalledProcessError as e:
            output = e.output

        output = output.decode('utf-8')
        output = output.strip()
        # print("Output of command", output)
        return output

    def _run_generic_command(self, repo, cmd):
        """
        Run a generic command within the repo. Assumes that you are
        in the repo's root directory
        """
        
        result = None
        with cd(repo.rootdir):
            # Dont use sh. It is not collecting the stdout of all
            # child processes.
            output = self._run(cmd)
            try:
                result = {
                    'cmd': cmd,
                    'status': 'success',
                    'message': output,
                }
            except Exception as e:
                result = {
                    'cmd': cmd,
                    'status': 'error',
                    'message': str(e)
                }

        return result

    # =>  Simple commands ...
    def notes(self, repo, args=[]):
        """
        Add notes to the commit

        Parameters
        ----------

        repo: Repository object
        args: notes-specific args

        """
        return self._run_generic_command(repo, ["notes"] + args)

    # =>  Simple commands ...
    def push(self, repo, args=[]):
        """
        Push to origin master

        Parameters
        ----------

        repo: Repository object
        args: git-specific args

        """
        return self._run_generic_command(repo, ["push"] + args)

    # =>  Simple commands ...
    def remote(self, repo, args=[]):
        """
        Check remote URL

        Parameters
        ----------

        repo: Repository object
        args: git-specific args

        """
        return self._run_generic_command(repo, ["remote"] + args)

    # =>  Simple commands ...
    def pull(self, repo, args=[]):
        """
        Pull from origin/filesystem based master

        Parameters
        ----------

        repo: Repository object
        args: git-specific args

        """
        return self._run_generic_command(repo, ["pull"] + args)

    def status(self, repo, args=[]):
        """
        Show status of the repo (pass thru git command)

        Parameters
        ----------

        repo: Repository object
        args: git-specific args
        """
        return self._run_generic_command(repo, ["status"] + args)

    def stash(self, repo, args=[]):
        """
        Stash all the changes (pass thru git command)

        Parameters
        ----------

        repo: Repository object
        args: git-specific args
        """
        return self._run_generic_command(repo, ["stash"] + args)

    def diff(self, repo, args=[]):
        """
        diff two repo versions  (pass thru git command)

        Parameters
        ----------

        repo: Repository object
        args: git-specific args
        """
        return self._run_generic_command(repo, ["diff"] + args)

    def log(self, repo, args=[]):
        """
        Show the log  (pass thru git command)

        Parameters
        ----------

        repo: Repository object
        args: git-specific args
        """
        return self._run_generic_command(repo, ["log"] + args)

    def commit(self, repo, args=[]):
        """
        Commit the changes to the repo (pass thru git command)

        Parameters
        ----------

        repo: Repository object
        args: git-specific args
        """
        
        return self._run_generic_command(repo, ["commit"] + args)

    def show(self, repo, args=[]):
        """
        Show the content of the repo (pass thru git command)

        Parameters
        ----------

        repo: Repository object
        args: git-specific args
        """
        return self._run_generic_command(repo, ["show"] + args)


    # => Run more complex functions to initialize, cleanup
    def init(self, username, reponame, force, backend=None):
        """
        Initialize a Git repo

        Parameters
        ----------

        username, reponame : Repo name is tuple (name, reponame)
        force: force initialization of the repo even if exists
        backend: backend that must be used for this (e.g. s3)
        """
        key = self.key(username, reponame)

        # In local filesystem-based server, add a repo
        server_repodir = self.server_rootdir(username,
                                             reponame,
                                             create=False)

        # Force cleanup if needed
        if os.path.exists(server_repodir) and not force:
            raise RepositoryExists()

        if os.path.exists(server_repodir):
            shutil.rmtree(server_repodir)
        os.makedirs(server_repodir)

        # Initialize the repo
        with cd(server_repodir):
            git.init(".", "--bare")

        if backend is not None:
            backend.init_repo(server_repodir)

        # Now clone the filesystem-based repo
        repodir = self.rootdir(username, reponame, create=False)

        # Prepare it if needed
        if os.path.exists(repodir) and not force:
            raise Exception("Local repo already exists")
        if os.path.exists(repodir):
            shutil.rmtree(repodir)
        os.makedirs(repodir)

        # Now clone...
        with cd(os.path.dirname(repodir)):
            git.clone(server_repodir, '--no-hardlinks')

        url = server_repodir
        if backend is not None:
            url = backend.url(username, reponame)

        repo = Repo(username, reponame)
        repo.manager = self
        repo.remoteurl = url
        repo.rootdir = self.rootdir(username, reponame)

        self.add(repo)
        return repo

    def clone(self, url, backend=None):
        """
        Clone a URL

        Parameters
        ----------

        url : URL of the repo. Supports s3://, git@, http://
        """


        # s3://bucket/git/username/repo.git
        username = self.username
        reponame = url.split("/")[-1] # with git
        reponame = reponame.replace(".git","")

        key = (username, reponame)

        # In local filesystem-based server, add a repo
        server_repodir = self.server_rootdir(username,
                                             reponame,
                                             create=False)

        rootdir = self.rootdir(username,  reponame, create=False)


        if backend is None:
            # Backend is standard git repo (https://, git@...)
            with cd(os.path.dirname(rootdir)):
                self._run(['clone', '--no-hardlinks', url])
        else:
            # Backend is s3
            # Sync if needed.
            if not os.path.exists(server_repodir):
                # s3 -> .dgit/git/pingali/hello.git -> .dgit/datasets/pingali/hello
                backend.clone_repo(url, server_repodir)

            # After sync clone,
            with cd(os.path.dirname(rootdir)):
                self._run(['clone', '--no-hardlinks', server_repodir])


        # Insert the notes push
        if True:
            configfile = os.path.join(rootdir, '.git', 'config')
            content = open(configfile).read()
            original = "fetch = +refs/heads/*:refs/remotes/origin/*"
            replacement ="""fetch = +refs/heads/*:refs/remotes/origin/*\n        fetch = +refs/notes/*:refs/notes/*"""
            if "notes" not in content:
                content = content.replace(original, replacement)
                with open(configfile, 'w') as fd:
                    fd.write(content)

            # Pull the notes if any as well..
            with cd(rootdir):
                self._run(['pull','origin'])

        # Insert the object into the internal table we maintain...
        r = Repo(username, reponame)
        r.rootdir = rootdir
        r.remoteurl = url
        r.manager = self

        package = os.path.join(r.rootdir, 'datapackage.json')
        packagedata = open(package).read()
        r.package = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(packagedata)

        return self.add(r)


    def delete(self, repo, args=[]):
        """
        Delete files from the repo
        """

        result = None
        with cd(repo.rootdir):
            try:
                cmd = ['rm'] + list(args)
                result = {
                    'status': 'success',
                    'message': self._run(cmd)
                }
            except Exception as e:
                result = {
                    'status': 'error',
                    'message': str(e)
                }

            # print(result)
            return result

    def drop(self, repo, args=[]):
        """
        Cleanup the repo
        """

        # Clean up the rootdir
        rootdir = repo.rootdir
        print("Cleaning repo directory: {}".format(rootdir))
        if os.path.exists(rootdir):
            shutil.rmtree(rootdir)

        # Cleanup the local version of the repo (this could be on
        # the server etc.
        server_repodir = self.server_rootdir_from_repo(repo,
                                                       create=False)
        if os.path.exists(server_repodir):
            print("Cleaning data from local git 'server': {}".format(server_repodir))
            shutil.rmtree(server_repodir)

        super(GitRepoManager, self).drop(repo)

        return {
            'status': 'success',
            'message': "successful cleanup"
        }

    def permalink(self, repo, path):
        """
        Get the permalink to command that generated the dataset
        """

        if not os.path.exists(path):
            return None

        # Get this directory
        cwd = os.getcwd()

        # Find the root of the repo and cd into that directory..
        os.chdir(os.path.dirname(path))
        rootdir = self._run(["rev-parse", "--show-toplevel"])
        if "fatal" in rootdir:
            return None

        os.chdir(rootdir)
        # print("Rootdir = ", rootdir)

        # Now find relative path
        relpath = os.path.relpath(path, rootdir)
        # print("relpath = ", relpath)

        # Get the last commit for this file
        #3764cc2600b221ac7d7497de3d0dbcb4cffa2914
        sha1 = self._run(["log", "-n", "1", "--format=format:%H", relpath])
        #print("sha1 = ", sha1)

        # Get the repo URL
        #git@gitlab.com:pingali/simple-regression.git
        #https://gitlab.com/kanban_demo/test_project.git
        remoteurl = self._run(["config", "--get", "remote.origin.url"])
        #print("remoteurl = ", remoteurl)

        # Go back to the original directory...
        os.chdir(cwd)

        # Now match it against two possible formats of the remote url
        # Examples
        #https://help.github.com/articles/getting-permanent-links-to-files/
        #https://github.com/github/hubot/blob/ed25584f5ac2520a6c28547ffd0961c7abd7ea49/README.md
        #https://gitlab.com/pingali/simple-regression/blob/3764cc2600b221ac7d7497de3d0dbcb4cffa2914/model.py
        #https://github.com/pingali/dgit/blob/ff91b5d04b2978cad0bf9b006d1b0a16d18a778e/README.rst
        #https://gitlab.com/kanban_demo/test_project/blob/b004677c23b3a31eb7b5588a5194857b2c8b2b95/README.md

        m = re.search('^git@([^:\/]+):([^/]+)/([^/]+)', remoteurl)
        if m is None:
            m = re.search('^https://([^:/]+)/([^/]+)/([^/]+)', remoteurl)
        if m is not None:
            domain = m.group(1)
            username = m.group(2)
            project = m.group(3)
            if project.endswith(".git"):
                project = project[:-4]
            permalink = "https://{}/{}/{}/blob/{}/{}".format(domain, username, project,
                                                        sha1, relpath)
            # print("permalink = ", permalink)
            return (relpath, permalink)
        else:
            return (None, None)



    def add_raw(self, repo, files):
        result = None
        with cd(repo.rootdir):
            try:
                result = self._run(["add"] + files)
            except:
                pass


    def add_files(self, repo, files):
        """
        Add files to the repo
        """
        rootdir = repo.rootdir
        for f in files:
            relativepath = f['relativepath']
            sourcepath = f['localfullpath']
            if sourcepath is None:
                # This can happen if the relative path is a URL
                continue #
            # Prepare the target path
            targetpath = os.path.join(rootdir, relativepath)
            try:
                os.makedirs(os.path.dirname(targetpath))
            except:
                pass
            # print(sourcepath," => ", targetpath)
            print("Updating: {}".format(relativepath))
            shutil.copyfile(sourcepath, targetpath)
            with cd(repo.rootdir):
                self._run(['add', relativepath])

    def config(self, what='get', params=None):
        """
        Paramers:
        ---------

        workspace: Directory to store the dataset repositories
        email:
        """
        if what == 'get':
            return {
                'name': 'git',
                'nature': 'repomanager',
                'variables': [],
            }
        elif what == 'set':
            self.workspace = params['Local']['workspace']
            self.workspace = os.path.abspath(self.workspace)
            self.username = params['User']['user.name']
            self.fullname = params['User']['user.fullname']
            self.email = params['User']['user.email']

            repodir = os.path.join(self.workspace, 'datasets')
            if not os.path.exists(repodir):
                return

            for username in os.listdir(repodir):
                for reponame in os.listdir(os.path.join(repodir, username)):
                    if self.is_my_repo(username, reponame):
                        r = Repo(username, reponame)
                        r.rootdir = os.path.join(repodir, username, reponame)
                        package = os.path.join(r.rootdir, 'datapackage.json')
                        if not os.path.exists(package):
                            print("datapackage.json does not exist in dataset")
                            print("Skipping: {}/{}".format(username, reponame))
                            continue

                        packagedata = open(package).read()
                        r.package = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(packagedata)
                        r.manager = self
                        self.add(r)

def setup(mgr):

    obj = GitRepoManager()
    mgr.register('repomanager', obj)


#!/usr/bin/env python 

import os, sys, json, subprocess, re 
import shutil 
from sh import git 
from dgitcore.repomanager import RepoManagerBase, RepoManagerHelper
from dgitcore.helper import cd 

class GitRepoManager(RepoManagerBase):     
    """
    Repomanager to extract platform-specific information
    """
    def __init__(self): 
        self.username = None
        self.workspace = None
        self.metadatadir = '.git'
        self.repos = {} 
        self.per_dataset_repo = True 
        super(GitRepoManager, self).__init__('git', 
                                             'v0', 
                                             "Git-based repomanager")

    def run(self, cmd):
        cmd = " ".join(cmd) 
        output = subprocess.check_output(cmd, 
                                         stderr=subprocess.STDOUT, 
                                         shell=True)
        output = output.decode('utf-8')
        output = output.strip() 
        return output

    def init(self, username, reponame, force, backend=None): 
        """
        Initialize a Git repo 
        """
        key = (username, reponame) 
        
        # In local filesystem-based server, add a repo 
        server_repodir = self.server_rootdir(username, 
                                             reponame, 
                                             create=False)

        # Force cleanup if needed 
        if os.path.exists(server_repodir) and not force: 
            raise Exception("Repo already exists")

        if os.path.exists(server_repodir): 
            shutil.rmtree(server_repodir) 
        os.makedirs(server_repodir) 

        # Initialize the repo 
        with cd(server_repodir): 
            git.init(".", "--bare")

        if backend is not None: 
            backend.init_repo(server_repodir)

        # Now clone the filesystem-based repo 
        repodir = self.rootdir(username, reponame, 
                               create=False) 

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

        key = self.add(username, reponame, 
                 {
                     'username': username,
                     'reponame': reponame,
                     'rootdir': self.rootdir(username, reponame),
                     'remote-url': url
                 })

        return key 

    def clone(self, url, backend=None): 
        """
        Initialize a Git repo 
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

        if backend is None: 
            print("Backend is standard git server") 
            repodir = self.rootdir(username,  reponame, create=False)
            with cd(os.path.dirname(repodir)): 
                git.clone(url) 
        else: 
            if os.path.exists(server_repodir): 
                raise Exception("Local copy already exists") 

            # s3 -> .dgit/git/pingali/hello.git -> .dgit/datasets/pingali/hello 
            print("Backend cloned the repo") 
            backend.clone_repo(url, server_repodir)
            repodir = self.rootdir(username,  reponame, create=True)             
            with cd(os.path.dirname(repodir)): 
                git.clone(server_repodir, '--no-hardlinks') 

        self.add(username, reponame, 
                 {
                     'username': username,
                     'reponame': reponame,
                     'rootdir': self.rootdir(username, reponame),
                     'remote-url': url 
                 })

    def push(self, key): 
        repo = self.lookup(key=key)
        result = None
        print("Pushing to origin from local repository", repo['rootdir'])
        with cd(repo['rootdir']): 
            # Dont use sh. It is not collecting the stdout of all
            # child processes.
            pushoutput = self.run(["/usr/bin/git", 
                                   "push", "origin", 
                                   "master"])
            try: 
                result = {
                    'status': 'success',
                    'message': pushoutput,
                }
            except Exception as e: 
                result = {
                    'status': 'error',
                    'message': str(e) 
                }
             
        print(result) 
        return result         
        
        

    def status(self, key):        
        repo = self.lookup(key=key)
        result = None
        with cd(repo['rootdir']): 
            try: 
                result = {
                    'status': 'success',
                    'message': git.status()
                }
            except Exception as e: 
                result = {
                    'status': 'error',
                    'message': str(e) 
                }

        return result 

    def permalink(self, key, path):        
        """
        Get the permalink to command that generated the dataset 
        """

        if not os.path.exists(path):
            return None 
          
        # Get this directory 
        cwd = os.getcwd() 

        # Find the root of the repo and cd into that directory..
        os.chdir(os.path.dirname(path))    
        rootdir = self.run(["/usr/bin/git", "rev-parse", "--show-toplevel"])    
        os.chdir(rootdir)        
        # print("Rootdir = ", rootdir) 

        # Now find relative path 
        relpath = os.path.relpath(path, rootdir)
        # print("relpath = ", relpath) 

        # Get the last commit for this file
        #3764cc2600b221ac7d7497de3d0dbcb4cffa2914
        sha1 = self.run(["/usr/bin/git", "log", "-n", "1", "--format=format:%H", relpath])    
        #print("sha1 = ", sha1) 

        # Get the repo URL 
        #git@gitlab.com:pingali/simple-regression.git
        #https://gitlab.com/kanban_demo/test_project.git
        remoteurl = self.run(["/usr/bin/git", "config", "--get", "remote.origin.url"])
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
            print("permalink = ", permalink)
            return (relpath, permalink)
        else: 
            return (None, None) 


    def stash(self, key):
        """
        Stash the changes 
        """
        repo = self.lookup(key=key)
        with cd(repo['rootdir']): 
            try: 
                result = {
                    'status': 'success',
                    'message': git.stash() 
                }
            except Exception as e: 
                result = {
                    'status': 'error',
                    'message': str(e) 
                }

    def log(self, key):
        """
        Log of the changes
        """
        repo = self.lookup(key=key)
        with cd(repo['rootdir']): 
            output = self.run(["/usr/bin/git", "log"])
            try: 
                result = {
                    'status': 'success',
                    'message': output,
                    }
            except Exception as e: 
                result = {
                    'status': 'error',
                    'message': str(e) 
                }
            
        return result 

    def add_raw(self, key, files): 
        repo = self.lookup(key=key)
        result = None
        with cd(repo['rootdir']): 
            try: 
                result = git.add(files) 
            except: 
                pass 

    def commit(self, key, message): 
        """
        Commit files to a repo 
        """
        repo = self.lookup(key=key)
        result = None
        with cd(repo['rootdir']): 
            try: 
                result = git.commit('-m', message, '-a')
            except Exception as e: 
                result = {
                    'status': 'error',
                    'message': str(e) 
                }


    def add_files(self, key, files): 
        """
        Add files to the repo 
        """
        repo = self.lookup(key=key)
        rootdir = repo['rootdir']
        for f in files: 
            relativepath = f['relativepath']                        
            sourcepath = f['localfullpath']             
            # Prepare the target path
            targetpath = os.path.join(rootdir, relativepath) 
            try: 
                os.makedirs(os.path.dirname(targetpath))
            except:
                pass 
            print(sourcepath," => ", targetpath)
            shutil.copyfile(sourcepath, targetpath) 
            with cd(repo['rootdir']):             
                git.add(relativepath)

    def config(self, what='get', params=None): 
        """
        Paramers: 
        --------
        per_dataset_repo: Per dataset repo

        """
        if what == 'get': 
            return {
                'name': 'git', 
                'nature': 'repomanager',
                'variables': ['enable', 'per_dataset_repo'],
                'defaults': { 
                    'enable': {
                        'value': "n",
                        "description": "Use Git for storing datasets",
                    },            
                    'per_dataset_repo': {
                        'value': 'y',
                        'description': "Use one repo for each dataset"
                    },
                }
            }
        elif what == 'set': 
            self.workspace = params['Local']['workspace']
            self.username = params['User']['user.name']
            self.enable = params['git'].get('enable', 'n')
            self.per_dataset_repo = params['git'].get('per_dataset_repo', 'y') 
            if self.enable == 'n': 
                return 

            if self.per_dataset_repo == 'n': 
                raise Exception("Global repo for all datasets is not supported") 
                
            repodir = os.path.join(self.workspace, 'datasets')
            if not os.path.exists(repodir): 
                return 

            for username in os.listdir(repodir): 
                for reponame in os.listdir(os.path.join(repodir, username)):
                    if self.is_my_repo(username, reponame): 
                        rootdir = os.path.join(repodir, username, reponame)
                        repo = {
                            'username': username,
                            'reponame': reponame,
                            'rootdir': rootdir
                        }

                        package = os.path.join(repo['rootdir'], 'datapackage.json')
                        if not os.path.exists(package): 
                            print("Invalid dataset: %s/%s at %s " %(username, reponame, rootdir))
                            print("Skipping")
                            continue 
                        repo['package'] = json.loads(open(package).read())
                        self.add(username, reponame, repo) 
                    
def setup(mgr): 
    
    obj = GitRepoManager()
    mgr.register('repomanager', obj)


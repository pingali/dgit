#!/usr/bin/env python 
"""
This is the core module for manipulating the dataset metadata 
"""
import os, sys, copy, fnmatch, re, shutil 
import yaml, json, tempfile 
import webbrowser 
import subprocess, string, random, pipes
import shelve, getpass
from datetime import datetime
from hashlib import sha256
import mimetypes
import platform
import uuid, shutil 
import boto3, glob2 
import subprocess 
from dateutil import parser 
from ..config import get_config
from ..plugins.common import get_plugin_mgr 
from ..helper import bcolors, clean_str, cd, compute_sha256, run, clean_name
from .detect import get_schema
from .history import get_history

#####################################################    
# Repo independent commands...
#####################################################    
def lookup(username, dataset): 
    """
    Lookup a repo based on username dataset
    """
    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    repo =  repomgr.lookup(username=username, reponame=dataset) 
    return repo 

def list_repos(remote):
    mgr = get_plugin_mgr() 
    
    if not remote: 
        repomgr = mgr.get(what='repomanager', name='git') 
        repos = repomgr.get_repo_list() 
        repos.sort() 
        for r in repos: 
            print("{}/{}".format(*r))
    else:         
        repomgr = mgr.get(what='backend', name='s3') 


#####################################################    
# Repo specific generic commands
#####################################################    
def shellcmd(repo, args):   
    """
    Run a shell command within the repo's context
    """
    with cd(repo.rootdir):
        result = run(args) 
        print(result)


def datapackage_exists(repo): 
    """
    Check if the datapackage exists...
    """
    datapath = os.path.join(repo.rootdir,
                            "datapackage.json")
    return os.path.exists(os.path.dirname(datapath))

#####################################################    
# Repo specific simple commands 
#####################################################    
def generic_repo_cmd(repo, cmd, show=True, *args): 
    print("Running generic command", cmd, args)
    result = repo.run(cmd, *args) 
    if show:
        print("Status:", result['status'])
        print(result['message'])
    return result 
    
def log(repo, args): 
    """
    Log of the changes executed until now
    """
    return generic_repo_cmd(repo, 'log', True, args)

def push(repo, args): 
    """
    Push to S3 
    """
    return generic_repo_cmd(repo, 'push', True, args) 

def commit(repo, args): 
    """
    Commit the changes made...    
    """
    return generic_repo_cmd(repo, 'commit', True, args) 

def drop(repo, args): 
    """
    Commit the changes made...    
    """
    return generic_repo_cmd(repo, 'drop', True, args) 

def stash(repo, args): 
    """
    Stash the changes
    """
    return generic_repo_cmd(repo, 'stash', True, args) 

def delete(repo, force, files): 
    """
    Delete files
    """
    
    # Cleanup metadata for these files.
    missing = []
    for f in files: 
        found = False
        for i, r in enumerate(repo.package['resources']):
            if r['relativepath'] == f: 
                del repo.package['resources'][i]                
                found = True
                break 
        if not found: 
            missing.append(f)

    if len(missing) > 0: 
        print("Could not find metadata for the following:", missing) 
        print("Repo may have been corrupted")

    # Cleanup the repo
    generic_repo_cmd(repo, 'delete', False, 
                     force, files)

    
    # Now sync the metadata 
    (handle, filename) = tempfile.mkstemp()    
    with open(filename, 'w') as fd: 
        fd.write(json.dumps(repo.package, indent=4))

    # Update the file..
    repo.run('add_files',
             [
                 { 
                     'relativepath': 'datapackage.json',
                     'localfullpath': filename, 
                 }
             ])

def diff(repo, args): 
    """
    Delete files
    """
    return generic_repo_cmd(repo, 'diff', True, args) 


#####################################################    
# Initialize a repo 
#####################################################    
def bootstrap_datapackage(repo, force=False): 
    """ 
    Create the datapackage file..
    """
    
    # get the directory 
    tsprefix = datetime.now().date().isoformat()  

    # Initial data package json 
    package = {
        'uuid': str(uuid.uuid1()),
        'username': repo.username,
        'reponame': repo.reponame,
        'name': str(repo),
        'title': "",
        'description': "",
        'keywords': [], 
        'resources': [
        ],
        'creator': getpass.getuser(),
        'createdat': datetime.now().isoformat(),
        'remote-url': repo.remoteurl, 
    }

    for var in ['title', 'description']: 
        value = ''
        while value in ['',None]:
            value = input('Your dataset ' + var.title() + ": ")
            if len(value) == 0: 
                print("{} cannot be empty. Please re-enter.".format(var.title()))
                
        package[var] = value

    
    # Now store the package...
    (handle, filename) = tempfile.mkstemp()    
    with open(filename, 'w') as fd: 
        fd.write(json.dumps(package, indent=4))

    repo.package = package 

    return filename 

def init(username, dataset, setup, force):
    """
    Given a filename, prepare a datapackage.json for each dataset.
    """

    backend = None 
    if setup == 'git+s3':
        backend = 's3'

    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    backendmgr = mgr.get(what='backend', name=backend) 
    repo = repomgr.init(username, dataset, force, backendmgr) 

    # Now bootstrap the datapackage.json metadata file and copy it in...
    filename = bootstrap_datapackage(repo)
    repo.run('add_files',
             [
                 { 
                     'relativepath': 'datapackage.json',
                     'localfullpath': filename, 
                 }
             ])

    os.unlink(filename) 
    args = ['-a', '-m', 'Bootstrapped the datapackage']
    repo.run('commit', args)
                   
    
def clone(url): 
    """
    Given a filename, prepare a manifest for each dataset.
    """
    backend = None 
    backendmgr = None
    if url.startswith('s3'): 
        backend = 's3'
    elif url.startswith("http") or url.startswith("git"): 
        backend = 'git'
    else: 
        backend = None

    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    backendmgr = mgr.get(what='backend', name=backend) 
    key = repomgr.clone(url, backendmgr) 

    # Insert a datapackage if it doesnt already exist...
    repo = repomgr.lookup(key=key)    
    if not datapackage_exists(repo):
        bootstrap_datapackage(repo)
        args = ['-a', '-m', 'Bootstrapped cloned repo']
        repomgr.commit(key, args)

#####################################################
# Add content to the metadata
#####################################################
def add_preview(repo, size, args): 

    rootdir = repo.rootdir 
    packagefilename = 'datapackage.json' 
    package = repo.package
    
    files = package['resources'] 
    for f in files: 
        
        relativepath = f['relativepath']
        path = os.path.join(rootdir, relativepath) 

        # Should I be adding a snippet? 
        match = False
        for i in args: 
            if fnmatch.fnmatch(path, i) or fnmatch.fnmatch(relativepath, i):
                match = True
                break 
                
        if match: 
            print("Reading content", path)
            f['content'] = open(path).read()[:size]
            f['schema'] = get_schema(path) 

    
    # Write a temp file 
    (handle, filename) = tempfile.mkstemp()    
    with open(filename, 'w') as fd: 
        fd.write(json.dumps(package, indent=4))

    # Add it to the list of files...
    repo.run('add_files',[
        { 
            'relativepath': 'datapackage.json',
            'localfullpath': filename, 
        }
    ])
    

def status(repo, details, args): 

    result = generic_repo_cmd(repo, 'status', False, args)

    if details: 
        print("Dataset: %s" %(str(repo)))
        print("Backend: %s" %(repo.package['remote-url']))
    print("Status: ", result['status'])
    print("Message:") 
    print(result['message']) 

    if 'dirty' in result and not result['dirty']: 
        print("Nothing to commit, working directory clean")

    if 'deleted-files' in result and len(result['deleted-files']) > 0: 
        print("Deleted files:")
        for x in result['deleted-files']: 
            print(bcolors.FAIL + "    deleted: " +x + bcolors.ENDC)

    if 'new-files' in result and len(result['new-files']) > 0: 
        print("New files:")
        for x in result['new-files']: 
            print(bcolors.OKGREEN + "    new: " +x + bcolors.ENDC)

    if 'renamed-files' in result and len(result['renamed-files']) > 0: 
        print("Renamed files:")
        for x in result['renamed-files']: 
            print(bcolors.OKGREEN + "    renamed: %s -> %s " %(x['from'],x['to']) + bcolors.ENDC)
                
    if (('untracked-files' in result) and 
        (len(result['untracked-files']) > 0)): 
        print("Untracked files:")
        for f in result['untracked-files']: 
            print("   untracked:", f)



###########################################################
# Post metadata to a server
###########################################################
def post(repo, args): 
    """
    Post to metadata server
    """

    mgr = get_plugin_mgr() 
    metadatamgr = mgr.get(what='metadata',name='generic-metadata') 
    try: 
        # Annotate with history as well...
        package = repo.package 
        package['history'] = get_history(repo.rootdir) 
        metadatamgr.post(package)
    except Exception as e:
        print(e)
        print("Could not post. Please look at the log files")
        return 


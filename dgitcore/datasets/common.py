#!/usr/bin/env python 
"""
This is the core module for manipulating the dataset metadata 
"""
import os, sys, copy, fnmatch, re, shutil 
import yaml, json, tempfile, mimetypes
import webbrowser, traceback 
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
def lookup(username, reponame): 
    """
    Lookup a repo based on username reponame
    """
    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    repo =  repomgr.lookup(username=username, reponame=reponame) 
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

def delete(repo, args): 
    """
    Delete files
    """
    
    # Cleanup the repo
    generic_repo_cmd(repo, 'delete', False, args)

    # Have to sync up repo files and datapackage.json 
    print("XXXX Update datapackage.json") 
    
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
            value = input('Your Repo ' + var.title() + ": ")
            if len(value) == 0: 
                print("{} cannot be empty. Please re-enter.".format(var.title()))
                
        package[var] = value

    
    # Now store the package...
    (handle, filename) = tempfile.mkstemp()    
    with open(filename, 'w') as fd: 
        fd.write(json.dumps(package, indent=4))

    repo.package = package 

    return filename 

def init(username, reponame, setup, force):
    """
    Given a filename, prepare a datapackage.json for each repo.
    """

    backend = None 
    if setup == 'git+s3':
        backend = 's3'

    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    backendmgr = mgr.get(what='backend', name=backend) 
    repo = repomgr.init(username, reponame, force, backendmgr) 

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
    return repo 
    
def clone(url): 
    """
    Clone a S3/Other URL 
    """
    backend = None 
    backendmgr = None
    if url.startswith('s3'): 
        backendtype = 's3'
    elif url.startswith("http") or url.startswith("git"): 
        backendtype = 'git'
    else: 
        backendtype = None

    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    backendmgr = mgr.get(what='backend', name=backendtype) 
    
    if backendmgr is not None and not backendmgr.url_is_valid(url): 
        raise Exception("Invalid URL") 
        
    key = repomgr.clone(url, backendmgr) 

    # Insert a datapackage if it doesnt already exist...
    repo = repomgr.lookup(key=key)    
    if not datapackage_exists(repo):
        bootstrap_datapackage(repo)
        args = ['-a', '-m', 'Bootstrapped cloned repo']
        repomgr.commit(key, args)

    return repo 


def status(repo, details, args): 

    result = generic_repo_cmd(repo, 'status', False, args)

    if details: 
        print("Repo: %s" %(str(repo)))
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

def annotate_metadata_data(repo, task, patterns, size=0): 
    """
    Update metadata with the content of the files
    """
    
    matching_files = repo.find_matching_files(patterns)
    package = repo.package
    rootdir = repo.rootdir 
    files = package['resources'] 
    for f in files:
        relativepath = f['relativepath']
        if relativepath in matching_files: 
            path = os.path.join(rootdir, relativepath) 
            if task == 'preview': 
                print("Adding preview for ", path)
                f['content'] = open(path).read()[:size]            
            elif task == 'schema': 
                print("Adding schema for ", path)
                f['schema'] = get_schema(path) 

def annotate_metadata_code(repo, files):
    """
    Update metadata with the commit information 
    """
    
    package = repo.package 
    package['code'] = []
    for f in files: 
        f = os.path.abspath(f)
        package['code'].append({ 
            'permalink': repo.manager.permalink(repo, f),
            'uuid': str(uuid.uuid1()),
            'mimetypes': mimetypes.guess_type(f)[0],
            'sha256': compute_sha256(f),
        })


def annotate_metadata_platform(repo):
    """
    Update metadata host information
    """

    print("Added platform information")    
    package = repo.package 
    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='instrumentation', name='platform') 
    package['platform'] = repomgr.get_metadata()
    

def post(repo, args=[]): 
    """
    Post to metadata server
    """


    if 'metadata-management' in repo.options:

        metadata = repo.options['metadata-management']
        
        # Add data repo history 
        if 'include-data-history' in metadata and metadata['include-data-history']: 
            print("Including history")
            repo.package['history'] = get_history(repo.rootdir)

        # Add data repo history 
        if 'include-preview' in metadata: 
            annotate_metadata_data(repo, 
                                   task='preview',
                                   patterns=metadata['include-preview']['files'],
                                   size=metadata['include-preview']['length'])

        if 'include-schema' in metadata: 
            annotate_metadata_data(repo, 
                                   task='schema',
                                   patterns=metadata['include-schema'])
            
        if 'include-code-history' in metadata: 
            annotate_metadata_code(repo, 
                                   files=metadata['include-code-history'])

        if 'include-platform' in metadata: 
            annotate_metadata_platform(repo)
            

    try: 
        mgr = get_plugin_mgr() 
        keys = mgr.search(what='metadata')
        keys = keys['metadata']
        for k in keys: 
            print("Key", k)
            metadatamgr = mgr.get_by_key('metadata', k)
            print("Posting to ", metadatamgr)
            metadatamgr.post(repo)
    except Exception as e:
        traceback.print_exc()
        print(e)
        print("Could not post. Please look at the log files")
        return 


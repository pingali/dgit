#!/usr/bin/env python
"""
This is the core module for manipulating the dataset metadata
"""
import os, sys, copy, fnmatch, re, shutil
import yaml, json, tempfile, mimetypes
import webbrowser, traceback, collections
import subprocess, string, random, pipes
from collections import OrderedDict
import shelve, getpass
from datetime import datetime
from hashlib import sha256
import mimetypes
import platform
import uuid, shutil
import boto3, glob2
import subprocess
from dateutil import parser
try:
    from urllib.parse import urlparse
except:
    from urlparse import urlparse
from ..config import get_config
from ..plugins.common import plugins_get_mgr
from ..helper import bcolors, clean_str, cd, compute_sha256, run, clean_name
from ..exceptions import *
from .detect import get_schema
from .history import get_history, get_diffs
from .validation import validate

#####################################################
# Exports
#####################################################

__all__ = [
    'lookup',
    'list_repos',
    'shellcmd',
    'log', 'show', 'push', 'pull', 'commit',
    'stash', 'drop', 'status', 'post',
    'clone', 'init', 'diff',
    'remote'
]

#####################################################
# Repo independent commands...
#####################################################
def lookup(username, reponame):
    """
    Lookup a repo based on username reponame
    """

    mgr = plugins_get_mgr()

    # XXX This should be generalized to all repo managers.
    repomgr = mgr.get(what='repomanager', name='git')
    repo =  repomgr.lookup(username=username,
                           reponame=reponame)
    return repo

def list_repos(remote=False):
    """
    List repos

    Parameters
    ----------

    remote: Flag
    """
    mgr = plugins_get_mgr()

    if not remote:
        repomgr = mgr.get(what='repomanager', name='git')
        repos = repomgr.get_repo_list()
        repos.sort()
        return repos
    else:
        raise Exception("Not supported yet")


#####################################################
# Repo specific generic commands
#####################################################
def shellcmd(repo, args):
    """
    Run a shell command within the repo's context

    Parameters
    ----------

    repo: Repository object
    args: Shell command
    """
    with cd(repo.rootdir):
        result = run(args)
        return result


def datapackage_exists(repo):
    """
    Check if the datapackage exists...
    """
    datapath = os.path.join(repo.rootdir, "datapackage.json")
    return os.path.exists(datapath)

#####################################################
# Repo specific simple commands
#####################################################
def generic_repo_cmd(repo, cmd, *args):
    # print("Running generic command", cmd, args)
    return repo.run(cmd, *args)


def log(repo, args=[]):
    """
    Log of the changes executed until now

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'log', args)

def show(repo, args=[]):
    """
    Show commit details

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'show', args)

def remote(repo, args=[]):
    """
    Show remote

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'remote', args)

def push(repo, args=[]):
    """
    Push changes to the backend

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'push', args)

def pull(repo, args=[]):
    """
    Pull changes from the backend

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'pull', args)

def commit(repo, args=[]):
    """
    Commit changes to the data repository

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'commit', args)

def drop(repo, args=[]):
    """
    Drop the repository (new to dgit)

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'drop', args)

def stash(repo, args=[]):
    """
    Stash the changes

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'stash', args)

def diff(repo, args=[]):
    """
    Diff between versions

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """
    return generic_repo_cmd(repo, 'diff', args)

def status(repo, args=[]):
    """
    Show status of the repo

    Parameters
    ----------

    repo: Repository object (result of lookup)
    details: Show internal details of the repo
    args: Parameters to be passed to git status command

    """

    result = generic_repo_cmd(repo, 'status', args)
    return result


def delete(repo, args=[]):
    """
    Delete files

    Parameters
    ----------

    repo: Repository object
    args: Arguments to git command
    """

    message = """Delete is not yet implemented completely. datapackage.json should be updated to keep in sync with files on disk."""
    raise NotImplemented()

    # Cleanup the repo
    generic_repo_cmd(repo, 'delete', args)

    # Have to sync up repo files and datapackage.json
    # XXX MISSING

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



#####################################################
# Initialize a repo
#####################################################
def bootstrap_datapackage(repo, force=False,
                          options=None, noinput=False):
    """
    Create the datapackage file..
    """

    print("Bootstrapping datapackage")

    # get the directory
    tsprefix = datetime.now().date().isoformat()

    # Initial data package json
    package = OrderedDict([
        ('title', ''),
        ('description', ''),
        ('username', repo.username),
        ('reponame', repo.reponame),
        ('name', str(repo)),
        ('title', ""),
        ('description', ""),
        ('keywords', []),
        ('resources', []),
        ('creator', getpass.getuser()),
        ('createdat', datetime.now().isoformat()),
        ('remote-url', repo.remoteurl)
    ])

    if options is not None:
        package['title'] = options['title']
        package['description'] = options['description']
    else:
        if noinput:
            raise IncompleteParameters("Option field with title and description")

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

def init(username, reponame, setup,
         force=False, options=None,
         noinput=False):
    """
    Initialize an empty repository with datapackage.json

    Parameters
    ----------

    username: Name of the user
    reponame: Name of the repo
    setup: Specify the 'configuration' (git only, git+s3 backend etc)
    force: Force creation of the files
    options: Dictionary with content of dgit.json, if available.
    noinput: Automatic operation with no human interaction
    """

    mgr = plugins_get_mgr()
    repomgr = mgr.get(what='repomanager', name='git')

    backendmgr = None
    if setup == 'git+s3':
        backendmgr = mgr.get(what='backend', name='s3')

    repo = repomgr.init(username, reponame, force, backendmgr)

    # Now bootstrap the datapackage.json metadata file and copy it in...

    # Insert a gitignore with .dgit directory in the repo. This
    # directory will be used to store partial results
    (handle, gitignore) = tempfile.mkstemp()
    with open(gitignore, 'w') as fd:
        fd.write(".dgit")

    # Try to bootstrap. If you cant, cleanup and return
    try:
        filename = bootstrap_datapackage(repo, force, options, noinput)
    except Exception as e:
        repomgr.drop(repo,[])
        os.unlink(gitignore)
        raise e

    repo.run('add_files',
             [
                 {
                     'relativepath': 'datapackage.json',
                     'localfullpath': filename,
                 },
                 {
                     'relativepath': '.gitignore',
                     'localfullpath': gitignore,
                 },
             ])


    # Cleanup temp files
    os.unlink(filename)
    os.unlink(gitignore)

    args = ['-a', '-m', 'Bootstrapped the repo']
    repo.run('commit', args)
    return repo

def clone(url):
    """
    Clone a URL. Examples include:

        - git@github.com:pingali/dgit.git
        - https://github.com:pingali/dgit.git
        - s3://mybucket/git/pingali/dgit.git

    Parameters
    ----------

    url: URL of the repo

    """
    backend = None
    backendmgr = None
    if url.startswith('s3'):
        backendtype = 's3'
    elif url.startswith("http") or url.startswith("git"):
        backendtype = 'git'
    else:
        backendtype = None

    mgr = plugins_get_mgr()
    repomgr = mgr.get(what='repomanager', name='git')
    backendmgr = mgr.get(what='backend', name=backendtype)

    # print("Testing {} with backend {}".format(url, backendmgr))
    if backendmgr is not None and not backendmgr.url_is_valid(url):
        raise InvalidParameters("Invalid URL")

    key = repomgr.clone(url, backendmgr)

    # Insert a datapackage if it doesnt already exist...
    repo = repomgr.lookup(key=key)
    if not datapackage_exists(repo):
        filename = bootstrap_datapackage(repo)
        repo.run('add_files',
                 [
                     {
                         'relativepath': 'datapackage.json',
                         'localfullpath': filename,
                    },
                 ])
        os.unlink(filename)
        args = ['-a', '-m', 'Bootstrapped the repo']
        repo.run('commit', args)

    return repo



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
                print("Adding preview for ", relativepath)
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
    for p in files:
        matching_files = glob2.glob("**/{}".format(p))
        for f in matching_files:
            absf = os.path.abspath(f)
            print("Add commit data for {}".format(f))
            package['code'].append(OrderedDict([
                ('script', f),
                ('permalink', repo.manager.permalink(repo, absf)),
                ('mimetypes', mimetypes.guess_type(absf)[0]),
                ('sha256', compute_sha256(absf))
            ]))


def annotate_metadata_platform(repo):
    """
    Update metadata host information
    """

    print("Added platform information")
    package = repo.package
    mgr = plugins_get_mgr()
    repomgr = mgr.get(what='instrumentation', name='platform')
    package['platform'] = repomgr.get_metadata()

def annotate_metadata_diffs(repo):

    print("Computing diffs")
    with cd(repo.rootdir):
        get_diffs(repo.package['history'])

def annotate_metadata_validation(repo):

    print("Adding validation information")
    # Collect the validation results by relativepath
    results = validate(repo)
    fileresults = {}
    for r in results:
        filename = r['target']
        if filename not in fileresults:
            fileresults[filename] = []
        fileresults[filename].append(r)

    for r in repo.package['resources']:
        path = r['relativepath']
        if path in fileresults:
            r['validation'] = fileresults[path]

def annotate_metadata_dependencies(repo):
    """
    Collect information from the dependent repo's
    """

    options = repo.options

    if 'dependencies' not in options:
        print("No dependencies")
        return []

    repos = []
    dependent_repos = options['dependencies']
    for d in dependent_repos:
        if "/" not in d:
            print("Invalid dependency specification")
        (username, reponame) = d.split("/")
        try:
            repos.append(repo.manager.lookup(username, reponame))
        except:
            print("Repository does not exist. Please create one", d)

    package = repo.package
    package['dependencies'] = []
    for r in repos:
        package['dependencies'].append({
            'username': r.username,
            'reponame': r.reponame,
            })

def post(repo, args=[]):
    """
    Post to metadata server

    Parameters
    ----------

    repo: Repository object (result of lookup)
    """

    mgr = plugins_get_mgr()
    keys = mgr.search(what='metadata')
    keys = keys['metadata']

    if len(keys) == 0:
        return

    # Incorporate pipeline information...
    if 'pipeline' in repo.options:
        for name, details in repo.options['pipeline'].items():
            patterns = details['files']
            matching_files = repo.find_matching_files(patterns)
            matching_files.sort()
            details['files'] = matching_files
            for i, f in enumerate(matching_files):
                r = repo.get_resource(f)
                if 'pipeline' not in r:
                    r['pipeline'] = []
                r['pipeline'].append(name + " [Step {}]".format(i))

    if 'metadata-management' in repo.options:

        print("Collecting all the required metadata to post")
        metadata = repo.options['metadata-management']

        # Add data repo history
        if 'include-data-history' in metadata and metadata['include-data-history']:
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

        if 'include-validation' in metadata:
            annotate_metadata_validation(repo)

        if 'include-dependencies' in metadata:
            annotate_metadata_dependencies(repo)

        history = repo.package.get('history',None)
        if (('include-tab-diffs' in metadata) and
            metadata['include-tab-diffs'] and
            history is not None):
            annotate_metadata_diffs(repo)

        # Insert options as well
        repo.package['config'] = repo.options

    try:
        for k in keys:
            # print("Key", k)
            metadatamgr = mgr.get_by_key('metadata', k)
            url = metadatamgr.url
            o = urlparse(url)
            print("Posting to ", o.netloc)
            response = metadatamgr.post(repo)
            if isinstance(response, str):
                print("Error while posting:", response)
            elif response.status_code in [400]:
                content = response.json()
                print("Error while posting:")
                for k in content:
                    print("   ", k,"- ", ",".join(content[k]))
    except NetworkError as e:
        print("Unable to reach metadata server!")
    except NetworkInvalidConfiguration as e:
        print("Invalid network configuration in the INI file")
        print(e.message)
    except Exception as e:
        print("Could not post. Unknown error")
        print(e)



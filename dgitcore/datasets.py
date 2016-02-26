#!/usr/bin/env python 
"""
This is the core module for manipulating the dataset metadata 
"""
import os, sys, copy, fnmatch, re  
import yaml, json, tempfile 
import webbrowser 
import subprocess, string, random 
import shelve, getpass
from datetime import datetime
from hashlib import sha1 
import mimetypes
import platform
import uuid, shutil 
import boto3, glob2 
import subprocess 
from dateutil import parser 
from .config import get_config
from .aws import get_session 
from .plugins import get_plugin_mgr 
from .helper import bcolors, clean_str 

def clean_name(n): 
    n = "".join([x if (x.isalnum() or x == "-") else "_" for x in n])    
    return n

def compute_sha1(filename):    
    h = sha1()
    fd = open(filename) 
    while True: 
        buf = fd.read(0x1000000)
        if buf in [None, ""]:
            break 
        h.update(buf.encode('utf-8')) 
    return h.hexdigest() 

def check_datapackage(repo): 
    """
    Check if the datapackage exists...
    """
    rootdir = repo['rootdir']
    datapath = os.path.join(rootdir,"datapackage.json")
    return os.path.exists(os.path.dirname(datapath))

    
def bootstrap_datapackage(repo, force=False): 
    """ 
    Create the datapackage file..
    """
    
    print("Bootstrapping datapackage") 
    print(json.dumps(repo, indent=4))

    # get the directory 
    tsprefix = datetime.now().date().isoformat()  

    # Initial data package json 
    package = {
        'uuid': str(uuid.uuid1()),
        'username': repo['username'],
        'reponame': repo['reponame'],
        'name': "%(username)s/%(reponame)s" % repo,
        'title': "",
        'description': "",
        'keywords': [], 
        'resources': [
        ],
        'creator': getpass.getuser(),
        'createdat': datetime.now().isoformat(),
        'remote-url': repo['remote-url']
    }

    # Get user input...
    with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
        print("Name of file", temp.name)
        temp.write(yaml.dump(package, default_flow_style=False).encode('utf-8'))
        temp.flush()
        EDITOR = os.environ.get('EDITOR','/usr/bin/vi')
        subprocess.call("%s %s" %(EDITOR,temp.name), shell=True)
        temp.seek(0)
        data = temp.read() 
        conf = yaml.load(data) 

    # Now store the package...
    rootdir = repo['rootdir']
    datapath = os.path.join(rootdir,"datapackage.json")
    if os.path.exists(datapath) and not force:
        print("A bootstrapping directory already exists for the dataset:")
        print(os.path.dirname(datapath))
        sys.exit()     

    with open(datapath, 'w') as fd: 
        fd.write(json.dumps(conf, indent=4))

    return 

def init(username, dataset, setup, force):
    """
    Given a filename, prepare a datapackage.json for each dataset.
    """
    repo = 'git'
    backend = None 
    if setup == 'git+s3':
        backend = 's3'

    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name=repo) 
    backendmgr = mgr.get(what='backend', name=backend) 
    key = repomgr.init(username, dataset, force, backendmgr) 

    # Now bootstrap the datapackage.json metadata file...
    repo = repomgr.lookup(key=key)
    bootstrap_datapackage(repo)
    repomgr.add_files(key, ['datapackage.json'])
    repomgr.commit(key, message="Bootstrapped the datapackage")

                   
    
def clone(url): 
    """
    Given a filename, prepare a manifest for each dataset.
    """
    repo = 'git'
    backend = None 
    backendmgr = None
    if url.startswith('s3'): 
        backend = 's3'
    elif url.startswith("http") or url.startswith("git"): 
        backend = 'git'
    else: 
        backend = None

    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name=repo) 
    backendmgr = mgr.get(what='backend', name=backend) 
    key = repomgr.clone(url, backendmgr) 

    # Insert a datapackage if it doesnt already exist...
    repo = repomgr.lookup(key=key)    
    if check_datapackage(repo):
        bootstrap_datapackage(repo)
        repomgr.commit(key, message="Bootstrapped cloned repo")

def push(username, dataset):
    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='repomanager', name='git') 
    key = repomgr.key(username, dataset) 
    repomgr.push(key)


def add_files(args, script):
        
    files = []

    # get the directory 
    ts = datetime.now().isoformat()     
    
    for f in args: 
        basename = os.path.basename(f)
        change = 'update' if basename in files else 'add'
        update = {
            'change': change,
            'type': 'data' if not script else 'script',
            'uuid': str(uuid.uuid1()),
            'filename': basename, 
            'mimetypes': mimetypes.guess_type(f)[0],
            'sha1': compute_sha1(f),
            'ts': ts, 
            'localfullpath': f,
            'localrelativepath': os.path.relpath(f, ".")
        }

        print("Added change:", change, basename)
        files.append(update)             
        
    return files
    
def add(username, dataset, args, 
        execute, includes, script=False): 
    """
    Given a filename, prepare a manifest for each dataset.
    """

    mgr = get_plugin_mgr() 
    (repomanager, repo) = mgr.get_by_repo(username, dataset)
    if repo is None: 
        raise Exception("Invalid repo") 

    # Gather the files...
    if not execute: 
        files = add_files(args, script) 
    else: 
        files = run_executable(args, includes)

    if files is not None and len(files) > 0: 
        repomanager.add_files(repo, files) 

    return 

def stash(username, dataset): 
    """
    Show what has changed in a repo
    """

    mgr = get_plugin_mgr() 
    (repomanager, repo) = mgr.get_by_repo(username, dataset)
    if repo is None: 
        raise Exception("Invalid repo") 
        
    repomanager.stash(repo) 

def stash1(username, dataset): 
    state = get_state()

    repo = state['datasets'][username][dataset]
    metadata = repo['metadata']
    commits = repo['commits']

    # Cleanup metadata
    if 'changes' in metadata and len(metadata['changes']['files']) > 0: 
        metadata['changes']['files'] = []

    # Cleanup the directory...
    workspace = state['config']['Local']['workspace']
                
    # Cleanup files on disk as well as json 
    try: 
        tmpdir = os.path.join(workspace, "tmp", username, dataset) 
        shutil.rmtree(tmpdir)
    except:
        pass 
    
    state.sync() 

def status(name, details): 

    mgr = get_plugin_mgr() 
    
    # Find all repo managers
    repomanager_keys = mgr.search(what='repomanager')['repomanager']
    for repomanager_key in repomanager_keys: 
        repomanager = mgr.get_by_key('repomanager', repomanager_key) 
        repokeys = repomanager.get_repos() 
        for key in repokeys: 
            result = repomanager.status(key)

            print("Dataset: %s/%s" %(key[0], key[1]))
            print("Backend: %s" %(repomanager_key[0].upper()))
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

    
    
def status1(name, details): 
    """
    Show all datasets available locally along with changes 
    """

    state = get_state()
    workspace = state['config']['Local']['workspace']

    for username in state['datasets']: 
        for dataset in state['datasets'][username]: 
            if ((name is None) or
                (name == username) or 
                (name == dataset)):               
                repo = state['datasets'][username][dataset]

                metadata = repo['metadata']
                commits = repo['commits']                
                trackedfiles = []
                print("%s/%s : %s" %(username, dataset, 
                                     metadata['title']))
                if 'changes' in metadata: 
                    for c in metadata['changes']['files']: 
                        trackedfiles.append(c['filename'])
                        if c['change'] == 'add': 
                            print("      New file: (%s) " %(c['type']) 
                                  + bcolors.OKGREEN + c['filename'] + bcolors.ENDC)
                        elif c['change'] == 'update': 
                            print("  Updated file: (%s) "  %(c['type'])
                                  + bcolors.WARNING + c['filename'] + bcolors.ENDC)
                        elif c['change'] == 'delete': 
                            print("  Deleted file: (%s) " %(c['type']) 
                                  + bcolors.FAIL + c['filename'] + bcolors.ENDC)
                        else: 
                            print("    Error file: " + 
                                  bcolors.OKBLUE + c['filename'] + 
                                  bcolors.ENDC)

                # Find extra unaccounted for files...
                tmpdir = os.path.join(workspace, "tmp", username, dataset) 
                msg = ""
                paths = glob2.glob(os.path.join(tmpdir, '**', '*'))
                for p in paths: 
                    if os.path.isfile(p) and os.path.relpath(p, tmpdir) not in trackedfiles:
                        print("  Untracked file: " + bcolors.FAIL + p + bcolors.ENDC)                
                            
                if details: 
                    data = json.dumps(repo, indent=4)
                    lines = data.split("\n")
                    for l in lines: 
                        sys.stdout.write('     {l}\n'.format(l=l))

    return 

def log(username, dataset): 
    """
    Log of the changes executed until now
    """

    mgr = get_plugin_mgr() 
    (repomanager, repokey) = mgr.get_by_repo(username, dataset)
    if repokey is None: 
        raise Exception("Invalid repo") 
    
    result = repomanager.log(repokey)
    print("Status:", result['status'])
    print(result['message'])


def commit(username, dataset, message): 
    """
    Commit the changes made...
    """
    mgr = get_plugin_mgr() 
    (repomanager, repo) = mgr.get_by_repo(username, dataset)
    if repo is None: 
        raise Exception("Invalid repo") 

    repomanager.commit(repo, message) 

def commit1(username, dataset, message): 
    # No files to commit
    if 'changes' in metadata and len(metadata['changes']['files']) == 0: 
        print("No changes to commit")
        return 
        
    commitid = str(uuid.uuid1())

    # Take the last commit and update it with new values...
    commit = {
        'id': commitid, 
        'createdat': datetime.now().isoformat(),
        'user': getpass.getuser(),
        'message': message,
        'changed-files': [],
        'status': {}
    }

    workspace = state['config']['Local']['workspace']    
    rootpath = os.path.join(workspace, 'datasets', 
                            username, dataset)
    filesdir = os.path.join(rootpath, commitid)
    try: 
        os.makedirs(filesdir)
    except:
        pass 

    # Go through each file to see what is to be done...
    # Compute target path
    # Copy file/delete file 
    # construct status 
    # Update the metadata 
    for c in metadata['changes']['files']: 
        if c['change'] == 'add': 
            targetpath = os.path.join(filesdir, c['filename'])
            try:
                os.makedirs(os.path.dirname(targetpath))
            except:
                pass 
            shutil.copy(c['localfullpath'], targetpath)
            metadata['files'].append(c) 
            status = { 
                'status': 'added',
                'commitid': commitid,
                'hash': compute_sha1(targetpath)
            }
            commit['changed-files'].append(c['filename'])
            commit['status'][c['filename']] = status
        elif c['change'] == 'update': 
            targetpath = os.path.join(filesdir, c['filename'])
            try:
                os.makedirs(os.path.dirname(targetpath))
            except:
                pass  
            shutil.copy(c['localfullpath'], targetpath)
            for i in range(len(metadata['files'])): 
                if metadata['files'][i]['filename'] == c['filename']:
                    metadata['files'][i] = c 
                    break                 
            status = { 
                'status': 'updated',
                'commitid': commitid,
                'hash': compute_sha1(targetpath)
            }
            commit['changed-files'].append(c['filename'])
            commit['status'][c['filename']] = status
        elif c['change'] == 'delete': 
            for i in range(len(metadata['files'])): 
                if metadata['files'][i]['filename'] == c['filename']:
                    metadata['files'].pop(i)

    metadata['changes']['files'] = [] 

    # Save the datapackage.json.
    datapath = os.path.join(rootpath,commitid,"datapackage.json")
    with open(datapath, 'w') as fd: 
        fd.write(json.dumps(metadata, indent=4))

    # add datapackage.json to the list of updated files...
    ts = datetime.now().isoformat()  
    commit['changed-files'].append('datapackage.json')
    commit['status']['datapackage.json'] = {
        "mimetype": "application/json",
        "type": "package",
        "createdat": ts, 
        "filename": "datapackage.json",
        "path": "%s/datapackage.json" %(commitid)
    }
    # Update the metadata 
    for i in range(len(metadata['files'])): 
        if metadata['files'][i]['filename'] == 'datapackage.json': 
            metadata['files'][i] = commit['status']['datapackage.json'] 

    commits.insert(0, commit) # Insert the new commit 
    

    # Save the commits 
    commitspath = os.path.join(rootpath,"commits.json")
    with open(commitspath, 'w') as fd: 
        fd.write(json.dumps(commits, indent=4))

    state['datasets'][username][dataset] = { 
        'metadata': metadata,
        'commits': commits
    }

    state.sync() 

    return 


def drop(name): 
    """
    Drop a particular dataset
    """
    state = get_state()
    
    matched = False
    for i in range(len(state['datasets'])):
        d = state['datasets'][i]
        if name in [d['name'], d['uuid']] :
            matched = True
            res = input("Deleting dataset (%s)? [yN] : " %(name))
            if res.lower() == 'y': 
                del state['datasets'][i]

    if not matched: 
        print("No datasets matched the specified name.")
        print("Note that for dropping, the precise name is required")
        sys.exit() 

    state.sync() 
            
def extract_files(filename, includes): 
    """
    Extract the files to be added based on the includes 
    """

    lines = open(filename).readlines() 

    # Extract only open files - whether for read or write. You often
    # want to capture the json/ini configuration file 
    # 20826 open("/usr/lib/locale/locale-archive", O_RDONLY|O_CLOEXEC) = 3
    files = []
    lines = [l.strip() for l in lines if 'open(' in l]
    for l in lines: 
        try:
            matchedfile = re.search('open\("(.+?)\"', l).group(1)
        except AttributeError:
            matchedfile = None
                
        if matchedfile is not None and os.path.isfile(matchedfile) and os.path.exists(matchedfile): 
            matchedfile = os.path.relpath(matchedfile, ".")
            for i in includes: 
                if fnmatch.fnmatch(matchedfile, i):
                    files.append(matchedfile)

    input('Please select files to keep (press ENTER)')

    # Let the user have the final say on which files must be included.
    with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
        temp.write(yaml.dump(files, default_flow_style=False).encode('utf-8'))
        temp.flush()
        EDITOR = os.environ.get('EDITOR','/usr/bin/vi')
        subprocess.call("%s %s" %(EDITOR,temp.name), shell=True)
        temp.seek(0)
        data = temp.read() 
        files = yaml.load(data) 

    print("You selected", len(files), "file(s)")

    # Now we know the list of files. Where should they go? 
    print('Please select target locations for each of the relative paths')
    print('Please make sure you do not delete any rows or edit the keys.')
    input('(press ENTER)')
    prefixes = {} 
    for f in files: 
        dirname = os.path.dirname(f)
        prefixes[dirname] = dirname 

    while True: 
        with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
            temp.write(yaml.dump(prefixes, default_flow_style=False).encode('utf-8'))
            temp.flush()
            EDITOR = os.environ.get('EDITOR','/usr/bin/vi')
            subprocess.call("%s %s" %(EDITOR,temp.name), shell=True)
            temp.seek(0)
            data = temp.read() 
            try: 
                revised = yaml.load(data) 
            except Exception as e: 
                print(e) 
                revised = {} 

            print(list(revised.keys()))
            print(list(prefixes.keys()))

            if set(list(revised.keys())) == set(list(prefixes.keys())):
                prefixes = revised 
                break 
            else: 
                print("Could not process edited file. Either some rows are missing or entry has YAML syntax errors")
                input("Press ENTER to continue")

    result = []
    ts = datetime.now().isoformat()     
    for f in files: 
        result.append({
            "localfullpath": os.path.abspath(f),
            "filename": os.path.join(prefixes[os.path.dirname(f)], os.path.basename(f)),
            'type': 'run-output',
            'uuid': str(uuid.uuid1()),
            'mimetypes': mimetypes.guess_type(f)[0],
            'sha1': compute_sha1(f),
            'ts': ts, 
            'localrelativepath': os.path.relpath(f, ".")
        })
        
    print(json.dumps(result, indent=4))
    return result

def run_executable(args, includes): 
    """
    Run the executable and capture the input and output...
    """
    
    # Create a local directory 
    tmpdir = tempfile.mkdtemp()

    # Construct the strace command
    strace_filename = os.path.join(tmpdir,'strace.out.txt')
    cmd = ["/usr/bin/strace", "-f", "-o", strace_filename, 
           "-s", "1024", "-q"] + args 
    
    # Run the command 
    p = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()

    # Capture the stdout/stderr
    stdout = os.path.join(tmpdir, 'stdout.log.txt')
    with open(stdout, 'w') as fd: 
        fd.write(out.decode('utf-8'))

    stderr = os.path.join(tmpdir, 'stderr.log.txt')
    with open(stderr, 'w') as fd: 
        fd.write(err.decode('utf-8'))

        
    # Check the strace output 
    files = extract_files(strace_filename, includes) 

    return 


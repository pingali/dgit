#!/usr/bin/env python 
"""
This is the core module for manipulating the dataset metadata 
"""
import os, sys, copy, fnmatch, re, shutil 
import yaml, json, tempfile 
import webbrowser 
import subprocess, string, random 
import shelve, getpass
from datetime import datetime
from hashlib import sha256
import mimetypes
import platform
import uuid, shutil 
import boto3, glob2 
import subprocess 
from dateutil import parser 
from .config import get_config
from .aws import get_session 
from .plugins import get_plugin_mgr 
from .helper import bcolors, clean_str, cd 

def clean_name(n): 
    n = "".join([x if (x.isalnum() or x == "-") else "_" for x in n])    
    return n

def compute_sha256(filename):    
    h = sha256()
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
        temp.write(yaml.dump(package, default_flow_style=False).encode('utf-8'))
        temp.flush()
        EDITOR = os.environ.get('EDITOR','/usr/bin/vi')
        subprocess.call("%s %s" %(EDITOR,temp.name), shell=True)
        temp.seek(0)
        data = temp.read() 
        conf = yaml.load(data) 

    # Now store the package...
    (handle, filename) = tempfile.mkstemp()    
    with open(filename, 'w') as fd: 
        fd.write(json.dumps(conf, indent=4))

    print("Bootstrapping", filename) 

    return filename 

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
    filename = bootstrap_datapackage(repo)
    repomgr.add_files(key, [
        { 
            'relativepath': 'datapackage.json',
            'localfullpath': filename, 
        }
    ])

    os.unlink(filename) 
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


def add_files(args, targetdir, generator, script):
        
    files = []

    # get the directory 
    ts = datetime.now().isoformat()     
    
    for f in args: 
        relativepath = os.path.join(targetdir, os.path.basename(f))
        change = 'update' if basename in files else 'add'
        update = {
            'change': change,
            'type': 'data' if not script else 'script',
            'generator': True if (script and generator) else False,
            'uuid': str(uuid.uuid1()),
            'relativepath': relativepath, 
            'mimetypes': mimetypes.guess_type(f)[0],
            'content': open(f).read(512), 
            'sha256': compute_sha256(f),
            'ts': ts, 
            'localfullpath': f,
            'localrelativepath': relpath, 
        }

        print("Added change:", change, basename)
        files.append(update)             
        
    return files
    
def add(username, dataset, args,
        execute, generator,targetdir, 
        includes, script=False): 
    """
    Given a filename, prepare a manifest for each dataset.
    """

    mgr = get_plugin_mgr() 
    (repomanager, repo) = mgr.get_by_repo(username, dataset)
    if repo is None: 
        raise Exception("Invalid repo") 


    # Gather the files...
    if not execute: 
        files = add_files(args, generator, script) 
    else: 
        files = run_executable(repomanager, repo, 
                               args, includes)


    if files is not None and len(files) > 0: 

        # Copy the files 
        repomanager.add_files(repo, files) 

        # Update the package.json 
        repo = repomanager.lookup(key=repo)
        rootdir = repo['rootdir']
        with cd(rootdir): 
            datapath = "datapackage.json"
            package = json.loads(open(datapath).read()) 
            
            # Update the resources 
            for h in files: 
                found = False
                for i, r in  enumerate(package['resources']):
                    if h['relativepath'] == r['relativepath']: 
                        package['resources'][i] = h
                        found = True
                        break 
                if not found: 
                    package['resources'].append(h) 

            with open(datapath, 'w') as fd: 
                fd.write(json.dumps(package, indent=4))
        
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

    # Load the execution strace log 
    lines = open(filename).readlines() 

    # Extract only open files - whether for read or write. You often
    # want to capture the json/ini configuration file as well
    files = {}
    lines = [l.strip() for l in lines if 'open(' in l]
    for l in lines: 

        # Check both these formats...
        # 20826 open("/usr/lib/locale/locale-archive", O_RDONLY|O_CLOEXEC) = 3
        #[28940] access(b'/etc/ld.so.nohwcap', F_OK)      = -2 (No such file or directory)
        matchedfile = re.search('open\([b]["\'](.+?)["\']', l)
        if matchedfile is None: 
            matchedfile = re.search('open\("(.+?)\"', l)
            
        if matchedfile is None: 
            continue 

        matchedfile = matchedfile.group(1) 

        if os.path.exists(matchedfile) and os.path.isfile(matchedfile): 
            
            #print("Looking at ", matchedfile) 

            # Check what action is being performed on these 
            action = 'input' if 'O_RDONLY' in l else 'output'

            matchedfile = os.path.relpath(matchedfile, ".")
            #print("Matched file's relative path", matchedfile) 

            for i in includes: 
                if fnmatch.fnmatch(matchedfile, i):
                    if matchedfile not in files: 
                        files[matchedfile] = [action] 
                    else: 
                        if action not in files[matchedfile]: 
                            files[matchedfile].append(action) 

    # A single file may be opened and closed multiple times 

    if len(files) == 0: 
        print("No input or output files found that match pattern")
        return []

    print('We captured files that matched the pattern you specified.')
    print('Please select files to keep (press ENTER)')

    # Let the user have the final say on which files must be included.
    filenames = list(files.keys())
    filenames.sort() 
    with tempfile.NamedTemporaryFile(suffix=".tmp") as temp:
        temp.write(yaml.dump(filenames, default_flow_style=False).encode('utf-8'))
        temp.flush()
        EDITOR = os.environ.get('EDITOR','/usr/bin/vi')
        subprocess.call("%s %s" %(EDITOR,temp.name), shell=True)
        temp.seek(0)
        data = temp.read() 
        selected = yaml.load(data) 

    print("You selected", len(selected), "file(s)")
    if len(selected) == 0: 
        return []

    # Get the action corresponding to the selected files
    filenames = [f for f in filenames if f in selected] 

    # Now we know the list of files. Where should they go? 
    print('Please select target locations for the various directories we found')
    print('Please make sure you do not delete any rows or edit the keys.')
    input('(press ENTER)')
    prefixes = {} 
    for f in filenames: 
        dirname = os.path.dirname(f)
        if dirname == "":
            dirname = "."
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
                revised = {} 

            #print(list(revised.keys()))
            #print(list(prefixes.keys()))

            if set(list(revised.keys())) == set(list(prefixes.keys())):
                prefixes = revised 
                break 
            else: 
                print("Could not process edited file. Either some rows are missing or entry has YAML syntax errors")
                input("Press ENTER to continue")

    # Add the root directory back 
    if "." in prefixes: 
        prefixes[""] = prefixes["."]

    result = []
    ts = datetime.now().isoformat()     
    for f in filenames: 
        relativepath = prefixes[os.path.dirname(f)]
        if relativepath == ".": 
            relativepath = os.path.basename(f)
        else: 
            relativepath = os.path.join(relativepath, os.path.basename(f))

        result.append({
            "relativepath": relativepath, 
            'type': 'run-output',
            'actions': files[f],
            'uuid': str(uuid.uuid1()),
            'mimetypes': mimetypes.guess_type(f)[0],
            'content': open(f).read(512), 
            'sha256': compute_sha256(f),
            'ts': ts, 
            'localrelativepath': os.path.relpath(f, "."),
            "localfullpath": os.path.abspath(f),            
        })
        
    print(json.dumps(result, indent=4))
    return result

def find_executable_commitpath(repomanager, repo, args): 

    print("Finding executable commit path", args)
    # Find the first argument that is a file and is part of a repo
    for f in args: 
        if os.path.exists(f): 

            # Get full path (to get username)
            f = os.path.realpath(f) 

            # Try getting the permalink 
            (relpath, permalink) = repomanager.permalink(repo, f)
            if permalink is not None: 
                return (relpath, permalink)
    
            # Check if this part of system bin directories 
            if os.environ['HOME'] in f: 
                return (f, None) 
    
    return (None, None) 

def run_executable(repomanager, repo, 
                   args, includes): 
    """
    Run the executable and capture the input and output...
    """

    # Get platform information
    mgr = get_plugin_mgr() 
    repomgr = mgr.get(what='instrumentation', name='platform') 
    platform_metadata = repomgr.get_metadata()

    print("Obtaining Commit Information")
    (executable, commiturl) = \
            find_executable_commitpath(repomanager, repo, args) 

    # Create a local directory 
    tmpdir = tempfile.mkdtemp()

    # Construct the strace command
    print("Running the command")
    strace_filename = os.path.join(tmpdir,'strace.out.txt')
    cmd = ["strace.py", "-f", "-o", strace_filename, 
           "-s", "1024", "-q", "--"] + args 
    
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

    
    # Now insert the execution metadata 
    execution_metadata = { 
        'likely-executable': executable,
        'commit-path': commiturl, 
        'args': args,
    }
    execution_metadata.update(platform_metadata)

    for i in range(len(files)):
        files[i]['execution-details'] = execution_metadata

    return files 

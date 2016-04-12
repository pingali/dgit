#!/usr/bin/env python

import os, sys, re, unicodedata
import json, inspect 
import shelve
from hashlib import sha256
import subprocess, pipes
from datetime import datetime
import getpass
import uuid
import subprocess
from collections import OrderedDict

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        # print("Looking at ", key)
        if key in a:
            if isinstance(a[key], dict) and \
               isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            if isinstance(a[key], list) and \
               isinstance(b[key], list):
                a[key].extend(b[key])
            elif a[key] == b[key]:
                pass # same leaf value
            elif type(a[key]) == type(b[key]):
                a[key] = b[key]
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            # print("Adding new key", key)
            a[key] = b[key]
    return a

def find_executable_path(filename):
    cmd = ["/bin/which",filename]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    res = p.stdout.readlines()
    if len(res) == 0:
        return None

    path = res[0].decode('utf-8')
    return path.strip()

def parse_dataset_name(dataset):

    if dataset is None:
        return (None, None)

    if dataset.count("/") not in [1]:
        print("Valid dataset format is <user>/<name>")
        return (None, None)

    username = dataset.split("/")[0]
    dataset = dataset.split("/")[1]

    return (username, dataset)

def clean_args(args, execute):

    # Clean args
    args = list(args)
    if execute:
        filename = args[0]
        filename = find_executable_path(filename)
        if filename is None:
            print("Invalid executable path", args[0])
            return None

        args[0] = filename
    else:
        for i in range(len(args)):
            if "://" not in args[i]:
                args[i] = os.path.realpath(args[i])

    return args

def clean_str(s):

    for c in ['/', '\\','.',' ']:
        s = s.replace(c,'_')
    return s

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def clean_name(n):
    n = "".join([x if (x.isalnum() or x == "-") else "_" for x in n])
    return n

def compute_sha256(filename):
    """
    Try the library. If it doesnt work, use the command line..
    """
    try:
        h = sha256()
        fd = open(filename, 'rb')
        while True:
            buf = fd.read(0x1000000)
            if buf in [None, ""]:
                break
            h.update(buf.encode('utf-8'))
        fd.close()
        return h.hexdigest()
    except:
        output = run(["sha256sum", "-b", filename])
        return output.split(" ")[0]

def run(cmd):
    """
    Run a shell command
    """
    cmd = [pipes.quote(c) for c in cmd]
    cmd = " ".join(cmd)
    cmd += "; exit 0"
    # print("Running {} in {}".format(cmd, os.getcwd()))
    try:
        output = subprocess.check_output(cmd,
                                         stderr=subprocess.STDOUT,
                                         shell=True)
    except subprocess.CalledProcessError as e:
            output = e.output

    output = output.decode('utf-8')
    output = output.strip()
    return output

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore')
    value = value.decode('utf-8')
    value = re.sub(r'[^\w\s-]', '-', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

def log_action(func, result, *args, **kwargs):

    trigger = "unknown"
    # https://docs.python.org/3/library/inspect.html
    stack = inspect.stack() 
    for s in stack: 
        filename = s[1] 
        funcname = s[3] 
        if filename.endswith("bin/dgit"): 
            trigger = "user" 
        elif filename.endswith("dgitcore/api.py"):
            trigger = "api"
        elif filename.endswith("datasets/common.py") and funcname == "post": 
            trigger = "auto"
        else:
            continue
        break 
     
    # First, find the repo 
    repo = None         
    for a in args: 
        if a.__class__.__name__ == "Repo": 
            repo = a
            break
            
    if repo is None: 
        return 

    # Clean the args 
    cleaned_args = [str(a) for a in args if a != repo]
    cleaned_kwargs = OrderedDict([(str(k), str(v)) \
                                  for (k,v) in kwargs.items()])

    # Get platform information...
    from .plugins import plugins_get_mgr 
    mgr = plugins_get_mgr()
    repomgr = mgr.get(what='instrumentation', name='platform')
    platform = repomgr.get_metadata()
    
    absf = os.path.abspath(".") 
    (relpath, permalink) = repo.manager.permalink(repo, absf)
    
    # Defaults...
    maxlength = 2048
    funcname = func.__name__

    # Construct a record 
    record = OrderedDict([
        ('uuid', str(uuid.uuid1().hex)),
        ('username', repo.username),
        ('reponame', repo.reponame),
        ('trigger', trigger),
        ('action', funcname),
        ('ts', datetime.now().replace(microsecond=0).isoformat()),
        ('args', cleaned_args),
        ('kwargs', cleaned_kwargs),
        ('result', result),
        ('platform', platform),
        ('code', permalink)
    ])

    
    # Now append to the log file...
    logfile = os.path.join(repo.rootdir, '.dgit', 'log.json')
    try: 
        os.makedirs(os.path.dirname(logfile))
    except:
        pass 
        
    with open(logfile, 'a') as fd: 
        print(json.dumps(record), file=fd)

def log_repo_action(func): 
    """
    Log all repo actions to .dgit/log.json 
    """
        
    def inner(*args, **kwargs):
        result = func(*args, **kwargs)         
        log_action(func, result, *args, **kwargs)
        return result 
    return inner

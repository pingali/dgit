#!/usr/bin/env python 

import os, sys 
import json 
import shelve 
from datetime import datetime
import getpass 
from .config import get_state 
import uuid 
import subprocess 

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
            args[i] = os.path.abspath(args[i])
        
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

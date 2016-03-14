import os, sys, getpass, stat, glob, json, platform 
import subprocess, time
from collections import OrderedDict
from ..config import get_config
from ..plugins.common import get_plugin_mgr 

autofile = 'dgit.json' 

def find_executable_files(): 
    """
    Find max 5 executables that are responsible for this repo. 
    """
    files = glob.glob("*") + glob.glob("*/*") + glob.glob('*/*/*')
    files = filter(lambda f: os.path.isfile(f), files)
    executable = stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH    
    final = []
    for filename in files:
        if os.path.isfile(filename):
            st = os.stat(filename)
            mode = st.st_mode
            if mode & executable:
                final.append(filename) 
                if len(final) > 5: 
                    break 
    return final 

def init(force_init): 
    """
    Initialize a repo-specific configuration file to execute dgit
    """

    if os.path.exists(autofile) and not force_init: 
        try: 
            autooptions = json.loads(open(autofile).read())
            return autooptions 
        except: 
            print("Error in dgit.json configuration file")


    config = get_config() 
    mgr = get_plugin_mgr() 

    # Get the dataset name...
    username = getpass.getuser() 
    thisdir = os.path.abspath(os.getcwd())
    basename = os.path.basename(thisdir)
    dataset = "{}/{}" .format(username, basename) 

    # Get the default backend URL 
    keys = mgr.search('backend') 
    keys = keys['backend']     
    keys = [k for k in keys if k[0] != "local"]
    remoteurl = ""
    if len(keys) > 0: 
        backend = mgr.get_by_key('backend', keys[0])
        remoteurl = backend.url(username, basename) 

    
    autooptions = OrderedDict([
        ("dataset", dataset),
        ("remoteurl", remoteurl),
        ('tracking', OrderedDict([
            ('files', ['*.csv', '*.tsv', '*.txt','*.json']),
            ('scripts', find_executable_files())
        ]))
    ])

    keys = mgr.search('metadata') 
    keys = keys['metadata']     
    if len(keys) > 0: 
        domains = [] 
        for k in keys: 
            server = mgr.get_by_key('metadata', k)        
            domain = server.url.split("/")[2] 
            domains.append(domain)
    
        autooptions.update(OrderedDict([
            ('management', OrderedDict([
                ('servers', domains),
                ('preview', True),
                ('log-history', True),
                ('tab-diffs', True)
            ]))]))
    
    with open(autofile, 'w') as fd: 
        fd.write(json.dumps(autooptions, indent=4))

    
    if platform.system() == "Linux": 
        subprocess.call(["xdg-open", autofile])
        print("Please edit the options and rerun dgit auto")
        sys.exit() 

    return autooptions

def collect(force_init): 
    
    autooptions = init(force_init) 
    
    

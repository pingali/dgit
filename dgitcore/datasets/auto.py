import os, sys, getpass, stat, glob, json, platform 
import subprocess, time
from collections import OrderedDict
import fnmatch, re
from ..config import get_config
from ..plugins.common import get_plugin_mgr 
from .common import clone as common_clone, init as common_init, add_preview as common_add_preview 
from .files import add as files_add
from .history import get_history 
from .detect import get_schema 

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

def auto_init(autofile, force_init=False): 
    """
    Initialize a repo-specific configuration file to execute dgit
    """

    if os.path.exists(autofile) and not force_init: 
        try: 
            autooptions = json.loads(open(autofile).read())
            return autooptions 
        except: 
            print("Error in dgit.json configuration file")
            traceback.print_exc() 
            raise Exception("Invalid configuration file")

    config = get_config() 
    mgr = get_plugin_mgr() 

    print("No dgit repo-specific configuration file found. Creating one.")
    
    # Get the username
    username = getpass.getuser() 
    revised = input("Please specify username [{}]".format(username))
    if revised not in ["", None]: 
        username = revised 

    # Get the reponame
    thisdir = os.path.abspath(os.getcwd())
    reponame = os.path.basename(thisdir)    
    revised = input("Please specify repo name [{}]".format(reponame))
    if revised not in ["", None]: 
        reponame = revised 

    # Get the default backend URL     
    keys = mgr.search('backend') 
    keys = keys['backend']     
    keys = [k for k in keys if k[0] != "local"]
    remoteurl = ""
    backend = None 
    if len(keys) > 0: 
        backend = mgr.get_by_key('backend', keys[0])
        candidate = backend.url(username, reponame)
        revised = input("Please specify remote URL [{}]".format(candidate))
        if revised not in ["", None]: 
            remoteurl = candidate

    autooptions = OrderedDict([
        ("username", username),
        ("reponame", reponame),
        ("remoteurl", remoteurl),
        ("working-directory", "."),
        ('track' ,OrderedDict([
            ('includes', ['*.csv', '*.tsv', '*.txt','*.json']),
            ('excludes', ['.git', '.svn', os.path.basename(autofile)]),
        ])),
        ('import' ,OrderedDict([
            ('directory-mapping' ,OrderedDict([
                ('.', '')
            ]))
        ])),
    ])

    keys = mgr.search('metadata') 
    keys = keys['metadata']     
    if len(keys) > 0: 
        
        # => Select domains that be included.
        servers = [] 
        for k in keys: 
            server = mgr.get_by_key('metadata', k)        
            server = server.url.split("/")[2] 
            servers.append(server)
    
        # Specify what should be included 
        autooptions.update(OrderedDict([
            ('metadata-management', OrderedDict([
                ('servers', servers),
                ('include-code-history', find_executable_files()),
                ('include-preview', ['*.txt', '*.csv', '*.tsv']), 
                ('include-data-history', True),
                ('include-schema', ['*.csv', '*.tsv']),
                ('include-tab-diffs', ['*.csv', '*.tsv']),
            ]))]))
    
    with open(autofile, 'w') as fd: 
        fd.write(json.dumps(autooptions, indent=4))

    print("Generated/updated config file: {}".format(autofile))
    print("Please edit it and rerun dgit auto.")
    print("You could consider committing dgit.json to the code repository.")
        
    #if platform.system() == "Linux": 
    #    subprocess.call(["xdg-open", autofile])

    sys.exit() 


def auto_get_repo(autooptions, debug=False): 
    """
    Clone this repo if exists. Otherwise create one...
    """

    # plugin manager
    mgr = get_plugin_mgr() 

    # get the repo manager 
    repomgr = mgr.get(what='repomanager', name='git') 

    repo = None

    try: 
        if debug:
            print("Looking repo")
        repo = repomgr.lookup(username=autooptions['username'],
                              reponame=autooptions['reponame'])
    except: 
        # Clone the repo 
        try: 

            url = autooptions['remoteurl']
            if debug:
                print("Doesnt exist. trying to clone: {}".format(url))
            common_clone(url)        
            repo = remgr.lookup(username=autooptions['username'],
                                reponame=autooptions['reponame'])
            if debug: 
                print("Cloning successful")
        except:
            yes = input("Repo doesnt exists and could not clone. Should I create one? [yN]") 
            if yes == 'y': 
                setup = "git"
                if autooptions['remoteurl'].startswith('s3://'):
                    setup = 'git+s3'                 
                repo = common_init(username=autooptions['username'],
                                   reponame=autooptions['reponame'],
                                   setup=setup, 
                                   force=True)
                if debug: 
                    print("Successfully inited repo") 

    print("Adding auto options ", autooptions) 
    repo.options = autooptions 

    return repo
                

def get_files_to_commit(autooptions): 
    """
    Look through the local directory to pick up files to check
    """
    workingdir = autooptions['working-directory']
    includes = autooptions['track']['includes'] 
    excludes = autooptions['track']['excludes'] 

    # transform glob patterns to regular expressions
    includes = r'|'.join([fnmatch.translate(x) for x in includes])
    excludes = r'|'.join([fnmatch.translate(x) for x in excludes]) or r'$.'

    matched_files = []
    for root, dirs, files in os.walk(workingdir):

        # exclude dirs
        # dirs[:] = [os.path.join(root, d) for d in dirs]
        dirs[:] = [d for d in dirs if not re.match(excludes, d)]

        # exclude/include files
        files = [f for f in files if not re.match(excludes, f)]
        files = [f for f in files if re.match(includes, f)]
        files = [os.path.join(root, f) for f in files]

        matched_files.extend(files)

    return matched_files

def find_matching_files(repo, includes): 
  
    files = [f['relativepath'] for f in repo.package['resources']]
    includes = r'|'.join([fnmatch.translate(x) for x in includes])
    files = [f for f in files if re.match(includes, os.path.basename(f))]
    return files 

def auto_add(repo, autooptions, files): 
    """
    Cleanup the paths and add 
    """
    # Get the mappings and keys. 
    mapping = { ".": "" } 
    if (('import' in autooptions) and 
        ('directory-mapping' in autooptions['import'])): 
        mapping = autooptions['import']['directory-mapping']
        
    # Apply the longest prefix first...
    keys = mapping.keys()     
    keys = sorted(keys, key=lambda k: len(k), reverse=True)

    params = []
    for f in files:         
        
        # Find the destination
        relativepath = f
        for k in keys: 
            v = mapping[k] 
            if f.startswith(k + "/"): 
                print("Replacing ", k)
                relativepath = f.replace(k + "/", v)
                break 

        # Now add to repository 
        files_add(repo=repo, 
            args=[f],
            targetdir=os.path.dirname(relativepath))


def collect(autofile, force_init): 
    
    # Gather the repo name...
    autooptions = auto_init(autofile, force_init) 

    # Load repo from the dgit.json file 
    repo = auto_get_repo(autooptions)
    
    # find all the files that must be collected
    files = get_files_to_commit(autooptions) 

    # Add the files to the repo
    auto_add(repo, autooptions, files) 

    # Add metadata information 
    history = None 
    if 'metadata-management' in autooptions: 
        metadata = autooptions['metadata-management']
        
        # Include history of the data repo 
        include_data_history = metadata.get('include-data-history',False)
        if include_data_history: 
            history = get_history(repo.rootdir) 
            print("Got history") 
        
        # Include 
        include_schema = metadata.get('include-schema',False)
        if include_schema: 
            files = find_matching_files(repo, metadata['include-schema'])

        # Include preview 
        include_preview = metadata.get('include-preview',False)
        if include_preview: 
            files = find_matching_files(repo, metadata['include-preview'])
            print("Including for preview", files)

    package = repo.package
    package['history'] = history 


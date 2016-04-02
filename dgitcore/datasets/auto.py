import os, sys, getpass, stat, glob, json, platform
import subprocess, time, traceback
from collections import OrderedDict
import fnmatch, re
from ..config import get_config
from ..plugins.common import plugins_get_mgr
from .common import clone as common_clone, init as common_init, post as common_post
from .files import add as files_add
from .history import get_history
from .detect import get_schema
from datetime import datetime

#####################################################
# Exports
#####################################################

__all__ = ['auto_update', 'auto_init', 'auto_get_repo']

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

    Parameters
    ----------

    autofile: Repo-specific configuration file (dgit.json)
    force_init: Flag to force to re-initialization of the configuration file

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
    pluginmgr = plugins_get_mgr()

    print("Repo configuration file missing or corrupted. Creating one")
    print("Let us know a few details about your data repository")

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
    keys = pluginmgr.search('backend')
    keys = keys['backend']
    keys = [k for k in keys if k[0] != "local"]
    remoteurl = ""
    backend = None
    if len(keys) > 0:
        backend = pluginmgr.get_by_key('backend', keys[0])
        candidate = backend.url(username, reponame)
        revised = input("Please specify remote URL [{}]".format(candidate))
        if revised in ["", None]:
            remoteurl = candidate
        else:
            remoteurl = revised

    # Get title...
    title = ""
    while title == "":
        title = input("One line summary of your repo:")
        if title == "":
            print("The repo requires a one line summary")
        else:
            break

    # Get description
    description = ""
    while description == "":
        description = input("Detailed description:")
        if description == "":
            print("The repo requires some text as well")
        else:
            break

    autooptions = OrderedDict([
        ("username", username),
        ("reponame", reponame),
        ("remoteurl", remoteurl),
        ("title", title),
        ("description", description),
        ("working-directory", "."),
        ('track' ,OrderedDict([
            ('includes', ['*.csv', '*.tsv', '*.txt','*.json', '*.xlsx', "*.sql", "*.hql"]),
            ('excludes', ['.git', '.svn', os.path.basename(autofile)]),
        ])),
        ('auto-push', False),
        ('pipeline' ,OrderedDict([])),
        ('import' ,OrderedDict([
            ('directory-mapping' ,OrderedDict([
                ('.', '')
            ]))
        ])),
        ('dependencies' ,OrderedDict([]))
    ])

    # Gather options from each of the enabled plugins
    for p in ['validator', 'transformer']:
        keys = pluginmgr.search(p)
        keys = keys[p]
        options = OrderedDict()
        for k in keys:
            if k.name in options:
                continue
            mgr = pluginmgr.get_by_key(p, k)
            options[k.name] = mgr.autooptions()
        autooptions[p] = options

    keys = pluginmgr.search('metadata')
    keys = keys['metadata']
    if len(keys) > 0:

        # => Select domains that be included.
        servers = []
        for k in keys:
            server = pluginmgr.get_by_key('metadata', k)
            server = server.url.split("/")[2]
            servers.append(server)

        # Specify what should be included. Some of these should go ino
        # the metadata modules

        autooptions.update(OrderedDict([
            ('metadata-management', OrderedDict([
                ('servers', servers),
                ('include-code-history', find_executable_files()),
                ('include-preview', OrderedDict([
                    ('length', 512),
                    ('files', ['*.txt', '*.csv', '*.tsv'])
                    ])),
                ('include-data-history', True),
                ('include-validation', True),
                ('include-dependencies', True),
                ('include-schema', ['*.csv', '*.tsv']),
                ('include-tab-diffs', ['*.csv', '*.tsv']),
                ('include-platform', True),
            ]))]))

    with open(autofile, 'w') as fd:
        fd.write(json.dumps(autooptions, indent=4))

    print("")
    print("Updated dataset specific config file: {}".format(autofile))
    print("Please edit it and rerun dgit auto.")
    print("Tip: Consider committing dgit.json to the code repository.")

    #if platform.system() == "Linux":
    #    subprocess.call(["xdg-open", autofile])

    sys.exit()


def auto_get_repo(autooptions, debug=False):
    """
    Automatically get repo

    Parameters
    ----------

    autooptions: dgit.json content

    """

    # plugin manager
    pluginmgr = plugins_get_mgr()

    # get the repo manager
    repomgr = pluginmgr.get(what='repomanager', name='git')

    repo = None

    try:
        if debug:
            print("Looking repo")
        repo = repomgr.lookup(username=autooptions['username'],
                              reponame=autooptions['reponame'])
    except:
        # Clone the repo
        try:
            print("Checking and cloning if the dataset exists on backend")
            url = autooptions['remoteurl']
            if debug:
                print("Doesnt exist. trying to clone: {}".format(url))
            common_clone(url)
            repo = repomgr.lookup(username=autooptions['username'],
                                  reponame=autooptions['reponame'])
            if debug:
                print("Cloning successful")
        except:
            # traceback.print_exc()
            yes = input("Repo doesnt exist. Should I create one? [yN]")
            if yes == 'y':
                setup = "git"
                if autooptions['remoteurl'].startswith('s3://'):
                    setup = 'git+s3'
                repo = common_init(username=autooptions['username'],
                                   reponame=autooptions['reponame'],
                                   setup=setup,
                                   force=True,
                                   options=autooptions)

                if debug:
                    print("Successfully inited repo")
            else:
                raise Exception("Cannot load repo")

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

    count = 0
    params = []
    for f in files:

        # Find the destination
        relativepath = f
        for k in keys:
            v = mapping[k]
            if f.startswith(k + "/"):
                #print("Replacing ", k)
                relativepath = f.replace(k + "/", v)
                break

        # Now add to repository
        count += files_add(repo=repo,
                           args=[f],
                           targetdir=os.path.dirname(relativepath))

    return count

def auto_update(autofile, force_init):

    # Gather the repo name...
    autooptions = auto_init(autofile, force_init)

    # Load repo from the dgit.json file
    repo = auto_get_repo(autooptions)

    # find all the files that must be collected
    files = get_files_to_commit(autooptions)

    if len(files) > 10:
        print("Large number ({}) files are being added.".format(len(files)))
        proceed = input("Do you wish to proceed? [yN] ")
        if proceed != 'y':
            return

    # Add the files to the repo
    count = auto_add(repo, autooptions, files)
    if count == 0:
        print("There is no change in repo")
    else:
        # Commit the changes
        ts = datetime.now().isoformat()
        message = input("Quick summary of changes? ")
        if message in [None, '']:
            message = "Automatic commit on {}".format(ts)
        repo.run('commit', ['-a', '-m', message])

    # Add the dgit.json as a note in the dgit_config namespace
    autofile = os.path.abspath(autofile)
    repo.run('notes', ['--ref', 'dgit_config',
                       'add',
                       '-F', autofile,
                       'HEAD'])

    # Push notes and commits to server
    print("Sync'ing with backend")
    if 'auto-push' in autooptions and autooptions['auto-push']:
        repo.run('push', ['origin', "refs/notes/*"])
        repo.run('push', ['origin', 'master'])

    # Collect all the metadata and post
    common_post(repo)

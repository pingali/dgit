#!/usr/bin/env python
"""
This is the core module for manipulating the dataset metadata
"""
import os, sys, copy, fnmatch, re, shutil
import yaml, json, tempfile
import webbrowser
from collections import OrderedDict
import subprocess, string, random, pipes
import getpass
from datetime import datetime
from hashlib import sha256
import mimetypes
import platform
import uuid, shutil
from dateutil import parser
from ..config import get_config
from ..plugins.common import plugins_get_mgr
from ..helper import bcolors, clean_str, cd, compute_sha256, run, clean_name
from .detect import get_schema

#####################################################
# Exports
#####################################################

__all__ = ['add']

############################################################
# Add files and links...
############################################################
def annotate_record(h):

    # Insert defaults
    defaults = OrderedDict([
        ('type', 'data'),
        ('generator', False),
        ('source', None)
    ])

    for k, v in defaults.items():
        if k not in h:
            h[k] = v

    # Update UUID and other detauls
    f = h['localfullpath']
    h.update(OrderedDict([
        ('mimetypes', mimetypes.guess_type(f)[0]),
        ('sha256', compute_sha256(f))
    ]))

    return h

def add_link(f):
    update = OrderedDict([
        ('type', 'data'),
        ('generator', False),
        ('relativepath', f),
        ('mimetypes', ""),
        ('content', ""),
        ('sha256', ""),
        ('localfullpath', None),
        ('localrelativepath', None)
    ])

    return (f, update)

def add_file_normal(f, targetdir, generator,script, source):
    """
    Add a normal file including its source
    """

    basename = os.path.basename(f)
    if targetdir != ".":
        relativepath = os.path.join(targetdir, basename)
    else:
        relativepath = basename

    relpath = os.path.relpath(f, os.getcwd())
    filetype = 'data'
    if script:
        filetype = 'script'
        if generator:
            filetype = 'generator'

    update = OrderedDict([
        ('type', filetype),
        ('generator', generator),
        ('relativepath', relativepath),
        ('content', ""),
        ('source', source),
        ('localfullpath', f),
        ('localrelativepath', relpath)
    ])

    update = annotate_record(update)

    return (basename, update)


def add_files(args, targetdir, generator, source, script):

    seen = []
    files = []
    for f in args:
        # print("Looking at", f)
        if "://" not in f:
            (base, update) = add_file_normal(f=f,
                                             targetdir=targetdir,
                                             generator=generator,
                                             script=script,
                                             source=source)
        else:
            print("Adding special file")
            (base, update) = add_link(f)

        if base not in seen:
            update['change'] = 'add'
            ts = datetime.now()
            seen.append(base)
        else:
            update['change'] = 'update'
            ts = os.path.getmtime(f)
            ts = datetime.fromtimestamp(ts)
        update['ts'] = ts.isoformat()
        files.append(update)

    return files

###################################################################
# Gather files from execution of the scripts
###################################################################

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
                    # Exclude python libraries
                    if 'site-packages' in matchedfile:
                        continue
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

        result.append(OrderedDict([
            ('relativepath', relativepath),
            ('type', 'run-output'),
            ('actions', files[f]),
            ('mimetypes', mimetypes.guess_type(f)[0]),
            ('content', open(f).read(512)),
            ('sha256', compute_sha256(f)),
            ('ts', ts),
            ('localrelativepath', os.path.relpath(f, ".")),
            ('localfullpath', os.path.abspath(f)),
        ]))

    print(json.dumps(result, indent=4))
    return result

def find_executable_commitpath(repo, args):

    print("Finding executable commit path", args)
    # Find the first argument that is a file and is part of a repo
    for f in args:
        if os.path.exists(f):

            # Get full path (to get username)
            f = os.path.realpath(f)

            # Try getting the permalink
            (relpath, permalink) = repo.manager.permalink(repo, f)
            if permalink is not None:
                return (relpath, permalink)

            # Check if this part of system bin directories
            if os.environ['HOME'] in f:
                return (f, None)

    return (None, None)

def run_executable(repo, args, includes):
    """
    Run the executable and capture the input and output...
    """

    # Get platform information
    mgr = plugins_get_mgr()
    repomgr = mgr.get(what='instrumentation', name='platform')
    platform_metadata = repomgr.get_metadata()

    print("Obtaining Commit Information")
    (executable, commiturl) = \
            find_executable_commitpath(repo, args)

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
        'likelyexecutable': executable,
        'commitpath': commiturl,
        'args': args,
    }
    execution_metadata.update(platform_metadata)

    for i in range(len(files)):
        files[i]['execution_metadata'] = execution_metadata

    return files

################################################
# Main function
################################################
def add(repo, args, targetdir,
        execute=False, generator=False,
        includes=[], script=False,
        source=None):
    """
    Add files to the repository by explicitly specifying them or by
    specifying a pattern over files accessed during execution of an
    executable.

    Parameters
    ----------

    repo: Repository

    args: files or command line
         (a) If simply adding files, then the list of files that must
         be added (including any additional arguments to be passed to
         git
         (b) If files to be added are an output of a command line, then
         args is the command lined
    targetdir: Target directory to store the files
    execute: Args are not files to be added but scripts that must be run.
    includes: patterns used to select files to
    script: Is this a script?
    generator: Is this a generator
    source: Link to the original source of the data

    """

    # Gather the files...
    if not execute:
        files = add_files(args=args,
                          targetdir=targetdir,
                          source=source,
                          script=script,
                          generator=generator)
    else:
        files = run_executable(repo, args, includes)

    if files is None or len(files) == 0:
        return repo


    # Update the repo package but with only those that have changed.

    filtered_files = []
    package = repo.package
    for h in files:
        found = False
        for i, r in  enumerate(package['resources']):
            if h['relativepath'] == r['relativepath']:
                found = True
                if h['sha256'] == r['sha256']:
                    change = False
                    for attr in ['source']:
                        if h[attr] != r[attr]:
                            r[attr] = h[attr]
                            change = True
                    if change:
                        filtered_files.append(h)
                    continue
                else:
                    filtered_files.append(h)
                    package['resources'][i] = h
                break
        if not found:
            filtered_files.append(h)
            package['resources'].append(h)

    if len(filtered_files) == 0:
        return 0

    # Copy the files
    repo.manager.add_files(repo, filtered_files)

    # Write to disk...
    rootdir = repo.rootdir
    with cd(rootdir):
        datapath = "datapackage.json"
        with open(datapath, 'w') as fd:
            fd.write(json.dumps(package, indent=4))

    return len(filtered_files)


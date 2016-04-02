#!/usr/bin/env python

import os, sys
import json
import messytables
import subprocess
from dgitcore.helper import cd
from dgitcore.plugins.instrumentation import InstrumentationBase
from dgitcore.config import get_config


def run(cmd):
    output = subprocess.check_output(cmd,
                                     stderr=subprocess.STDOUT,
                                     shell=True)
    output = output.decode('utf-8')
    output = output.strip()
    return output

def repo_origin(filename, what=['Push  URL']):

    with cd(os.path.dirname(filename)):
        cmd = "git remote show origin"
        output = run(cmd)
        #* remote origin
        #Fetch URL: git@github.com:jaredpar/VsVim.git
        #Push  URL: git@github.com:jaredpar/VsVim.git
        #HEAD branch: master
        #Remote branches:

        response = {}
        output = output.split("\n")
        output = output[1:]
        for o in output:
            for w in what:
                if w in o:
                    response[w] = o[o.index(":")+1:]

    return response

def repo_remote_url(filename):

    with cd(os.path.dirname(filename)):
        cmd = "git config --get remote.origin.url"
        output = run(cmd)
        return {'remote.origin.url': output.strip()}

def executable_commit(filename,
                      what=['commit', 'username', 'useremail', 'date']):
    mapping = {
        'commit': '%H',
        'username': '%cn',
        'useremail': '%ce',
        'date': '%cd'
    }

    missing = [mapping[w] for w in what if w not in mapping]
    if len(missing) > 0:
        print("Cannot gather commit attributes of executable", missing)
        raise Exception("Invalid specification")

    codes = ",".join([mapping[w] for w in what if w in mapping])

    with cd(os.path.dirname(filename)):
        cmd = 'git log -n 1  --date=iso --pretty="%s" -- %s ' %(codes, filename)
        output = run(cmd)
        output = output.strip()
        output = output.split(",")
        return {what[i]: output[i] for i in range(len(what))}

    return {}

def executable_repopath(filename):

    with cd(os.path.dirname(filename)):
        cmd = 'git rev-parse --show-prefix'
        output = run(cmd)
        output = output.strip()
        return {
            'path': os.path.join(output, os.path.basename(filename))
        }

def executable_filetype(filename):

    with cd(os.path.dirname(filename)):
        cmd = '/usr/bin/file ' + filename
        output = run(cmd)
        output = output.strip()
        output = output[output.index(":")+1:]
        return {
            'filetype': output
        }

def get_metadata(args):
    filename = args[0]
    metadata = {'cmd': ' '.join(args) }
    metadata.update(repo_remote_url(filename))
    metadata.update(executable_commit(filename))
    metadata.update(executable_repopath(filename))
    metadata.update(executable_filetype(filename))
    return metadata

class ExecutableInstrumentation(InstrumentationBase):
    """Instrumentation to extract executable related summaries such as the git commit, nature of executable, parameters etc.
    """

    def __init__(self):
        super(ExecutableInstrumentation, self).__init__('executable',
                                                        'v0',
                                                        "Executable analysis")

    def update(self, config):
        if 'executables' in config:
            for i in range(len(config['executables'])):
                args = config['executable'][i]['args']
                metadata = get_metdata(args)
                config['executable'][i].update(metadata)

        return config

def setup(mgr):

    obj = ExecutableInstrumentation()
    mgr.register('instrumentation', obj)

if __name__ == "__main__":

    viz = '/home/pingali/analytics/politics/bin/mumbai-visualize.py'
    response = run_executable([viz])
    print(json.dumps(response, indent=4))

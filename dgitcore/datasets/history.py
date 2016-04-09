#!/usr/bin/env python

import os, sys, parse, shutil 
import traceback 
import subprocess, pipes
from collections import OrderedDict
import tempfile 
import json
import daff
from ..helper import run, cd
from ..plugins.common import plugins_get_mgr

def get_change():

    cmd = ["git", "log", "--all", "--branches", "--numstat"]
    output = run(cmd)

    #commit 6a9c9e0db3869df252910dbcdae8cc97fa0291e4
    #Author: Venkata Pingali <pingali@gmail.com>
    #Date:   Fri Feb 26 17:07:50 2016 +0530
    #
    #    1. Simplify the SQL and post-processing scripts
    #
    #5       3       performance/bin/analyze
    #21      20      performance/bin/gather-rawdata.sh
    #


    changes = {}
    h = None
    lines = output.split("\n")
    for l in lines:
        #if l.startswith("Date") or l.startswith("Author"):
        #    continue
        r =  parse.parse("commit {commit}", l)
        if r is not None:
            if h is not None:
                changes[h['abbrev-commit']] = h
            h = {
                'abbrev-commit': r['commit'][:7],
                'commit': r['commit'],
                'changes': []
            }
            continue

        r =  parse.parse("{added}\t{deleted}\t{path}", l)
        if r is not None:
            h['changes'].append({
                'added': r['added'],
                'deleted': r['deleted'],
                'path': r['path']
            })
            continue

        # print("Skipping ", l)

    if h is not None:
        changes[h['abbrev-commit']] = h

    return changes

def get_tree(gitdir="."):
    """
    Get the commit history for a given dataset
    """

    cmd = ["git", "log", "--all", "--branches", '--pretty=format:{  "commit": "%H",  "abbreviated_commit": "%h",  "tree": "%T",  "abbreviated_tree": "%t",  "parent": "%P",  "abbreviated_parent": "%p",  "refs": "%d",  "encoding": "%e",  "subject": "%s", "sanitized_subject_line": "%f",  "commit_notes": "",  "author": {    "name": "%aN",    "email": "%aE",    "date": "%ai"  },  "commiter": {    "name": "%cN",    "email": "%cE",    "date": "%ci"  }},']

    output = run(cmd)
    lines = output.split("\n")

    content = ""
    history = []
    for l in lines:
        try:
            revisedcontent = content + l
            if revisedcontent.count('"') % 2 == 0:
                j = json.loads(revisedcontent[:-1])
                if "Notes added by" in j['subject']:
                    content = ""
                    continue
                history.append(j)
                content = ""
            else:
                content = revisedcontent
        except Exception as e:
            print("Error while parsing record")
            print(revisedcontent)
            content = ""

    # Order by time. First commit first...
    history.reverse()

    #
    changes = get_change()

    for i in range(len(history)):
        abbrev_commit = history[i]['abbreviated_commit']
        if abbrev_commit not in changes:
            raise Exception("Missing changes for " + abbrev_commit)

        history[i]['changes'] = changes[abbrev_commit]['changes']


    return history

def associate_branches(history):

    # print(json.dumps(history, indent=4))

    branches = {}

    for i in range(len(history)):

        h = history[i]
        # print(json.dumps(h, indent=4))
        parent = h['parent']
        commit = h['commit']
        refs = h['refs']
        author = h['author']['name']
        timestamp = h['author']['date']
        # print("{}/{}/{}/{}".format(commit,parent,refs,author))

        d = {
            'commit': commit,
            'timestamp': timestamp,
            'author': author,
        }
        if parent == "":
            d.update({
                'parent-branches': [],
                'branch': 'master',
                'action': 'commit',
                'children': []
            })
        elif " " in parent:
            # Merge action
            parent = parent.split(" ")
            d.update({
                'parent-branches': [branches[parent[0]]['branch'],
                                     branches[parent[1]]['branch']],
                'branch': branches[parent[0]]['branch'],
                'action': 'merge',
                'children': []
            })
            branches[parent[0]]['children'].append(commit)
            branches[parent[1]]['children'].append(commit)
        elif ((refs == "") or (refs != "" and 'tag' in refs)) \
             and parent in branches:
            d.update({
                'parent-branches': [branches[parent]['branch']],
                'branch': branches[parent]['branch'],
                'action': 'commit',
                'children': []
            })
            branches[parent]['children'].append(commit)

        elif refs != "" and parent in branches :
            # print("REF", refs)
            # Clean refs...
            refs = refs.replace("(","")
            refs = refs.replace(")","")
            refs = refs.split(",")
            # print("REF", refs)
            refs = [r.strip() for r in refs]
            # refs = [r.replace("origin/","") for r in refs]
            d.update({
                'parent-branches': [branches[parent]['branch']],
                'branch': refs[-1],
                'action': 'branch',
                'children': []
            })
        else:
            raise Exception("Could not construct tree")

        branches[commit] = d

        # print("updated branches with", d)

    for i in range(len(history)):
        commit = history[i]['commit']
        if commit not in branches:
            raise Exception("Missing branch information for " + commit)
        history[i]['action'] = branches[commit]['action']
        history[i]['branch'] = branches[commit]['branch']
        history[i]['parent-branches'] = branches[commit]['parent-branches']

    # print(json.dumps(branches, indent=4))
    #values = branches.values()
    #values = sorted(values, key=lambda k: k['timestamp'], reverse=True)
    #print(json.dumps(values, indent=4))

    return history


def get_diffs(history):
    """
    Look at files and compute the diffs intelligently
    """

    # First get all possible representations
    mgr = plugins_get_mgr() 
    keys = mgr.search('representation')['representation']
    representations = [mgr.get_by_key('representation', k) for k in keys]

    for i in range(len(history)):
        if i+1 > len(history) - 1:
            continue

        prev = history[i]
        curr = history[i+1]

        #print(prev['subject'], "==>", curr['subject'])
        #print(curr['changes'])
        for c in curr['changes']:
            
            path = c['path']

            # Skip the metadata file
            if c['path'].endswith('datapackage.json'): 
                continue 

            # Find a handler for this kind of file...
            handler = None 
            for r in representations: 
                if r.can_process(path): 
                    handler = r 
                    break 
            
            if handler is None: 
                continue 

            # print(path, "being handled by", handler)

            v1_hex = prev['commit']
            v2_hex = curr['commit']

            temp1 = tempfile.mkdtemp(prefix="dgit-diff-") 
            
            try: 
                for h in [v1_hex, v2_hex]: 
                    filename = '{}/{}/checkout.tar'.format(temp1, h)
                    try:
                        os.makedirs(os.path.dirname(filename))
                    except:
                        pass 
                    extractcmd = ['git', 'archive', '-o', filename, h, path]
                    output = run(extractcmd)
                    if 'fatal' in output: 
                        raise Exception("File not present in commit") 
                    with cd(os.path.dirname(filename)): 
                        cmd = ['tar', 'xvf', 'checkout.tar']
                        output = run(cmd) 
                        if 'fatal' in output: 
                            print("Cleaning up - fatal 1", temp1)
                            shutil.rmtree(temp1)
                            continue 

                # Check to make sure that 
                path1 = os.path.join(temp1, v1_hex, path) 
                path2 = os.path.join(temp1, v2_hex, path) 
                if not os.path.exists(path1) or not os.path.exists(path2): 
                    # print("One of the two output files is missing") 
                    shutil.rmtree(temp1)
                    continue 

                #print(path1, path2) 

                # Now call the handler
                diff = handler.get_diff(path1, path2)

                #print("Inserting diff")
                c['diff'] = diff

            except Exception as e: 
                # traceback.print_exc() 
                #print("Cleaning up - Exception ", temp1)
                shutil.rmtree(temp1)

def get_history(gitdir="."):

    with cd(gitdir):
        history = get_tree()
        history = associate_branches(history)

    return history


if __name__ == "__main__":

    history = get_history()
    print(json.dumps(history, indent=4))


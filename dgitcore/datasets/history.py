#!/usr/bin/env python

import os, sys, parse
import subprocess, pipes
from collections import OrderedDict
import json
import daff
from ..helper import run, cd

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

def parse_diff(diff):
    #http://dataprotocols.org/tabular-diff-format/
    #@@ 	The header row, giving column names.

    #! 	The schema row, given column differences.
    #+++ 	An inserted row (present in REMOTE, not present in LOCAL).
    #--- 	A deleted row (present in LOCAL, not present in REMOTE).
    #-> 	A row with at least one cell modified cell. -->, --->, ----> etc. have the same meaning.
    #Blank 	A blank string or NULL marks a row common to LOCAL and REMOTE, given for context.
    #... 	Declares that rows common to LOCAL and REMOTE are being skipped.
    #+ 	A row with at least one added cell.
    #: 	A reordered row.

    #Reference: Schema row tags
    #Symbol 	Meaning
    #+++ 	An inserted column (present in REMOTE, not present in LOCAL).
    #--- 	A deleted column (present in LOCAL, not present in REMOTE).
    #(<NAME>) 	A renamed column (the name in LOCAL is given in parenthesis, and the name in REMOTE will be in the header row).
    #Blank 	A blank string or NULL marks a column common to LOCAL and REMOTE, given for context.
    #... 	Declares that columns common to LOCAL and REMOTE are being skipped.
    #: 	A reordered column.

    summary = OrderedDict([
        ('schema', OrderedDict([
            ("+++", ["New column", 0]),
            ("---", ["Deleted column", 0]),
            ("()", ["Renamed column",0]),
            (":", ["Rordered column",0])
        ])),
        ('data',OrderedDict([
            ("+++", ["New row",0]),
            ("---", ["Deleted row", 0]),
            ("+", ["Atleast one cell change",0]),
            (":", ["Reordered row",0])
        ]))
    ])

    diff = diff.getData()
    # [['!', '', '', '+++'], ['@@', 'State', 'City', 'Metro'], ['+', 'KA', 'Bangalore', '1'], ['+', 'MH', 'Mumbai', '2'], ['+++', 'KL', 'Kottayam', '0']]
    # print(diff)

    start = 0
    if diff[0][0] == "!":
        start = 1
        # Schema changes
        for col in diff[0][1:]:
            if "(" in col:
                col = "()"
            if col in summary['schema']:
                summary['schema'][col][1] += 1

    start += 1 # skip header row...
    for row in diff[start:]:
        if row[0] in summary['data']:
            summary['data'][row[0]][1] += 1

    return summary

def get_diffs(history):
    """
    Look at csv/tsv and compute the diffs intelligently
    """

    for i in range(len(history)):
        if i+1 > len(history) - 1:
            continue

        prev = history[i]
        curr = history[i+1]

        #print(prev['subject'], "==>", curr['subject'])
        #print(curr['changes'])
        for c in curr['changes']:

            path = c['path'].lower()
            delimiter = "," if path.endswith("csv") else "\t"

            if path.endswith('tsv') or path.endswith('csv'):

                # print(c['path'])

                v1_hex = prev['commit']
                v2_hex = curr['commit']

                # Read the content of the files
                cmd1 = ["git", "show", "{}:{}".format(v1_hex, c['path'])]
                csv1_raw = run(cmd1)
                cmd2 = ["git", "show", "{}:{}".format(v2_hex, c['path'])]
                csv2_raw = run(cmd2)

                if 'fatal' in csv1_raw or 'fatal' in csv2_raw:
                    continue

                #print(v1_hex)
                #print("csv1_raw", csv1_raw)
                #print(v2_hex)
                #print("csv2_raw", csv2_raw)

                # Generate simple list of lists that can be diffd using daff
                csv1 = csv1_raw.split("\n")
                csv1 = [c.split(delimiter) for c in csv1]
                csv2 = csv2_raw.split("\n")
                csv2 = [c.split(delimiter) for c in csv2]

                table1 = daff.PythonTableView(csv1)
                table2 = daff.PythonTableView(csv2)

                alignment = daff.Coopy.compareTables(table1,table2).align()

                data_diff = []
                table_diff = daff.PythonTableView(data_diff)

                flags = daff.CompareFlags()
                highlighter = daff.TableDiff(alignment,flags)
                highlighter.hilite(table_diff)

                # Parse the differences
                diff = parse_diff(table_diff)

                c['diff'] = diff

def get_history(gitdir="."):

    with cd(gitdir):
        history = get_tree()
        history = associate_branches(history)

    return history


if __name__ == "__main__":

    history = get_history()
    print(json.dumps(history, indent=4))


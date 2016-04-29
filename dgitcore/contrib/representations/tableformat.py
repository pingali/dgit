#!/usr/bin/env python

import os, sys, glob2
from collections import OrderedDict
from dgitcore.plugins.representation import RepresentationBase
from dgitcore.config import get_config
from dgitcore.helper import cd
import daff 
from messytables import type_guess, \
  types_processor, headers_guess, headers_processor, \
  offset_processor, any_tableset

class TableRepresentation(RepresentationBase):
    """
    Process tables in various forms

    Parameters
    ----------
    """
    def __init__(self):
        self.enable = 'y'
        super(TableRepresentation, self).__init__('table-representation',
                                               'v0',
                                               "Compute schema and diffs for csv/tsv/xls")

    def config(self, what='get', params=None):

        if what == 'get':
            return {
                'name': 'table-representation',
                'nature': 'representation',
                'variables': [],
            }

    def can_process(self, filename): 
        
        for ext in ['csv', 'tsv', 'xls']: 
            if filename.lower().endswith(ext):
                return True 
        return False 

    def read_file(self, filename): 
        """
        Guess the filetype and read the file into row sets
        """
        #print("Reading file", filename)

        try:
            fh = open(filename, 'rb')
            table_set = any_tableset(fh) # guess the type...
        except:
            #traceback.print_exc()
            # Cannot find the schema.
            table_set = None
            
        return table_set
        
    def get_schema(self, filename):
        """
        Guess schema using messytables
        """
        table_set = self.read_file(filename)
            
        # Have I been able to read the filename
        if table_set is None: 
            return [] 

        # Get the first table as rowset
        row_set = table_set.tables[0]

        offset, headers = headers_guess(row_set.sample)
        row_set.register_processor(headers_processor(headers))
        row_set.register_processor(offset_processor(offset + 1))
        types = type_guess(row_set.sample, strict=True)

        # Get a sample as well..
        sample = next(row_set.sample)

        clean = lambda v: str(v) if not isinstance(v, str) else v 
        schema = []
        for i, h in enumerate(headers):
            schema.append([h,
                           str(types[i]),
                           clean(sample[i].value)])

        return schema

    def parse_diff(self, diff):
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
                ("->", ["Changed rows",0]),
                (":", ["Reordered row",0])
            ]))
        ])

        diff = diff.getData()
        #print(diff)
        # [['!', '', '', '+++'], 
        #  ['@@', 'State', 'City', 'Metro'], 
        #  ['+', 'KA', 'Bangalore', '1'], 
        #  ['+', 'MH', 'Mumbai', '2'], 
        #  ['+++', 'KL', 'Kottayam', '0']]
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
            # print(row)
            if row[0] in summary['data']:
                summary['data'][row[0]][1] += 1

        return summary

    def get_diff(self, filename1, filename2):

        # print("get_diff", filename1, filename2)

        ext = filename1.split(".")[-1].lower() 
        if ext not in ['csv', 'tsv', 'xls']: 
            return None

        csvs = {} 
        for f in [filename1, filename2]: 
            # print("Loading file", f)
            table_set = self.read_file(f) 
            if table_set is None: 
                raise Exception("Invalid table set")
            row_set = table_set.tables[0]
            #print("Guessing headers")
            offset, headers = headers_guess(row_set.sample)
            row_set.register_processor(headers_processor(headers))
            row_set.register_processor(offset_processor(offset+1))
            
            # Output of rowset is a structure
            csvs[f] = [headers] 
            for row in row_set: 
                csvs[f].append([r.value for r in row])
            
            #print(csvs[f][:3])

        # Loaded csv1 and csv2 
        table1 = daff.PythonTableView(csvs[filename1])
        table2 = daff.PythonTableView(csvs[filename2])

        alignment = daff.Coopy.compareTables(table1,table2).align()

        # print("Achieved alignment") 

        data_diff = []
        table_diff = daff.PythonTableView(data_diff)

        flags = daff.CompareFlags()
        highlighter = daff.TableDiff(alignment,flags)
        highlighter.hilite(table_diff)

        # Parse the differences
        #print("Parsing diff") 
        diff = self.parse_diff(table_diff)

        # print("Computed diff", diff) 
        return diff 


def setup(mgr):

    obj = TableRepresentation()
    mgr.register('representation', obj)



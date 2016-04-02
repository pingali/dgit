#!/usr/bin/env python

import os, sys
from dgitcore.plugins.instrumentation import InstrumentationBase
from dgitcore.config import get_config
from hashlib import sha1
import mimetypes

from messytables import (CSVTableSet, type_guess, headers_guess,
                         offset_processor, DateType, StringType,
                         DecimalType, IntegerType,
                         DateUtilType, BoolType,
                         rowset_as_jts, headers_and_typed_as_jts)


def compute_sha1(filename):

    h = sha1()
    fd = open(filename)
    while True:
        buf = fd.read(0x1000000)
        if buf in [None, ""]:
            break
        h.update(buf.encode('utf-8'))
    return h.hexdigest()


class ContentInstrumentation(InstrumentationBase):
    """Instrumentation to extract content summaries including mimetypes, sha1 signature and schema where possible.

    """
    def __init__(self):
        self.enable = 'y'
        super(ContentInstrumentation, self).__init__('content',
                                                     'v0',
                                                     "Basic content analysis")

    def update(self, config):

        # Update the mime, sha1 of the files
        for i in range(len(config['files'])):
            filename = config['files'][i]['filename']
            if os.path.exists(filename):

                u = {
                    'mimetype': mimetypes.guess_type(filename)[0],
                    'sha1': compute_sha1(filename)
                }

                if filename.lower().endswith('sv'): # csv/tsv
                    rows = CSVTableSet(csv_file).tables[0]
                    guessed_types = type_guess(rows.sample)
                    u['schema'] = guessed_types

                config['files'][i].update(u)


        return config

def setup(mgr):

    obj = ContentInstrumentation()
    mgr.register('instrumentation', obj)



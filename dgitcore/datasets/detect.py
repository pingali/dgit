#!/usr/bin/env python

from messytables import type_guess, \
  types_processor, headers_guess, headers_processor, \
  offset_processor, any_tableset

def get_schema(filename):
    """
    Guess the schema using messytables
    """
    fh = open(filename, 'rb')

    try:
        table_set = any_tableset(fh) # guess the type...
        row_set = table_set.tables[0]
    except:
        # Cannot find the schema.
        return []

    offset, headers = headers_guess(row_set.sample)
    row_set.register_processor(headers_processor(headers))
    row_set.register_processor(offset_processor(offset + 1))
    types = type_guess(row_set.sample, strict=True)

    # Get a sample as well..
    sample = next(row_set.sample)

    schema = []
    for i, h in enumerate(headers):
        schema.append([h,
                       str(types[i]),
                       sample[i].value])

    return schema

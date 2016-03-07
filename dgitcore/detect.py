#!/usr/bin/env python 

from messytables import CSVTableSet, type_guess, \
  types_processor, headers_guess, headers_processor, \
  offset_processor, any_tableset

def get_schema(filename): 
    
    if filename.lower().endswith('.csv'):
        
        fh = open(filename, 'rb')
        table_set = CSVTableSet(fh)
        row_set = table_set.tables[0]
        offset, headers = headers_guess(row_set.sample)
        row_set.register_processor(headers_processor(headers))
        row_set.register_processor(offset_processor(offset + 1))
        types = type_guess(row_set.sample, strict=True)
        
        schema = []
        for i, h in enumerate(headers): 
            schema.append([h, str(types[i])])
    
        return schema 

    return None

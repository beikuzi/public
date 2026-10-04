"""Strict comment-like parsing: missing and malformed counts are never observed zeros."""
import re

def parse_likes(value):
    if value is None:return {'value':None,'status':'unknown','reason':'missing_or_null'}
    if isinstance(value,bool):return {'value':None,'status':'invalid','reason':'boolean_not_count'}
    if isinstance(value,int):
        if value>=0:return {'value':value,'status':'observed','reason':None}
        return {'value':None,'status':'invalid','reason':'negative_count'}
    if isinstance(value,str):
        stripped=value.strip()
        if not stripped:return {'value':None,'status':'unknown','reason':'blank_count'}
        if re.fullmatch(r'[0-9]+',stripped):
            try:return {'value':int(stripped),'status':'observed','reason':None}
            except ValueError:return {'value':None,'status':'invalid','reason':'integer_out_of_range'}
        return {'value':None,'status':'invalid','reason':'non_integer_string'}
    if isinstance(value,float):return {'value':None,'status':'invalid','reason':'float_not_integer_count'}
    return {'value':None,'status':'invalid','reason':'unsupported_type'}

def row_likes(row):
    parsed=parse_likes(row.get('likes'))
    # An importer has already discarded an invalid raw value; preserve that finding.
    if row.get('likes') is None and row.get('likes_status')=='invalid':
        return {'value':None,'status':'invalid','reason':'invalid_in_imported_source'}
    return parsed

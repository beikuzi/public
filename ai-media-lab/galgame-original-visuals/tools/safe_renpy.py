#!/usr/bin/env python3
"""Read-only RPA-3/RPYC inspection. Python standard library; no pickle execution.

RPA indexes: a strict primitive-only pickle VM rejects every global/class/call
opcode. RPYC: an optional inert AST mode records a small whitelist of Ren'Py
class names, NEWOBJ and BUILD as data, never importing classes or calling them.
REDUCE, extension, persistent-id and all unknown opcodes are always rejected.
Only legacy zlib RPYC is supported, not modern RENPY RPC2 containers.
"""
import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
import os
from pathlib import Path, PurePosixPath
import pickletools
import re
import sys
import zlib

MAX_COMPRESSED = 32 * 1024 * 1024
MAX_DECOMPRESSED = 64 * 1024 * 1024
MAX_OPS = 2_000_000
MAX_ITEMS = 500_000
MAX_MEMBER = 128 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
CODE_SUFFIXES = {'.py', '.pyc', '.pyo', '.rpy', '.rpyc', '.rpym', '.rpymc', '.exe', '.dll', '.so', '.dylib', '.sh', '.bat', '.cmd', '.ps1', '.com', '.scr', '.js', '.jar'}
AST_CLASSES = {'Label', 'UserStatement', 'Scene', 'With', 'Show', 'Say', 'Hide', 'Python', 'EarlyPython', 'PyCode', 'Menu', 'Return', 'Jump', 'Call', 'If', 'While', 'Init', 'Image', 'Transform', 'Define', 'Default', 'Pass'}

class UnsafeData(ValueError):
    """Unsupported, malformed, or potentially unsafe input."""

@dataclass(eq=False)
class Symbol:
    module: str
    name: str

@dataclass(eq=False)
class InertNode:
    symbol: Symbol
    state: dict = field(default_factory=dict)
    ordinal: int = 0


def bounded_zlib(raw, limit=MAX_DECOMPRESSED, allow_digest=False):
    if len(raw) > MAX_COMPRESSED:
        raise UnsafeData('compressed input exceeds limit')
    d = zlib.decompressobj()
    try:
        data = d.decompress(raw, limit + 1)
    except zlib.error as e:
        raise UnsafeData('invalid zlib stream') from e
    if len(data) > limit or d.unconsumed_tail or not d.eof:
        raise UnsafeData('decompression limit or truncated stream')
    if d.unused_data and not (allow_digest and len(d.unused_data) == 16):
        raise UnsafeData('unexpected bytes after zlib stream')
    return data


def safe_pickle(data, inert_ast=False):
    """Interpret allowed opcodes as data only; never call pickle.loads/unpickle.

    Built-in exact container types only. Keys are bounded primitive tuples or
    scalars. In AST mode allowed symbols are inert, constructor args must be
    empty, and BUILD only copies string-keyed state dictionaries.
    """
    if len(data) > MAX_DECOMPRESSED:
        raise UnsafeData('pickle exceeds limit')
    stack, memo, nodes = [], {}, []
    mark = object()
    def pop():
        if not stack or stack[-1] is mark:
            raise UnsafeData('stack underflow')
        return stack.pop()
    def marked():
        i = len(stack) - 1
        while i >= 0 and stack[i] is not mark:
            i -= 1
        if i < 0:
            raise UnsafeData('missing MARK')
        values = stack[i + 1:]
        del stack[i:]
        return values
    def key_ok(x, depth=0):
        if depth > 20:
            return False
        if type(x) in (str, bytes, int, float, bool, type(None)):
            return True
        return type(x) is tuple and len(x) <= 100 and all(key_ok(v, depth+1) for v in x)
    def put_dict(target, pairs):
        if type(target) is not dict or len(pairs) % 2:
            raise UnsafeData('invalid dictionary operation')
        for i in range(0, len(pairs), 2):
            if not key_ok(pairs[i]):
                raise UnsafeData('unsafe dictionary key')
            target[pairs[i]] = pairs[i+1]
        if len(target) > MAX_ITEMS:
            raise UnsafeData('dictionary limit')
    try:
        for count, (op, arg, pos) in enumerate(pickletools.genops(data), 1):
            if count > MAX_OPS or len(stack) > MAX_ITEMS or len(memo) > MAX_ITEMS:
                raise UnsafeData('pickle resource limit')
            name = op.name
            if name == 'PROTO':
                if arg > 4:
                    raise UnsafeData('unsupported pickle protocol')
            elif name == 'FRAME':
                if arg > len(data) - pos - 9:
                    raise UnsafeData('invalid frame length')
            elif name == 'STOP':
                if len(stack) != 1 or stack[0] is mark or pos + 1 != len(data):
                    raise UnsafeData('invalid terminal stack or trailing bytes')
                return stack[0], nodes
            elif name == 'MARK': stack.append(mark)
            elif name == 'NONE': stack.append(None)
            elif name == 'NEWTRUE': stack.append(True)
            elif name == 'NEWFALSE': stack.append(False)
            elif name in {'INT', 'BININT', 'BININT1', 'BININT2', 'LONG', 'LONG1', 'LONG4', 'FLOAT', 'BINFLOAT'}:
                if type(arg) not in (int, bool, float):
                    raise UnsafeData('invalid number')
                stack.append(arg)
            elif name in {'STRING', 'BINSTRING', 'SHORT_BINSTRING', 'UNICODE', 'BINUNICODE', 'SHORT_BINUNICODE', 'BINUNICODE8', 'BINBYTES', 'SHORT_BINBYTES', 'BINBYTES8'}:
                if len(arg) > 8 * 1024 * 1024:
                    raise UnsafeData('string limit')
                stack.append(arg)
            elif name == 'EMPTY_LIST': stack.append([])
            elif name == 'EMPTY_DICT': stack.append({})
            elif name == 'EMPTY_TUPLE': stack.append(())
            elif name in {'TUPLE1', 'TUPLE2', 'TUPLE3'}:
                n = int(name[-1]); values = [pop() for _ in range(n)]; stack.append(tuple(reversed(values)))
            elif name == 'TUPLE': stack.append(tuple(marked()))
            elif name == 'LIST': stack.append(marked())
            elif name == 'DICT':
                pairs = marked(); d = {}; put_dict(d, pairs); stack.append(d)
            elif name in {'APPEND', 'APPENDS'}:
                values = [pop()] if name == 'APPEND' else marked()
                if not stack or type(stack[-1]) is not list:
                    raise UnsafeData('invalid list operation')
                if len(stack[-1]) + len(values) > MAX_ITEMS:
                    raise UnsafeData('list limit')
                stack[-1].extend(values)
            elif name in {'SETITEM', 'SETITEMS'}:
                if name == 'SETITEM':
                    v, k = pop(), pop(); pairs = [k, v]
                else: pairs = marked()
                if not stack: raise UnsafeData('missing dictionary')
                put_dict(stack[-1], pairs)
            elif name in {'BINPUT', 'LONG_BINPUT', 'PUT', 'MEMOIZE'}:
                i = len(memo) if name == 'MEMOIZE' else int(arg)
                if i < 0 or i >= MAX_ITEMS or not stack or stack[-1] is mark:
                    raise UnsafeData('invalid memo write')
                if i in memo: raise UnsafeData('duplicate memo write')
                memo[i] = stack[-1]
            elif name in {'BINGET', 'LONG_BINGET', 'GET'}:
                i = int(arg)
                if i not in memo: raise UnsafeData('invalid memo reference')
                stack.append(memo[i])
            elif inert_ast and name == 'GLOBAL':
                module, cls = arg.split(' ', 1)
                if module != 'renpy.ast' or cls not in AST_CLASSES:
                    raise UnsafeData('unsupported inert class: ' + arg)
                stack.append(Symbol(module, cls))
            elif inert_ast and name == 'NEWOBJ':
                args, sym = pop(), pop()
                if type(sym) is not Symbol or type(args) is not tuple or args:
                    raise UnsafeData('only empty inert constructor data supported')
                node = InertNode(sym, ordinal=len(nodes)); nodes.append(node); stack.append(node)
            elif inert_ast and name == 'BUILD':
                state = pop()
                if not stack or type(stack[-1]) is not InertNode:
                    raise UnsafeData('BUILD target must be inert')
                if stack[-1].symbol.name == 'PyCode':
                    # Custom PyCode state is retained only as inert opaque data;
                    # never deserialize its bytecode, evaluate or expose it.
                    stack[-1].state['_opaque_state'] = state
                    continue
                if type(state) is tuple and len(state) == 2:
                    parts = state
                else: parts = (state,)
                for part in parts:
                    if part is None: continue
                    if type(part) is not dict or any(type(k) is not str for k in part):
                        raise UnsafeData('unsupported inert state: ' + stack[-1].symbol.name + ' ' + str(type(state)) + ' part=' + str(type(part)))
                    stack[-1].state.update(part)
            else:
                raise UnsafeData('forbidden or unsupported opcode: ' + name)
    except (ValueError, IndexError, KeyError, TypeError, OverflowError, UnicodeError) as e:
        if isinstance(e, UnsafeData): raise
        raise UnsafeData('malformed pickle data') from e
    raise UnsafeData('missing STOP')


def safe_name(name):
    if type(name) is bytes:
        name = name.decode('utf-8')
    if type(name) is not str or not name or len(name) > 1024:
        raise UnsafeData('invalid member name')
    # Conservative portable paths: no drive, ADS, backslash, dot components,
    # control chars, Windows devices, or trailing spaces/dots.
    if '\\' in name or ':' in name or name.startswith('/') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise UnsafeData('unsafe archive path')
    parts = name.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM', 'LPT') for n in range(1,10)}
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) or p.split('.')[0].upper() in reserved for p in parts):
        raise UnsafeData('unsafe archive component')
    return name


@dataclass(frozen=True)
class Segment:
    offset: int
    length: int
    prefix: bytes

class RPA3:
    def __init__(self, path):
        self.path = Path(path)
        self.members = {}
        with self.path.open('rb') as f:
            self.size = os.fstat(f.fileno()).st_size
            h = f.readline(128)
            if not re.fullmatch(rb'RPA-3\.0 [0-9a-fA-F]{16} [0-9a-fA-F]{8}\r?\n', h):
                raise UnsafeData('not a supported RPA-3.0 header')
            self.index_offset = int(h[8:24],16); key = int(h[25:33],16)
            if not len(h) <= self.index_offset < self.size or self.size - self.index_offset > MAX_COMPRESSED:
                raise UnsafeData('archive index bounds invalid')
            f.seek(self.index_offset)
            raw_index, _ = safe_pickle(bounded_zlib(f.read(MAX_COMPRESSED+1)))
        if type(raw_index) is not dict or len(raw_index) > MAX_ITEMS:
            raise UnsafeData('index must be bounded dictionary')
        folded = set()
        for raw_name, segments in raw_index.items():
            name = safe_name(raw_name)
            if name.casefold() in folded:
                raise UnsafeData('case-colliding archive paths')
            folded.add(name.casefold())
            if type(segments) is not list or not segments or len(segments) > 10000:
                raise UnsafeData('invalid segment list')
            checked, total = [], 0
            for seg in segments:
                if type(seg) is not tuple or len(seg) not in (2,3) or any(type(x) is not int or x < 0 for x in seg[:2]):
                    raise UnsafeData('invalid segment')
                off, length = seg[0] ^ key, seg[1] ^ key
                prefix = seg[2] if len(seg) == 3 else b''
                if type(prefix) is str: prefix = prefix.encode('latin1')
                if type(prefix) is not bytes: raise UnsafeData('invalid segment prefix')
                physical = length - len(prefix)
                if length < 0 or length > MAX_MEMBER or physical < 0 or off < len(h) or off + physical > self.index_offset:
                    raise UnsafeData('member outside archive data bounds')
                total += length
                if total > MAX_MEMBER: raise UnsafeData('member exceeds limit')
                checked.append(Segment(off,length,prefix))
            self.members[name] = checked
        # A file path cannot also be the parent of another file.
        for name in self.members:
            parents = PurePosixPath(name).parents
            if any(str(p).casefold() in folded for p in parents if str(p) != '.'):
                raise UnsafeData('file/directory path collision')

    def index(self):
        return [{'name': n, 'size': sum(s.length for s in segs), 'segments': len(segs)} for n,segs in sorted(self.members.items())]

    def read(self, name):
        name = safe_name(name)
        if name not in self.members: raise UnsafeData('exact member not present: ' + name)
        result = bytearray()
        with self.path.open('rb') as f:
            if os.fstat(f.fileno()).st_size != self.size: raise UnsafeData('archive changed')
            for s in self.members[name]:
                result.extend(s.prefix); f.seek(s.offset)
                chunk = f.read(s.length-len(s.prefix))
                if len(chunk) != s.length-len(s.prefix): raise UnsafeData('short archive read')
                result.extend(chunk)
        return bytes(result)

    def extract(self, names, destination, allow_code=False):
        """Only exact explicit selection. Never overwrite or set executable bits."""
        root = Path(destination).absolute()
        if root.exists() and (root.is_symlink() or not root.is_dir()):
            raise UnsafeData('output root is not a real directory')
        # Reject symlink parents even if they resolve inside the output root.
        for parent in (root, *root.parents):
            if parent.is_symlink(): raise UnsafeData('symlink output parent')
        selected, total = [], 0
        for n in names:
            n = safe_name(n)
            if n not in self.members: raise UnsafeData('exact member not present: '+n)
            if not allow_code and PurePosixPath(n).suffix.lower() in CODE_SUFFIXES:
                raise UnsafeData('code extraction needs --allow-code and exact member names')
            total += sum(s.length for s in self.members[n])
            if total > MAX_TOTAL: raise UnsafeData('total extraction limit')
            selected.append(n)
        if len(set(selected)) != len(selected): raise UnsafeData('duplicate selection')
        if not selected: raise UnsafeData('select at least one exact member')
        # POSIX dirfd operations prevent symlink substitution races. Refuse
        # extraction if these primitives are missing; listing still works.
        if not hasattr(os,'O_NOFOLLOW') or os.open not in os.supports_dir_fd or os.mkdir not in os.supports_dir_fd:
            raise UnsafeData('secure extraction needs POSIX dirfd/O_NOFOLLOW support')
        def open_root():
            # Walk from filesystem root using only dirfds and O_NOFOLLOW, so
            # replacing an ancestor with a symlink cannot redirect extraction.
            fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for part in root.parts[1:]:
                    try: os.mkdir(part, mode=0o700, dir_fd=fd)
                    except FileExistsError: pass
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd); fd = child
                return fd
            except BaseException:
                os.close(fd); raise
        outputs = []
        for n in selected:
            fd = open_root()
            try:
                parts = n.split('/')
                for part in parts[:-1]:
                    try: os.mkdir(part, mode=0o700, dir_fd=fd)
                    except FileExistsError: pass
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd); fd = child
                out = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                with os.fdopen(out, 'wb') as f: f.write(self.read(n))
                outputs.append(str(root/n))
            finally: os.close(fd)
        return outputs


def read_rpyc(path):
    p = Path(path)
    with p.open('rb') as f: raw = f.read(MAX_COMPRESSED+1)
    data = bounded_zlib(raw, allow_digest=True)
    root, nodes = safe_pickle(data, inert_ast=True)
    if type(root) is not tuple or len(root)!=2 or type(root[0]) is not dict or type(root[1]) is not list:
        raise UnsafeData('unsupported RPYC root')
    return root, nodes


def simple(value, depth=0, _budget=None):
    """Bounded JSON-safe shallow metadata, with no game code evaluation."""
    if _budget is None: _budget = [2000]
    _budget[0] -= 1
    if _budget[0] < 0: return '<item limit>'
    if depth > 8: return '<depth limit>'
    if type(value) in (str,int,float,bool,type(None)): return value
    if type(value) is bytes: return value.decode('utf-8','replace')
    if type(value) in (tuple,list): return [simple(v,depth+1,_budget) for v in value[:100]]
    if type(value) is dict: return {str(k):simple(v,depth+1,_budget) for k,v in list(value.items())[:100]}
    if type(value) is InertNode: return {'inert_class':value.symbol.name}
    return '<unsupported>'


def script_records(path):
    root,nodes = read_rpyc(path)
    records = []
    current_label = None
    for node in nodes:
        s,kind = node.state,node.symbol.name
        # Nodes are in pickle construction order, generally script order. A
        # containing Label precedes its block; this is a structural inventory,
        # not a control-flow execution trace.
        if kind == 'Label': current_label = simple(s.get('name'))
        if kind in {'Say','Label','Scene','Show','Hide','Image','Menu','Jump','Call','Return','With','UserStatement'}:
            r={'kind':kind,'ordinal':node.ordinal,'line':simple(s.get('linenumber')), 'label': current_label}
            if kind=='Say': r.update(speaker=simple(s.get('who')),text=simple(s.get('what')))
            if kind=='Label': r['name']=simple(s.get('name'))
            for key in ('imspec','imgname','target','expression','items','expr','line'):
                if key in s: r[key if key!='line' else 'statement']=simple(s[key])
            records.append(r)
    return {'source':Path(path).name, 'script_version':root[0].get('version'), 'node_counts':dict(Counter(n.symbol.name for n in nodes)), 'records':records}


def write_json(path, data):
    if path:
        with Path(path).open('x',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
    else:
        json.dump(data,sys.stdout,ensure_ascii=False,indent=2); print()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('list',help='list validated RPA-3 index as JSON'); p.add_argument('archive'); p.add_argument('--output')
    p=sub.add_parser('extract',help='extract exact named members only'); p.add_argument('archive'); p.add_argument('destination'); p.add_argument('members',nargs='+'); p.add_argument('--allow-code',action='store_true')
    p=sub.add_parser('rpyc',help='legacy RPYC inert dialogue/image metadata JSON'); p.add_argument('input'); p.add_argument('--output')
    p=sub.add_parser('strings',help='non-executing legacy RPYC pickle string inventory'); p.add_argument('input'); p.add_argument('--output')
    args=parser.parse_args()
    try:
        if args.command=='list': write_json(args.output,RPA3(args.archive).index())
        elif args.command=='extract': write_json(None,RPA3(args.archive).extract(args.members,args.destination,args.allow_code))
        elif args.command=='rpyc': write_json(args.output,script_records(args.input))
        else:
            with Path(args.input).open('rb') as f: raw=f.read(MAX_COMPRESSED+1)
            data=bounded_zlib(raw,allow_digest=True)
            strings=[]
            for i,(op,arg,pos) in enumerate(pickletools.genops(data)):
                if i>=MAX_OPS: raise UnsafeData('opcode limit')
                if type(arg) is str and op.name in {'STRING','BINSTRING','SHORT_BINSTRING','UNICODE','BINUNICODE','SHORT_BINUNICODE','BINUNICODE8'}: strings.append({'offset':pos,'value':arg})
            write_json(args.output,strings)
    except (UnsafeData,OSError,ValueError) as e:
        parser.exit(2,'Rejected: '+str(e)+'\n')

if __name__=='__main__': main()

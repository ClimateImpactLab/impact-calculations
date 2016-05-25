#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, datetime, itertools, textwrap
from collections import OrderedDict


try:
  unicode
except NameError:
  unicode = str # python3

endheader = "##########\n"
endfinder = re.compile(r'^#{5,}[\t\s\n\r,\'\"]*$')
varfinder = re.compile(r'^(?P<desc>[^\[]+)\s+(?P<unit>\[([^\]]+)\])')
headerfinder = re.compile(r'^[\s]*#')
linesplitter = lambda line: re.split(r'(?<!([\s:]http|https)):', line, maxsplit=1)

def dated_version(prefix):
    return prefix + '.' + str(datetime.date.today())

def write_headinfo(fp, headinfo):
    write(fp, headinfo['oneline'], headinfo['version'], headinfo.get('dependencies', []), headinfo['variables'],
          headinfo['sources'], headinfo.get('description', None))

def write(fp, oneline, version, dependencies, variables, sources=None, description=None, prefix="# ", indent='    ', **kwargs):
    """Writes the common header.
online and version are short strings.
dependencies is a list of versions.
variables is a dictionary of name => tuple (short description, units).
sources is a dictionary of name => one-line string.
description can be many lines or missing."""

    fp.write(prefix + oneline + "\n")
    fp.write(prefix + "\n")
    fp.write(prefix + "Version: " + version + "\n")
    if dependencies:
        fp.write(prefix + "Dependencies: " + ', '.join(dependencies) + "\n")
    fp.write(prefix + "Variables:\n")
    if isinstance(variables, str):
        fp.write(prefix + "   " + variables + "\n")
    else:
        for name in variables:
            if isinstance(variables[name], Variable):
                fp.write(prefix + indent + str(variables[name]) + "\n")
            else:
                fp.write(prefix + indent + name + ": " + variables[name][0] + " [" + variables[name][1] + "]\n")
    if sources is not None:
        if isinstance(sources, list):
            fp.write('{p}Sources:\n{p}{i}{s}\n'.format(p=prefix, i=indent, s=('\n'+prefix+indent).join(sources)))
        elif isinstance(sources, dict):
            fp.write('{p}Sources:\n{p}{i}{s}\n'.format(p=prefix, i=indent, s=('\n'+prefix+indent).join(['{}: {}'.format(k,v) for k, v in sources.items()])))
        else:
            fp.write('{p}Sources:\n{p}{i}{s}\n'.format(p=prefix, i=indent, s=str(sources)))

    for kw, args in kwargs.items():
        fp.write('{}{}:\n{}{}\n'.format(prefix, kw.title(), prefix+indent, args if isinstance(args, str) else ('\n'+prefix+indent).join(args)))

    if description:
        fp.write(prefix + "\n")
        for line in textwrap.wrap(description):
            fp.write(prefix + line + "\n")

    if prefix != '':
        fp.write(endheader)

def deparse(fp, dependencies):
    header = parse(fp)

    if 'version' in header and header['version'] not in dependencies:
        dependencies.append(header['version'])

    return fp

def clean(string, addl=''):
    return string.strip('\n\t\r ,#\'\"'+addl)

class MalformedHeaderError(IOError):
    pass

class Variable(object):
    @classmethod
    def parse(cls, name, defn=''):
        matchstr = re.search(varfinder, defn)
        if matchstr is None:
            return cls(name, clean(defn))
        return cls(name, clean(matchstr.group('desc')), clean(matchstr.group('unit').strip('[]')))

    def __init__(self, name, description, unit = None):
        self.name = name
        self.description = description
        self.unit = unit
    def __repr__(self):
        return '<var {}>'.format(self.__str__())

    def __str__(self):
        return '{name}: {desc} [{unit}]'.format(name=self.name, desc=self.description, unit=self.unit)

def parse(fp, metafile=False):
    '''
    Reads a text or csv file and returns a parsed metadata dictionary

    The format for a standard ImpactLab header can be found at 
    https://docs.google.com/document/d/1aCc-erfuu2jLtwWPh2wjUNX0u6buDBwfVJ8bwnrNRxk/edit?usp=sharing
    '''

    i = 0

    if isinstance(fp, str) or isinstance(fp, unicode):
        with open(fp, 'r') as fp2:
            return parse(fp2, metafile)

    header = {}

    # Peek in file, exit on files with no header
    last_pos = fp.tell()
    try:
        i += 1
        line = next(fp)
    except UnicodeDecodeError as e:
        raise IOError('Reading file {} failed on line {} with error: {}'.format(fp, i+1, str(e)))

    while re.search(r'^,*$', line):
        try:
            line = next(fp)
        except StopIteration:
            break

    if (not metafile) and (not re.search(headerfinder, line)):
        fp.seek(last_pos)
        return header

    header['oneline'] = clean(line)

    if metafile:
        indent_searcher = re.compile(r'^[ \t]{2,}')
    else:
        indent_searcher = re.compile(r'^#[ \t]{2,}')

    addcall = None
    for i, line in enumerate(fp):
        if re.search(endfinder, line):
            break

        if not (metafile or re.search(headerfinder, line)):
            break

        if clean(line) == "":
            continue

        indented = True if re.search(indent_searcher, line.strip('\'\"')) else False

        splitline = linesplitter(line)
        if len(splitline) > 2:
            splitline = [splitline[0], splitline[-1]]
        chunks = map(clean, splitline)
        chunks = tuple(chunks)

        if indented:
            if addcall is None:
                raise MalformedHeaderError('indented section found on line {} with no valid metadata type'.format(i+2))
            addcall(*chunks)

        else:
            title = clean(chunks[0]).lower()
            if title == 'version':
                header['version'] = clean(chunks[1], '[]')
                addcall = None
            elif re.search(r'dependenc(y|ies)', title):
                header['dependencies'] = [clean(s) for s in clean(','.join(chunks[1:]), '[]').split(',') if len(clean(s)) > 0]
                addcall = lambda dep: header['dependencies'].append(clean(dep))
            elif re.search(r'variable(s)?', title):
                header['variables'] = {}
                addcall = lambda *defn: header['variables'].__setitem__(defn[0], Variable.parse(*defn))
            elif re.search(r'coordinate(s)?', title) or re.search(r'stack', title):
                category = 'stack' if re.search(r'stack', title) else 'coordinates'
                header[category] = OrderedDict()
                if len(chunks) > 1:
                    # Handle string, list, or dict of lists of coordinates
                    header[category].update(OrderedDict([(lambda v: (v[0],None if len(v) == 1 else [clean(ele) for ele in clean(','.join(v[1]), '[]').split(',')]))(linesplitter(ele)) for ele in clean(','.join(chunks[1:]), '[]\{\}').split(',') if ele is not '']))
                addcall = lambda *defn: header[category].__setitem__(defn[0], None if len(defn) <= 1 else [clean(ele) for ele in clean(','.join(chunks[1:]), '[]\{\}').split(',')])
            elif re.search(r'source(s)?', title):
                header['sources'] = []
                addcall = lambda *info: header['sources'].append(': '.join(info))
            elif len(chunks) > 1:
                header[title] = (lambda text: [text] if len(text) > 0 else [])(clean(chunks[1], '[]'))
                addcall = lambda *info: header[title].append(': '.join(info))
            elif len(chunks) == 1:
                header['description'] = ('' if 'description' not in header else header['description'] + ' ') + clean(chunks[0])
                addcall = None

    # Coerce header to string if input manually
    for attr in ['description', 'note', 'long_name']:
        if isinstance(header.get(attr, None), list):
            header[attr] = ' '.join(header[attr])

    return header

def add_header(filename_in, filename_out, oneline, version, dependencies, variables, sources, description=None):
    with open(filename_in, 'r') as fp_in:
        with open(filename_out, 'w') as fp_out:
            write(fp_out, oneline, version, dependencies, variables, sources, description)
            for line in fp_in:
                fp_out.write(line)

if __name__ == '__main__':
    import sys
    import readline

    def rlinput(prompt, prefill=''):
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
        try:
            return raw_input(prompt)
        finally:
            readline.set_startup_hook()

    filename_in = sys.argv[1]

    if filename_in[-4:].lower() == '.fgh':
        filename_out = filename_in
        print("Output file: ", filename_out)
        filename_in = None
    else:
        print("Input File: ", filename_in)
        filename_out = rlinput("Output File: ", filename_in)

    oneline = rlinput("One line description: ")
    version = rlinput("Version: ")

    print("Enter the dependencies (blank to finish):")
    dependencies = []
    while True:
        dependency = rlinput("Version: ")
        if not dependency:
            break
        dependencies.append(dependency)

    print("Define the variables (blank to finish):")
    variables = {}
    while True:
        name = rlinput("Variable Name: ")
        if not name:
            break

        desc = rlinput("Short description: ")
        unit = rlinput("Units: ")
        variables[name] = (desc, unit)

    print("Define the sources (blank to finish):")
    sources = {}
    while True:
        name = rlinput("Source Name: ")
        if not name:
            break

        desc = rlinput("Short description: ")
        sources[name] = desc

    print("Enter a description (type Ctrl-D on a blank line to finish):")
    description = '\n'.join(sys.stdin.readlines())
    if not description.strip():
        description = None

    if filename_in is not None:
        add_header(filename_in, filename_out, oneline, version, dependencies, variables, sources, description)
    else:
        with open(filename_out, 'w') as fp_out:
            write(fp_out, oneline, version, dependencies, variables, sources, description)


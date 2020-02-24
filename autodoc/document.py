import os, importlib
import server, describe, caller

# Collect all defined impacts
computations = {}

path = os.path.dirname(os.path.realpath(__file__))
for root, dirs, files in os.walk(path):
    if root != path:
        for filename in files:
            if filename[-3:] == '.py' and filename != '__init__.py':
                computations[filename[:-3]] = root[len(path)+1:]

print(("Computations:", len(computations)))

wikiroot = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../wiki"))
# Collect all wiki impacts
path = os.path.join(wikiroot, "HealthModels.rst")

seeking_gcpid = seeking_endgcpid = seeking_autogenflag = False
gcpid = None

docsections = []
alllines = []

with open(path, 'r+') as fp:
    for line in fp:
        alllines.append(line)
        if line.rstrip()[0:5] == '=====':
            if seeking_endgcpid:
                seeking_endgcpid = False
                seeking_autogenflag = True
            else:
                seeking_gcpid = True
        elif seeking_gcpid:
            if line.strip() != '':
                gcpid = line.strip()
                seeking_gcpid = False
                seeking_endgcpid = True
            else:
                seeking_gcpid = False
        elif seeking_autogenflag:
            if line.strip() == '':
                continue
            elif line[0:len('AUTOMATICALLY GENERATED')] == 'AUTOMATICALLY GENERATED':
                # Valid!
                docsections.append(gcpid) # Don't track locations, because will change
                # Reset
                seeking_gcpid = seeking_endgcpid = seeking_autogenflag = False
                gcpid = None
            else:
                seeking_autogenflag = False

# Read in the template
template = ""
with open(os.path.join(wikiroot, "Model Auto-generation Template.rst"), 'r') as fp:
    for line in fp:
        if line[0] == ' ':
            break

    template = line[2:]
    for line in fp:
        if line[0] == '\n':
            template += '\n'
        elif line[0] != ' ':
            break

        template += line[2:]

template += '\n'

# Access the spreadsheet
wks, header, ids = server.get_model_info()

# Fill in each docsection
for gcpid in docsections:
    # Find the end of the section
    if (gcpid + '\n') not in alllines:
        print(("Could not find impact", gcpid))
        continue
    startline = alllines.index(gcpid + '\n') + 2
    endline = None
    for ii in range(startline, len(alllines)):
        if alllines[ii].lower() == "impact calculation\n":
            endline = ii
            break
        if alllines[ii][0:5] == '=====':
            break
    if endline is None:
        print(("Could not find 'Impact calculation' after " + gcpid))
        continue

    autogen = template
    if gcpid not in ids:
        autogen = autogen.split('\n')[0] + "\n\nCould not find Unique ID in Master DMAS Information spreadsheet.\n"
    else:
        values = wks.row_values(ids.index(gcpid) + 1)
        print(autogen)
        for ii in range(min(len(header), len(values))):
            if values[ii] is not None:
                autogen = autogen.replace('[' + header[ii] + ']', values[ii])

        if gcpid not in computations:
            autogen = autogen.replace('[Function Docstring]', "Impact does not have a new-style computation.")
            autogen = autogen.replace('`(Source) <[Source Link]>`_', "")
            autogen = autogen.replace(':math:`[Calculation LaTeX]`', "")
            autogen = autogen.replace('[Dependencies]', "")
        else:
            # Load information from computation itself
            root = computations[gcpid]
            module = 'impacts.' + root.replace('/', '.') + '.' + gcpid
            mod = importlib.import_module(module, 'impacts')
            autogen = autogen.replace('[Function Docstring]', str(mod.__doc__))
            autogen = autogen.replace('[Source Link]', "https://bitbucket.org/ClimateImpactLab/socioeconomics/src/master/impacts/" + root + "/" + gcpid + ".py")

            try:
                calculation, dependencies = caller.call_prepare(module, None, None, None, getmodel=describe.get_model_info, getdata=describe.get_data_info)
                for (key, value, units) in calculation.latex():
                    if key == 'Equation':
                        autogen = autogen.replace('[Calculation LaTeX]', value)
                        autogen = autogen.replace('[Units]', units)
                    else:
                        autogen += '- :math:`' + key + '` ' + value + ' [' + units + ']\n'

                    autogen = autogen.replace('[Dependencies]', ', '.join(dependencies))
            except:
                autogen = autogen.replace('[Calculation LaTeX]', "Computation unavailable.")
                autogen = autogen.replace('[Units]', "")
                autogen = autogen.replace('[Dependencies]', '')

    alllines = alllines[:startline] + [autogen] + alllines[endline:]

# Replace the wiki page
with open(path, 'w') as fp:
    for line in alllines:
        fp.write(line)

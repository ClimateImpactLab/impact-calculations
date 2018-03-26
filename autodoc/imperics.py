import sys, os, csv, importlib, yaml
import numpy as np
from impactlab_tools.utils import files
from interpret import container, configs
from generate import caller, loadmodels, pvalses
from adaptation import csvvfile
from openest.generate import formatting
import lib

## Configuration

futureyear = 2050
region = 'IND.21.329.1353' #'USA.14.608'

config = files.get_argv_config()
allcalcs = sys.argv[2]

## Starting

print "Configuring system..."
with open(config['module'], 'r') as fp:
    config.update(yaml.load(fp))
shortmodule = os.path.basename(config['module'])[:-4]

allcalcs_prefix = shortmodule + "-allcalcs-"
onlymodel = os.path.basename(allcalcs)[len(allcalcs_prefix):-4]
dir = os.path.dirname(allcalcs)

batch, rcp, gcm, iam, ssp = tuple(dir.split('/')[-5:])

print "Batch: " + batch
print "RCP: " + rcp
print "GCM: " + gcm
print "IAM: " + iam
print "SSP: " + ssp
print "Region: " + region

# Find the relevant CSVV
foundcsvv = False
for model, csvvpath, module, specconf in container.get_modules_csvv(config):
    basename = os.path.basename(csvvpath)[:-5]
    if basename == onlymodel:
        foundcsvv = True
        break

assert foundcsvv, "Could not find a CSVV correspondnig to %s." % onlymodel

## Print the inputs

lib.show_header("Merged configuration:")
print yaml.dump(config)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, allcalcs_prefix + onlymodel + ".csv"), 2, region, range(2000, 2011) + [futureyear-1, futureyear], hasmodel=False)

shapenum = 0
with open(os.path.join("/shares/gcp/regions/hierarchy-flat.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    for row in reader:
        if row[0] == region:
            shapenum = int(row[header.index('agglomid')]) - 1
            break
        
lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath)
csvvobj = csvvfile.read(csvvpath)

lib.show_header("Weather:")
clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(container.get_bundle_iterator(configs.merge(config, {'only-models': [gcm]})))

weather = {}
for year, ds in weatherbundle.yearbundles(futureyear + 1):
    if year in range(2001, 2011) + [futureyear-1, futureyear]:
        ds = ds.isel(region=shapenum)
        weather[str(year)] = {variable: ds[variable].values for variable in ds}

for variable in weather['2001']:
    if variable in ['time', 'region']:
        continue
    lib.show_header("  %s:" % variable)
    for year in sorted(weather.keys()):
        print "%s: %s..." % (year, ','.join(map(str, weather[year][variable][:10])))
            
lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [2001, futureyear], shapenum)

## Computations
# decide on a covariated variable
for variable in set([csvv['prednames'][ii] for ii in range(len(csvv['prednames'])) if csvv['covarnames'][ii] != '1']):
    for year in [2001, futureyear]:
        lib.show_header("Calculation of %s coefficient in %d (%f reported)" % (variable, year, lib.excind(calcs, year-1, 'coeff-' + variable)))
        lib.show_coefficient(csvv, calcs, year, variable)

pvals = pvalses.ConstantPvals(.5)
calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvvobj, module, weatherbundle, economicmodel, pvals[basename], specconf=specconf, config=configs.merge(config, {'quiet': True}), standard=False)

formatting.format_reset()
fullelements = calculation.format('julia')

last_label = None
for year in [2001, futureyear]:
    used_outputs = set()
    for label, elements in formatting.format_labels:
        if label == 'rebased':
            break
        
        while label in used_outputs:
            label += '2'
        last_label = label
        used_outputs.add(label)

        lib.show_header("Calculation of %s in %d (%f reported)" % (label, year, outputs[year][label]))
        julia = formatting.format_julia(elements, {calcs['header'][ii]: calcs[str(year)][ii] for ii in range(len(calcs['header']))}, include_comments=False)
        lib.show_julia(julia.split('\n'), clipto=None)

## Calculate rebased
lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))

alllines = []
for year in range(2001, 2011):
    elements = formatting.format_labels[-2][1]
    julia = formatting.format_julia(elements, {calcs['header'][ii]: calcs[str(year)][ii] for ii in range(len(calcs['header']))}, include_comments=False)
    lines = julia.split('\n')
    lines[-1] = 'output%d = ' % year +lines[-1]
    alllines.extend(lines)

alllines.append("(" + ' + '.join(["output%d" % year for year in range(2001, 2011)]) + ") / 10")
lib.show_julia(alllines, clipto=None)

## Final calculation

lib.show_header("Calc. of rebased (%f reported)" % outputs[futureyear]['rebased'])
lib.show_julia("%f - %f" % (outputs[futureyear][last_label], lib.excind(calcs, 2000, 'baseline')))

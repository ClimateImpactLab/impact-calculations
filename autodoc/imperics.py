"""Diagnostic generation script for configuration-based projections.

This script performs a set of hand-calculation diagnostics for any
configuration-based projection. This script requires that the
projection is first run in "diagnostic" mode: producing a single
region and the associated `allcalcs` file.

When this script is run, the text that is produced has three sections:

1. Inputs: This includes the merged configuration file, excerpts from
the allcalcs file, the weather data, and the output results (which are
inputs to this diagnostic process).

2. Beta calculations: Beta parameters are derived from a combination
of the CSVV gamma parameters and the covariates. This makes sure that
the curves being produced have the correct parameters.

3. Result calculation: For each reported calculation result, this
checks that the result values are as expected.

For steps 2 and 3, the diagnostic is performed by producing a set of
julia code that is intended to reproduce the calculations in the
projection system. Often the calculations will be done in different
but equivalent way. This julia code is then run, and the result is
reported to be compared with the pre-computed result.
"""

import sys, os, csv, importlib, yaml
import numpy as np
from impactlab_tools.utils import files
from interpret import container, configs
from generate import caller, loadmodels, pvalses
from adaptation import csvvfile
from openest.generate import formatting
from datastore import irvalues
from . import lib

## Configuration

config = files.get_argv_config()
allcalcs = sys.argv[2]

region = sys.argv[3] if len(sys.argv) > 3 else 'USA.14.608' #'IND.21.329.1353'
futureyear = int(sys.argv[4]) if len(sys.argv) > 4 else 2050

## Starting

print("Configuring system...")
with open(config['module'], 'r') as fp:
    config.update(yaml.load(fp))
shortmodule = os.path.basename(config['module'])[:-4]

allcalcs_prefix = shortmodule + "-allcalcs-"
onlymodel = os.path.basename(allcalcs)[len(allcalcs_prefix):-4]
dir = os.path.dirname(allcalcs)

batch, rcp, gcm, iam, ssp = tuple(dir.split('/')[-5:])

print(("Batch: " + batch))
print(("RCP: " + rcp))
print(("GCM: " + gcm))
print(("IAM: " + iam))
print(("SSP: " + ssp))
print(("Region: " + region))

lib.show_header("Merged configuration:")
print yaml.dump(config)

# Find the relevant CSVV
foundcsvv = False
for model, csvvpath, module, specconf in container.get_modules_csvv(config):
    basename = os.path.basename(csvvpath)[:-5]
    
    csvv_parts = container.csvv_organization(specconf)
    if csvv_parts is not None:
        for part in csvv_parts:
            if basename + '-' + part == onlymodel:
                foundcsvv = True
                break
    if basename == onlymodel:
        foundcsvv = True
        break

assert foundcsvv, "Could not find a CSVV corresponding to %s." % onlymodel

## Print the inputs
if 'within-season' in specconf:
    season_months = irvalues.load_culture_months(specconf['within-season'])[region]
    season_doys = irvalues.load_culture_doys(specconf['within-season'])[region]
    print(("\nSeason months: %d - %d; Season doys: %d - %d\n" % (season_months[0], season_months[1], season_doys[0], season_doys[1])))

betalimits = lib.find_betalimits(config)
    
lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, allcalcs_prefix + onlymodel + ".csv"), 2, region, list(range(2000, 2011)) + [futureyear-1, futureyear], hasmodel=False)

shapenum = 0
with open(os.path.join("/shares/gcp/regions/hierarchy-flat.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = next(reader)
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
for year, ds in weatherbundle.yearbundles(futureyear + 2):
    if year in list(range(2001, 2011)) + [futureyear-1, futureyear]:
        ds = ds.isel(region=shapenum)
        weather[str(year)] = {variable: ds[variable].values for variable in ds}

for variable in weather['2001']:
    if variable in ['time', 'month', 'region']:
        continue
    lib.show_header("  %s:" % variable)
    for year in sorted(weather.keys()):
        print(("%s: %s..." % (year, ','.join(map(str, weather[year][variable][:10])))))
            
lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [2001, futureyear], shapenum, deltamethod=config.get('deltamethod', False))

## Computations
if not config.get('deltamethod', False):
    # decide on a covariated variable
    for variable in set([csvv['prednames'][ii] for ii in range(len(csvv['prednames'])) if csvv['covarnames'][ii] != '1']):
        if variable == '':
            continue
        for year in [2001, futureyear]:
            lib.show_header("Calculation of %s coefficient in %d (%f reported)" % (variable, year, lib.excind(calcs, year-1, 'coeff-' + variable)))
            lib.show_coefficient(csvv, calcs, year, variable, betalimits=betalimits.get(variable, None))

pvals = pvalses.ConstantPvals(.5)
calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvvobj, module, weatherbundle, economicmodel, pvals[basename], specconf=specconf, config=configs.merge(config, {'quiet': True}), standard=False)

formatting.format_reset()

if 'within-season' in specconf:
    formatting.functions_known['Limit to within season'] = formatting.ParameterFormatElement("season-weather", "seasonweather")

formatting.functions_known['Extract from weather'] = formatting.ParameterFormatElement('identity', 'identity')
for tt in range(24):
     formatting.functions_known['Select time %d' % tt] = formatting.ParameterFormatElement("get-t-%d" % tt, "gett%d" % tt)
formatting.functions_known['Extract bin from weather'] = formatting.ParameterFormatElement('extract-bin', 'getbin', dependencies=['bin-edges', 'edd'])

extraparams = {'extract-bin': "(weather, bin) -> length(size(weather)) == 2 ? weather[:, bin_edges .== bin] : weather[bin_edges .== bin]"}
if 'within-season' in specconf:
    extraparams['season-weather'] = "(x) -> (length(size(x)) == 2 ? (size(x)[1] <= 24 ? x[%d:%d, :] : x[%d:%d, :]) : (length(x) <= 24 ? x[%d:%d] : x[%d:%d]))" % (season_months[0], season_months[1], season_doys[0], season_doys[1], season_months[0], season_months[1], season_doys[0], season_doys[1])
    for tt in range(24):
        extraparams['get-t-%d' % tt] = '(x) -> (seasonx = (length(size(x)) == 2 ? (size(x)[1] <= 24 ? x[%d:%d, :] : x[%d:%d, :]) : (length(x) <= 24 ? x[%d:%d] : x[%d:%d])); length(size(seasonx)) == 2 ? (size(seasonx)[1] >= %d ? seasonx[%d, :] : zeros(size(seasonx)[2])) : (length(seasonx) >= %d ? seasonx[%d] : 0))' % (season_months[0], season_months[1], season_doys[0], season_doys[1], season_months[0], season_months[1], season_doys[0], season_doys[1], tt+1, tt+1, tt+1, tt+1)
else:
    for tt in range(24):
        extraparams['get-t-%d' % tt] = '(x) -> length(x) >= %d ? x[%d] : 0' % (tt+1, tt+1)

extraelements = {'bin-edges': formatting.ParameterFormatElement('refTemp', "bin_edges"),
                 'edd': formatting.ParameterFormatElement('edd', "edd")}

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

        elements.update(extraelements)

        allparams = {calcs['header'][ii]: calcs['2000'][ii] for ii in range(len(calcs['header']))}
        allparams.update({calcs['header'][ii]: calcs[str(year - 1)][ii] for ii in range(len(calcs['header'])) if isinstance(calcs[str(year - 1)][ii], np.ndarray) or not np.isnan(calcs[str(year - 1)][ii])})
        allparams.update(weather[str(year)])
        allparams.update(extraparams)
        
        julia = formatting.format_julia(elements, allparams, include_comments=False)
        lib.show_julia(julia.split('\n'), clipto=None)

# ## Calculate rebased
# lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))

# alllines = []
# for year in range(2001, 2011):
#     elements = formatting.format_labels[-2][1]
#     elements.update(extraelements)
#     julia = formatting.format_julia(elements, {calcs['header'][ii]: calcs[str(year)][ii] for ii in range(len(calcs['header']))}, include_comments=False)
#     lines = julia.split('\n')
#     lines[-1] = 'output%d = ' % year +lines[-1]
#     alllines.extend(lines)

# alllines.append("(" + ' + '.join(["output%d" % year for year in range(2001, 2011)]) + ") / 10")
# lib.show_julia(alllines, clipto=None)

## Final calculation

lib.show_header("Calc. of rebased (%f reported)" % outputs[futureyear]['rebased'])
if last_label is not None:
    if not config.get('deltamethod', False):
        lib.show_julia("%f - %f" % (outputs[futureyear][last_label], lib.excind(calcs, 2000, 'baseline')))
    else:
        lib.show_julia(lib.get_julia(outputs[futureyear][last_label]) + " - " + lib.get_julia(lib.excind(calcs, 2000, 'baseline')))
else:
    elements.update(extraelements)
    
    allparams = {calcs['header'][ii]: calcs['2000'][ii] for ii in range(len(calcs['header']))}
    allparams.update({calcs['header'][ii]: calcs[str(futureyear-1)][ii] for ii in range(len(calcs['header'])) if not np.all(np.isnan(calcs[str(futureyear-1)][ii]))})
    allparams.update(weather[str(futureyear)])
    allparams.update(extraparams)
    
    julia = formatting.format_julia(elements, allparams, include_comments=False)
    lib.show_julia(julia.split('\n'), clipto=None)

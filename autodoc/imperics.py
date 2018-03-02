import sys, os, csv, importlib, yaml
import numpy as np
from interpret import container, specification
from generate import caller
import lib

## Configuration

futureyear = 2050
region = 'USA.14.608' #'IND.33.542.2153'

config = sys.argv[1]
allcalcs = sys.argv[2]

## Starting

print "Configuring system..."
with open(config['module'], 'r') as fp:
    config.update(yaml.load(fp))
shortmodule = os.path.basename(config['module'])[:-4]

allcalcs_prefix = "allmodels-allcalcs-"
onlymodel = os.path.basename(allcalcs)[len(allcalcs_prefix):-4]

# Find the relevant CSVV
foundcsvv = False
for model, csvvpath, module, specconf in container.get_modules_csvv(config):
    basename = os.path.basename(csvvpath)[:-5]
    if basename == onlymodel:
        foundcsvv = True
        break

assert foundcsvv, "Could not find a CSVV correspondnig to %s." % onlymodel

## Print the inputs

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

lib.show_header("Weather:")
clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(container.get_bundle_iterator(config))
covariator = specification.create_covariator(config, weatherbundle, economicmodel, config)

weather = {}
covariates = {}
for year, ds in weatherbundle.yearbundles(futureyear):
    if year in range(2001, 2011) + [futureyear]:
        ds = ds.isel({'hierid': shapenum})
        if year == 2001:
            print ','.join([variable for variable in ds])
        for variable in ds:
            print "%d: %s..." % (year, ','.join(map(str, ds[variable].values[:10])))
        weather[year] = {variable: ds[varliable].values for variable in ds}
        covariates[year] = covariates.get_update(region, year, ds)
            
lib.show_header("Covariates:")
for year in covariates:
    print ','.join(covariates[year].keys())
    print "%d: %s" % (year, ','.join([covariates[year][key] for key in covariates[year]]))

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [futureyear], shapenum)

## Computations
# decide on a covariated variable
variable = [csvv['prednames'][ii] for ii in range(len(csvv['prednames'])) if csvv['covarnames'][ii] != '1'][0]

for year in [2001, futureyear]:
    lib.show_header("Calc. of %s coefficient in %d (%f reported)" % (variable, year, lib.excind(calcs, year-1, 'coeff-' + variable)))
    lib.show_coefficient(csvv, preds, year, variable, covariates[year])

calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename], specconf=specconf, config=config, standard=False)
    
print formatting.format_julia(calculation)
exit()

coefflist = ['coeff-tas'] + ['coeff-tas%d' % ii for ii in range(2, polypower + 1)]

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))
lines.append("bl1(weather) = sum([%s]' * weather)" % ', '.join(["%.12g" % lib.excind(calcs, 2000, coeff) for coeff in coefflist]))
lines.append("bl2(weather) = bl1([%s])" % '; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]))
terms = []
for year in range(2001, 2011):
    terms.append("bl2(weather_%d)" % (year))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (outputs[futureyear]['rebased']))

lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "eff1(weather) = sum([%s]' * weather)" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "eff2(weather) = eff1([%s])" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]))]
lines.append("eff2(weather_%d) - %.12g" % (futureyear, lib.excind(calcs, 2000, 'baseline')))
lib.show_julia(lines)

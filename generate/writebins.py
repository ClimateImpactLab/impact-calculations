import sys, os, csv
import standard
from impacts import weather, effectset
from adaptation import adapting_curve

get_model = effectset.get_model_server
pvals = effectset.ConstantPvals(.5)
#pvals = effectset.OnDemandRandomPvals()

basedir = '/shares/gcp/BCSD/grid2reg/cmip5'

with open("allbins.csv", 'w') as fp:
    writer = csv.writer(fp)
    writer.writerow(['region', 'year', 'model', 'result', 'bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_18C_23C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC'])

with open("allpreds.csv", 'w') as fp:
    writer = csv.writer(fp)
    writer.writerow(['region', 'year', 'meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'log gdppc', 'log popop'])

def result_callback(region, year, result, calculation, model):
    with open("allbins.csv", 'a') as fp:
        writer = csv.writer(fp)
        curve = adapting_curve.region_stepcurves[region].curr_curve
        writer.writerow([region, year, model, result[0]] + list(curve.yy))

def push_callback(region, year, application, get_predictors):
    with open("allpreds.csv", 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)
        writer.writerow([region, year] + list(predictors[0]))

standard.preload()

for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(basedir):
    if clim_scenario != 'rcp85':
        continue
    print clim_scenario, clim_model
    for econ_model, econ_scenario, economicmodel in adapting_curve.iterate_econmodels():
        if econ_model != 'OECD Env-Growth' or econ_scenario[0:4] != 'SSP3':
            continue
        print econ_scenario, econ_model

        standard.produce('.', weatherbundle, economicmodel, get_model, pvals, do_only="interpolation", country_specific=False, result_callback=result_callback, push_callback=push_callback, do_farmers=False)
        break
    break

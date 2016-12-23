import glob, os, csv
from impacts.conflict import standard
from generate.weather import SingleWeatherBundle
from climate.dailyreader import DailyWeatherReader
from adaptation.econmodel import iterate_econmodels
import curvegen, effectset

def produce(targetdir, weatherbundle, qvals, do_only=None, suffix=''):
    historicalbundle = SingleWeatherBundle(DailyWeatherReader("/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc", 1991, 'tas'))
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'OECD Env-Growth').next()

    # if do_only is None or do_only == 'acp':
    #     # ACP response
    #     calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_violentcrime', weatherbundle, qvals['ACRA_violentcrime'])
    #     effectset.write_ncdf(targetdir, "ViolentCrime", weatherbundle, calculation, None, "Violent crime using the ACP response function.", dependencies + weatherbundle.dependencies, suffix=suffix)
    #     calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_propertycrime', weatherbundle, qvals['ACRA_propertycrime'])
    #     effectset.write_ncdf(targetdir, "PropertyCrime", weatherbundle, calculation, None, "Property crime using the ACP response function.", dependencies + weatherbundle.dependencies, suffix=suffix)

    if do_only is None or do_only == 'interpolation':
        predgen1 = curvegen.WeatherPredictorator(historicalbundle, econmodel, 15, 3, 2005)

        ## Full interpolation
        for filepath in glob.glob("/shares/gcp/social/parameters/conflict/conflict_single_stage_12202016/*.csvv"):
            basename = os.path.basename(filepath)[:-5]

            predicted_betas = {'hasprcp': False}
            def betas_callback(variable, region, predictors, betas):
                if region in predicted_betas:
                    predicted_betas[region][variable] = betas
                else:
                    predicted_betas[region] = {variable: betas, 'pred': predictors}
                if variable == 'prcp':
                    predicted_betas['hasprcp'] = True

            thisqvals = qvals[basename]
            #try:
            calculation, dependencies, predvars = standard.prepare_csvv(filepath, thisqvals, betas_callback)
            #except:
            #    print "SKIPPING " + basename
            #    continue

            columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename, weatherbundle, calculation, predgen1.get_baseline, "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies, suffix=suffix)

            if is_tavg:
                finalvar = 'response'
            else:
                finalvar = 'sum'
            with open(os.path.join(targetdir, basename + '-final.csv'), 'w') as fp:
                writer = csv.writer(fp)
                header = ['region'] + range(columns[finalvar].shape[0])
                writer.writerow(header)
                for ii in range(len(weatherbundle.regions)):
                    row = [weatherbundle.regions[ii]] + list(columns[finalvar][:, ii])
                    writer.writerow(row)

            with open(os.path.join(targetdir, basename + '-betas.csv'), 'w') as fp:
                writer = csv.writer(fp)

                header = ['region'] + predvars[1:] + ['beta-temp']
                if predicted_betas['hasprcp']:
                    header += ['beta-prcp1', 'beta-prcp2', 'beta-prcp3']
                writer.writerow(header)

                for region in weatherbundle.regions:
                    if region not in predicted_betas:
                        row = [region] + ['NA'] * (len(header) - 1)
                    else:
                        row = [region] + list(predicted_betas[region]['pred']) + [predicted_betas[region]['temp']]
                        if predicted_betas['hasprcp']:
                            row += predicted_betas[region]['prcp']
                    writer.writerow(row)

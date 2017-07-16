import os
import numpy as np
from netCDF4 import Dataset
from adaptation import covariates, econmodel
from generate import agglib, nc4writer
from impactlab_tools.utils import paralog

POOR_THRESHOLD = 1913.1882
RICH_THRESHOLD = 4603.9224

CLAIM_TIMEOUT = 10*60*60
statman = paralog.StatusManager('indiamerge', "impacts.mortality.combine_india", 'logs', CLAIM_TIMEOUT)

for batch, clim_scenario, clim_model, econ_scenario, econ_model, targetdir in agglib.iterresults("/shares/gcp/outputs/mortality/impacts-crypto"):
    if not statman.claim(targetdir):
        continue

    print "Claimed " + targetdir
    
    for filename in os.listdir(targetdir):
        if filename[-4:] == '.nc4' and '-combined' in filename and '-aggregated' not in filename and '-levels' not in filename and '-indiamerge' not in filename:
            print filename

            if os.path.exists(os.path.join(targetdir, filename[:-4] + '-indiamerge.nc4')):
                continue
            
            # Find the corresponding India
            if filename.startswith("global_interaction_Tmean-POLY-4"):
                india_basename = 'IND_moratlity_poly_4_GMFD_062717'
                if '-histclim' in filename:
                    india_basename = india_basename + '-histclim'
            elif filename.startswith("global_interaction_Tmean-POLY-5"):
                india_basename = 'IND_moratlity_poly_5_GMFD_062717'
                if '-histclim' in filename:
                    india_basename = india_basename + '-histclim'
            elif filename.startswith("global_interaction_Tmean-CSpline-LS"):
                india_basename = 'IND_moratlity_cubic_splines_GMFD_062717'
                if '-histclim' in filename:
                    india_basename = india_basename + '-histclim'
            else:
                print "Could not find India file to correspond to " + filename
                continue

            if '-costs' not in filename:
                print "Normal Merge"
                try:
                    reader_rich = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
                    reader_poor = Dataset(os.path.join(targetdir, india_basename + '.nc4'), 'r', format='NETCDF4')
                
                    dependencies = []
                    covariator = covariates.EconomicCovariator(econmodel.SSPEconomicModel(econ_model, econ_scenario, dependencies), 1, 2015)
                    
                    writer, regions, years = nc4writer.create_derivative(targetdir, reader_rich, filename[:-4] + '-indiamerge', " combined with India", dependencies)
                    srcvalues_rich = reader_rich.variables['rebased'][:, :]
                    srcvalues_poor = reader_poor.variables['rebased'][:, :]
                except Exception as ex:
                    print str(ex)
                    continue
                
                dstvalues = np.zeros((len(years), len(regions)))
                for tt in range(len(years)):
                    print years[tt]
                    for ii in range(len(regions)):
                        covars = covariator.get_econ_predictors(regions[ii])
                        if years[tt] >= 2015:
                            covariator.get_update(regions[ii], years[tt], None)

                        if covars['gdppc'] <= POOR_THRESHOLD:
                            dstvalues[tt, ii] = srcvalues_poor[tt, ii]
                        elif covars['gdppc'] >= RICH_THRESHOLD:
                            dstvalues[tt, ii] = srcvalues_rich[tt, ii]
                        else:
                            richness = (covars['gdppc'] - POOR_THRESHOLD) / (RICH_THRESHOLD - POOR_THRESHOLD)
                            dstvalues[tt, ii] = srcvalues_poor[tt, ii] * (1 - richness) + srcvalues_rich[tt, ii] * richness
                            
                agglib.copy_timereg_variable(writer, reader_rich.variables['rebased'], 'rebased', dstvalues, "(indiamerge)")

                reader_rich.close()
                reader_poor.close()
                writer.close()

            else: # Costs!
                print "Costs Merge"
                try:
                    reader_rich = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
                    reader_rich_base = Dataset(os.path.join(targetdir, filename.replace('-costs', '')), 'r', format='NETCDF4')

                    writer, regions, years = nc4writer.create_derivative(targetdir, reader_rich_base, filename[:-4] + '-indiamerge', " combined with India", [])
                except Exception as ex:
                    print str(ex)
                    continue

                dstvalues = np.zeros((len(years), len(regions)))
                for key in ['costs_ub', 'costs_lb', 'costs_ub_cum', 'costs_lb_cum']:
                    dependencies = []
                    covariator = covariates.EconomicCovariator(econmodel.SSPEconomicModel(econ_model, econ_scenario, dependencies), 1, 2015)

                    srcvalues_rich = reader_rich.variables[key][:, :]
                    for tt in range(len(years)):
                        print years[tt]
                        for ii in range(len(regions)):
                            covars = covariator.get_econ_predictors(regions[ii])
                            if years[tt] >= 2015:
                                covariator.get_update(regions[ii], years[tt], None)

                            if tt == 0:
                                dstvalues[tt, ii] = 0
                            elif covars['gdppc'] <= POOR_THRESHOLD:
                                dstvalues[tt, ii] = 0
                            elif covars['gdppc'] >= RICH_THRESHOLD:
                                dstvalues[tt, ii] = dstvalues[tt - 1, ii] + (srcvalues_rich[tt, ii] - srcvalues_rich[tt - 1, ii])
                            else:
                                richness = (covars['gdppc'] - POOR_THRESHOLD) / (RICH_THRESHOLD - POOR_THRESHOLD)
                                dstvalues[tt, ii] = dstvalues[tt - 1, ii] + (srcvalues_rich[tt, ii] - srcvalues_rich[tt - 1, ii]) * richness
                        
                    agglib.copy_timereg_variable(writer, reader_rich.variables[key], key, dstvalues, "(indiamerge)")

                reader_rich.close()
                reader_rich_base.close()
                writer.close()

    statman.release(targetdir, "Complete")

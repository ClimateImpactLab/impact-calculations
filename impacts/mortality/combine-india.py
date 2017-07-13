from generate import agglib, nc4writer

POOR_THRESHOLD = 1913.1882
RICH_THRESHOLD = 4603.9224

for batch, clim_scenario, clim_model, econ_scenario, econ_model, targetdir in agglib.iterresults("/shares/gcp/outputs/mortality/impacts-crypto"):
    for filename in os.listdir(targetdir):
        if filename[-4:] == '.nc4' and '-combined' in filename and '-aggregated' not in filename and '-levels' not in filename:
            print filename

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

            covariator = covariates.EconomicCovariator(econmodel.SSPEconomicModel(econ_model, econ_scenario), 1, 2015)

            if '-costs' not in filename:
                reader_rich = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
                reader_poor = Dataset(os.path.join(targetdir, india_basename + '.nc4'), 'r', format='NETCDF4')

                writer, regions, years = nc4writer.create_derivative(targetdir, reader_rich, filename[:-4] + '-indiamerge', " combined with India", covariator.dependencies)

                covariator = covariates.EconomicCovariator(economicmodel, 1, 2015)
            
                dstvalues = np.zeros((len(years), len(regions)))
                srcvalues_rich = reader_rich.variables['rebased'][:, :]
                srcvalues_poor = reader_poor.variables['rebased'][:, :]
                for ii in range(len(regions)):
                    covariates = get_econ_predictors(regions[ii])
                    for tt in range(len(years)):
                        if years[tt] >= 2015:
                            covariates.get_update(regions[ii], years[tt], None)

                        if covariates['gdppc'] <= POOR_THRESHOLD:
                            dstvalues[tt, ii] = srcvalues_poor[tt, ii]
                        elif covariates['gdppc'] >= RICH_THRESHOLD:
                            dstvalues[tt, ii] = srcvalues_rich[tt, ii]
                        else:
                            richness = (covariates['gdppc'] - POOR_THRESHOLD) / (RICH_THRESHOLD - POOR_THRESHOLD)
                            dstvalues[tt, ii] = srcvalues_poor[tt, ii] * (1 - richness) + srcvalues_rich[tt, ii] * richness

                agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(indiamerge)")

                reader_rich.close()
                reader_poor.close()
                writer.close()

            else: # Costs!
                reader_rich = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
                reader_rich_base = Dataset(os.path.join(targetdir, filename.replace('-costs', '')), 'r', format='NETCDF4')

                writer, regions, years = nc4writer.create_derivative(targetdir, reader_rich_base, filename[:-4] + '-indiamerge', " combined with India", covariator.dependencies)

                dstvalues = np.zeros((len(years), len(regions)))
                srcvalues_rich = reader_rich.variables['rebased'][:, :]
                for ii in range(len(regions)):
                    covariates = get_econ_predictors(regions[ii])
                    for tt in range(len(years)):
                        if years[tt] >= 2015:
                            covariates.get_update(regions[ii], years[tt], None)

                        if tt == 0:
                            dstvalues[tt, ii] = 0
                        elif covariates['gdppc'] <= POOR_THRESHOLD:
                            dstvalues[tt, ii] = 0
                        elif covariates['gdppc'] >= RICH_THRESHOLD:
                            dstvalues[tt, ii] = dstvalues[tt - 1, ii] + (srcvalues_rich[tt, ii] - srcvalues_rich[tt - 1, ii])
                        else:
                            richness = (covariates['gdppc'] - POOR_THRESHOLD) / (RICH_THRESHOLD - POOR_THRESHOLD)
                            dstvalues[tt, ii] = dstvalues[tt - 1, ii] + (srcvalues_rich[tt, ii] - srcvalues_rich[tt - 1, ii]) * richness
                        
                agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(indiamerge)")

                reader_rich.close()
                reader_poor.close()
                writer.close()

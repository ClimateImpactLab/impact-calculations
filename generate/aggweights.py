## Construct population weights for each SSP, using default covariate definitions

import csv
from adaptation import covariates
from datastore import population
from impactlab_tools.utils import files

halfweight = population.SpaceTimeBipartiteData(1950, 2100, None)

#for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order():
for econ_model, econ_scenario, economicmodel in covariates.iterate_econmodels():
    if econ_model == 'high':
        continue
    
    print(econ_scenario)

    stweight = halfweight.load(1950, 2100, econ_model, econ_scenario)

    with open(files.sharedpath("outputs/covariates/population/%s.csv" % econ_scenario), 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(["region", "year", "population"])
        
        for region in stweight.regions:
            population = stweight.get_time(region)
            for yy in range(len(population)):
                writer.writerow([region, 1950 + yy, population[yy]])

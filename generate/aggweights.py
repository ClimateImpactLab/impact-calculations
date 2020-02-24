import csv
from adaptation import covariates
from datastore import population

halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)

#for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order():
for econ_model, econ_scenario, economicmodel in covariates.iterate_econmodels():
    if econ_model == 'high':
        continue
    
    print(econ_scenario)

    stweight = halfweight.load(1981, 2100, econ_model, econ_scenario)

    with open("/shares/gcp/outputs/covariates/population/%s.csv" % econ_scenario, 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(["region", "year", "population"])
        
        for region in stweight.regions:
            population = stweight.get_time(region)
            for yy in range(len(population)):
                writer.writerow([region, 1981 + yy, population[yy]])
                
        

    # Estimate E[T]

    # Estimate E[D[T]], E[D[Y]], E[D[P]]

    # Estimate E[T D[T]], E[T D[Y]], E[T D[P]]

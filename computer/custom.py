import os, sys, cStringIO
sys.path.append("../extract/lib")
sys.path.append("../../../../../research/gcp/impact-calculations")

import results
from impacts import labor, mortality
from generate import checks

do_fast = True

def count_results(iterator, check_doit):
    stdout_ = sys.stdout
    sys.stdout = stream = cStringIO.StringIO()

    complete = 0
    missingness = 0
    incomplete = 0
    toaggregate = 0
    failures = {} # {message -> targetdir}
    
    for batch, rcp, model, iam, ssp, targetdir in iterator:
        status = None
        for model in models:
            for variation in variations:
                if variation == '-costs':
                    if not os.path.exists(os.path.join(targetdir, model + variation + '.nc4')):
                        status = 'toaggregate'
                        break
                else:
                    if not os.path.exists(os.path.join(targetdir, model + variation + '.nc4')):
                        status = 'missingness'
                        continue

                    if check_doit(targetdir, model + variation, ''):
                        status = 'incomplete'
                        break
                
                for aggregate in aggregated:
                    if not os.path.exists(os.path.join(targetdir, model + variation + aggregate + '.nc4')):
                        print "Missing", os.path.join(targetdir, model + variation + aggregate + '.nc4')
                        status = 'toaggregate'
                        break

                    if variation != '-costs' and not checks.check_result_100years(os.path.join(targetdir, model + variation + aggregate + '.nc4'), regioncount=5665):
                        print "Failed aggregate", os.path.join(targetdir, model + variation + aggregate + '.nc4')

                        status = 'toaggregate'
                        break

                if status is not None and status != 'missingness':
                    break
            if status is not None and status != 'missingness':
                break

        if status == 'incomplete':
            incomplete += 1
        elif status == 'toaggregate':
            toaggregate += 1
        else:
            with open(os.path.join(targetdir, "COMPLETE"), 'w') as fp:
                fp.write("2016-12-23")
            if status == 'missingness':
                missingness += 1
            else:
                complete += 1

    sys.stdout = stdout_

    return complete, missingness, incomplete, toaggregate, stream.getvalue()

if do_fast:
    checks.do_skip_check = True

print 'C', 'M', 'I', 'A'

models = ['global_interaction_Tmean-POLY-4-AgeSpec-' + cohort for cohort in ['young', 'older', 'oldest', 'combined']]
variations = ['', '-noadapt', '-incadapt', '-histclim', '-costs']
aggregated = ['-aggregated', '-levels']

print "4th-order Polynomial Median:"
iterator = results.iterate_batch("/shares/gcp/outputs/mortality/impacts-harvester", 'median')
complete, missingness, incomplete, toaggregate, output4 = count_results(iterator, mortality.allmodels.check_doit)
print complete, missingness, incomplete, toaggregate

print output4

print "4th-order Polynomial Monte Carlo:"
iterator = results.iterate_montecarlo("/shares/gcp/outputs/mortality/impacts-harvester")
complete, missingness, incomplete, toaggregate, output3 = count_results(iterator, mortality.allmodels.check_doit)
print complete, missingness, incomplete, toaggregate

models = ['global_interaction_Tmean-CSpline-LS-AgeSpec-' + cohort for cohort in ['young', 'older', 'oldest', 'combined']]
variations = ['', '-noadapt', '-incadapt', '-histclim', '-costs']
aggregated = ['-aggregated', '-levels']

print "Cubic Spline Median:"
iterator = results.iterate_batch("/shares/gcp/outputs/mortality/impacts-subterran", 'median')
complete, missingness, incomplete, toaggregate, output2 = count_results(iterator, mortality.allmodels.check_doit)
print complete, missingness, incomplete, toaggregate

print output2

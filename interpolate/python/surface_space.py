import csv, os
import numpy as np
import statsmodels.api as sm
from sysreg import SUR
from scipy.stats import multivariate_normal
from openest.lincombo import hierregress, montecarlo
import utils

def make_XX(predictors):
    predictors = np.array(predictors)

    # Add intercept column
    return np.hstack((np.ones((predictors.shape[0], 1)), predictors))

def prepare_args(means, serrs, predictors, allowinf=False):
    XX = make_XX(predictors)
    assert len(means) == len(serrs)
    assert len(means) == XX.shape[0]

    serrs = np.array(serrs)
    means = np.array(means)
    valid = serrs > 0.0
    if allowinf:
        serrs[np.logical_not(valid)] = np.inf
        valid = serrs > 0.0
    means = means[valid]
    serrs = serrs[valid]
    XX = XX[valid, :]

    return means, serrs, XX

def pooled_fit(means, serrs, predictors):
    means, serrs, XX = prepare_args(means, serrs, predictors)
    return sm.WLS(means, XX, weights=1/(np.array(serrs)**2)).fit()

def pooled(means, serrs, predictors, seed=None, median=False):
    fit = pooled_fit(means, serrs, predictors)

    if median:
        return fit.params
    else:
        if seed is not None:
            np.random.seed(seed)
        return multivariate_normal.rvs(fit.params, fit.cov_HC0)

def hierreg_fit(means, serrs, predictors):
    means, serrs, XX = prepare_args(means, serrs, predictors)
    alltau, allmus, allbetahats = hierregress.lincombo_hierregress(means, serrs, XX)
    return allmus

def monteco_fit(means, serrs, predictors):
    means, serrs, XX = prepare_args(means, serrs, predictors)
    return montecarlo.regress_distribution(means, serrs, XX)

def seemur_fit(meanses, serrses, predictorses):
    """Estimate an SUR for all bins.
    meanses, serrses: lists of lists of the estimated values and their std. errors, one list per bin
    predictorses: list of arrays of predictors, not including an intercept, corresponding to each bin
    """
    # Collect all regressions into sys
    sys = []
    for ii in range(len(meanses)):
        # Check sizes, add an intercept; replace serr=0 and mean=NA with serr=inf
        means, serrs, XX = prepare_args(meanses[ii], serrses[ii], predictorses[ii], allowinf=True)
        # Reweight observations by the std. error
        for jj in range(len(means)):
            if serrs[jj] == np.inf:
                means[jj] = 0.
            else:
                means[jj] /= serrs[jj]
            XX[jj, :] /= serrs[jj]
        # Collect into the system, as ordered pairs of means, XX
        sys.append(means)
        sys.append(XX)

    # Fit the SUR model
    return SUR(sys).fit()

def single_standard(means, serrs, predictors, seed):
    # Monte Carlo method: dropped because doesn't handle outliers well
    #dist = monteco_fit(means, serrs, predictors)
    #if seed is None:
    #    return dist.mean()
    #np.random.seed(seed)
    #return dist.rvs()

    # Weighted pooled
    fit = pooled_fit(means, serrs, predictors)
    if seed is None:
        return fit.params
    np.random.seed(seed)
    return multivariate_normal.rvs(fit.params, fit.cov_HC0)

def standard(meanses, serrses, predictorses, seed):
    # Seemingly unrelated regression (SUR)
    fit = seemur_fit(meanses, serrses, predictorses)
    params = np.array(map(lambda x: x[0], fit.params))

    if seed is None:
        return params

    np.random.seed(seed)
    return multivariate_normal.rvs(params, fit.cov_params())

def all_predictors(predictorsdir, predcols, dependencies, allowinf=False):
    for binlo, binhi, fp in utils.all_predictors(predictorsdir, dependencies):
        reader = csv.reader(fp)
        header = reader.next()

        means = []
        serrs = []
        predictors = []
        for row in reader:
            serr = float(row[header.index('serr')])
            if np.isfinite(serr) or allowinf:
                means.append(float(row[header.index('coef')]))
                serrs.append(serr)
                predictors.append([utils.get_predcol(row, header, predcol, binlo, binhi) for predcol in predcols])

        yield binlo, binhi, means, serrs, predictors

if __name__ == '__main__':
    import sys
    from helpers import files
    import helpers.header as headre

    do_singlebin = False
    do_leaveone = False

    predictorsdir = sys.argv[1]
    predcols = ['meandays_self', 'log gdppc', 'log popop']

    dependencies = []

    if do_leaveone:
        with open("leaveones.csv", 'w') as fp:
            writer = csv.writer(fp, lineterminator='\n')
            writer.writerow(['binlo', 'binhi', 'intercept_coef', 'bindays_coef', 'gdppc_coef', 'popop_coef', 'intercept_serr', 'bindays_serr', 'gdppc_serr', 'popop_serr'])

            todrop = 0

            while True:
                print todrop + 1
                binlos = []
                binhis = []
                meanses = []
                serrses = []
                predictorses = []
                for binlo, binhi, means, serrs, predictors in all_predictors(predictorsdir, predcols, dependencies, allowinf=True):
                    if len(means) < todrop:
                        break

                    means = means[:todrop] + means[todrop+1:]
                    serrs = serrs[:todrop] + serrs[todrop+1:]
                    predictors = predictors[:todrop] + predictors[todrop+1:]

                    binlos.append(binlo)
                    binhis.append(binhi)
                    meanses.append(means)
                    serrses.append(serrs)
                    predictorses.append(predictors)

                if len(means) < todrop:
                    break

                fit = seemur_fit(meanses, serrses, predictorses)
                for jj in range(len(binlos)):
                    if binlos[jj] == 28.:
                        print fit.params[jj*4:(jj+1)*4][2]
                    writer.writerow([binlos[jj], binhis[jj]] + map(lambda x: x[0], fit.params[jj*4:(jj+1)*4]) + fit.bse[jj*4:(jj+1)*4].tolist())

                todrop += 1
            exit()

    if do_singlebin:
        with open('singlebin.csv', 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['mean', 'serr', 'intercept', 'binday', 'loggdppc', 'logpopop'])
            for binlo, binhi, means, serrs, predictors in all_predictors(predictorsdir, predcols, dependencies):
                print binlo, binhi
                for ii in range(len(means)):
                    writer.writerow([means[ii], serrs[ii], 1.] + predictors[ii])
                break
        exit()

    rowsets = {} # {method: (binlows, rows)}
    for method in ['seemur', 'pooled', 'hiereg', 'montec']:
        print method
        binlos = []
        rows = []

        if method == 'seemur':
            binhis = []
            meanses = []
            serrses = []
            predictorses = []
            for binlo, binhi, means, serrs, predictors in all_predictors(predictorsdir, predcols, dependencies, allowinf=True):
                binlos.append(binlo)
                binhis.append(binhi)
                meanses.append(means)
                serrses.append(serrs)
                predictorses.append(predictors)

            fit = seemur_fit(meanses, serrses, predictorses)
            for jj in range(len(binlos)):
                rows.append([binlos[jj], binhis[jj]] + map(lambda x: x[0], fit.params[jj*4:(jj+1)*4]) + fit.bse[jj*4:(jj+1)*4].tolist())
        else:
            for binlo, binhi, means, serrs, predictors in all_predictors(predictorsdir, predcols, dependencies):
                # Write out the uncertainty weighted lowest observed value
                print binlo, binhi, np.min([means[ii] / (1 + serrs[ii]**2) for ii in range(len(means))])

                binlos.append(binlo)
                if method == 'pooled':
                    fit = pooled_fit(means, serrs, predictors)
                    rows.append([binlo, binhi] + fit.params.tolist() + fit.HC0_se.tolist())
                elif method == 'hiereg':
                    allmus = hierreg_fit(means, serrs, predictors)
                    rows.append([binlo, binhi] + [np.mean(hierregress.get_sampled_column(allmus, jj)) for jj in range(4)] + [np.std(hierregress.get_sampled_column(allmus, jj)) for jj in range(4)])
                elif method == 'montec':
                    fit = monteco_fit(means, serrs, predictors)
                    rows.append([binlo, binhi] + fit.mean().tolist() + fit.std().tolist())
                else:
                    raise "Unknown method."

        rowsets[method] = (binlos, rows)

    filename = os.path.basename(predictorsdir).replace('predictors', 'surface') + '.csv'
    with open(files.sharedpath('social/adaptation/' + filename), 'w') as fp:
        headre.write(fp, "Coefficient coefficients for interpolation and adaptation.",
                     headre.dated_version('MORTALITY_SPACE'), dependencies,
                     {'method': ('Estimation method (seemur = SUR, pooled = weighted OLS, hiereg = Bayesian hierarchical, montec = dep. var. boostrap', 'str'),
                      'binlo': ('Lower bound on a given bin', 'deg. C'),
                      'binhi': ('Upper bound on a given bin', 'deg. C'),
                      'intercept_coef': ('Intercept coefficient mean', 'log mortality rate / day'),
                      'intercept_serr': ('Intercept coefficient std. err.', 'log mortality rate / day'),
                      'bindays_coef': ('Average temperature coefficient mean', 'log mortality rate / day / day'),
                      'bindays_serr': ('Intercept coefficient std. err.', 'log mortality rate / day / day'),
                      'gdppc_coef': ('GDP per capita coefficient mean', 'log mortality rate / day / USD$'),
                      'gdppc_serr': ('GDP per capita std. err.', 'log mortality rate / day / USD$'),
                      'popop_coef': ('Population-weighted population density coefficient mean', 'log mortality rate / day / (ppl/km^2)'),
                      'popop_serr': ('population density std. err.', 'log mortality rate / day / (ppl/km^2)')})

        writer = csv.writer(fp, lineterminator='\n')
        writer.writerow(['method', 'binlo', 'binhi', 'intercept_coef', 'bindays_coef', 'gdppc_coef', 'popop_coef', 'intercept_serr', 'bindays_serr', 'gdppc_serr', 'popop_serr'])
        for method in ['seemur', 'pooled', 'hiereg', 'montec']:
            binlos, rows = rowsets[method]
            for ii in np.argsort(binlos):
                writer.writerow([method] + rows[ii])

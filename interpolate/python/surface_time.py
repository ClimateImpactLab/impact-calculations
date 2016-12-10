import csv, os
import numpy as np
import statsmodels.formula.api as smf
from scipy.stats import multivariate_normal
from helpers import files
import helpers.header as headre
import utils

# Minimum level to offset others
def minimum_effect(means, serrs):
    if np.all(np.sign(means) > 0):
        return 0

    return np.min([means[ii] / (1 + serrs[ii]**2) for ii in range(len(means))])

# Return indices for means to use (may be duplicated or missing as negative values are encountered)
def positive_only(means, times, groups):
    indices = []

    last_positive = {} # {group: index-of-last-positive}
    order = np.argsort(times)
    for ii in order:
        if means[ii] > 0:
            indices.append(ii)
            last_positive[groups[ii]] = ii
        elif groups[ii] in last_positive:
            indices.append(last_positive[groups[ii]])

    return indices

def pooled_fit(means, serrs, times, groups, predictors):
    predictors = np.array(predictors)
    assert len(means) == len(serrs)
    assert len(means) == len(times)
    assert len(means) == len(groups)
    assert len(means) == predictors.shape[0]

    assert np.all(np.sign(means) == np.sign(means[0])), "All predictors must be of the same sign."

    # Generate P_i t_i columns
    predictorstime = np.array(predictors)
    for jj in range(predictorstime.shape[1]):
        predictorstime[:,jj] *= times

    predictors = np.hstack((predictors, np.transpose(np.matrix(times)), predictorstime))

    return smf.MixedLM(np.log(means), predictors, groups=groups).fit()

def pooled(means, serrs, times, groups, predictors, seed=None, median=False):
    fit = pooled_fit(means, serrs, times, groups, predictors)

    taustart = np.array(predictors).shape[1]
    if median:
        return fit.params[taustart:]
    else:
        if seed is not None:
            np.random.seed(seed)
        return multivariate_normal.rvs(fit.params[taustart:], fit.cov_params[taustart:, taustart:])

def all_predictors(dependencies):
    for binlo, binhi, fp in utils.all_predictors(files.sharedpath('social/adaptation/predictors-time'), dependencies):
        reader = csv.reader(fp)
        header = reader.next()

        means = []
        serrs = []
        times = []
        groups = []
        predictors = []
        for row in reader:
            serr = float(row[header.index('serr')])
            if np.isfinite(serr):
                means.append(float(row[header.index('coef')]))
                serrs.append(serr)
                times.append((float(row[header.index('year1')]) + float(row[header.index('year2')])) / 2)
                groups.append(row[header.index('group')])
                predictors.append([])

        # Adjust all means against minimum effect
        means = np.array(means) - minimum_effect(means, serrs)
        # Take only those positive relative to this minimum effect
        indices = np.where(means > 0)

        yield binlo, binhi, means[indices], np.array(serrs)[indices], np.array(times)[indices], np.array(groups)[indices], np.array(predictors)[indices]

if __name__ == '__main__':
    dependencies = []

    binlos = []
    rows = []
    for binlo, binhi, means, serrs, times, groups, predictors in all_predictors(dependencies):
        fit = pooled_fit(means, serrs, times, groups, predictors)
        binlos.append(binlo)
        rows.append([binlo, binhi, fit.params[0], fit.bse[0]])

    with open(files.sharedpath('social/adaptation/outputs/surface-time.csv'), 'w') as fp:
        headre.write(fp, "NOT READY (based on preliminary input files)! Coefficient coefficients for adaptation rates.", # TODO: Remove NOT READY when input data has headers
                     headre.dated_version('MORTALITY_TIME'), dependencies,
                     {'binlo': ('Lower bound on a given bin', 'deg. C'),
                      'binhi': ('Upper bound on a given bin', 'deg. C'),
                      'trend_coef': ('Trend coefficient mean', 'log(log mortality rate / day)/year'),
                      'trend_serr': ('Trend coefficient std. err.', 'log(log mortality rate / day)/year')})

        writer = csv.writer(fp, lineterminator='\n')
        writer.writerow(['binlo', 'binhi', 'trend_coef', 'trend_serr'])
        for ii in np.argsort(binlos):
            writer.writerow(rows[ii])

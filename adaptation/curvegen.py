"""Classes that extend the open-estimate curve generation system for
econometric results.

Econometric models used by the CIL typically have covariates that
describe the potential for sensitivity to adapt to future climates and
wealth. The curves generated for a given region and year, then, are
conditional on these climate and socioeconomic covariates. These
classes encode the logic for using CSVVs to use these covariates. See
docs/CSVV File Format Specification.pdf for more information.

The most important class here is CSVVCurveGenerator, which embodies
the adaptation logic used in CIL. A set of "gamma" coefficients-- the
result of an interactions between covariates and weather predictors--
define the adaptation curve:
    y = sum_k (gamma_k0 + sum_l gamma_kl z_l) x_k
  where z_l is the z_l is a covariate and x_k is a weather predictor.

In a given year and region, these gamma coefficients can be applied to
covariates to produce a corresponding set of "beta" coefficients,
which are then applied to predictors:
    beta_k = gamma_k0 + sum_l gamma_kl z_l
    y = sum_k beta_k x_k

This two-step process is used both because the beta_k parameters are
of interest in their own right, and because the expression relating
gammas to a beta may be arbitrarily complicated (e.g., using
elasticities in the case of MLE or accounting for clipping).

"""

import copy
import numpy as np
from openest.generate.curvegen import *
from openest.generate import checks, fast_dataset, formatting, smart_curve, formattools
from openest.models.curve import FlatCurve

region_curves = {}

class CSVVCurveGenerator(CurveGenerator):
    """

    Parameters
    ----------
    prednames : sequence of str
        Independent variable names.
    indepunits : sequence of str
        Independent variable units.
    depenunit : str
        Dependent variable unit.
    csvv : dict
        CSVV dict as produced by `interpret.container.produce_csvv`.
    betalimits: dict
    """
    def __init__(self, prednames, indepunits, depenunit, csvv, betalimits=None, ignore_units=False):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunit)

        if betalimits is None:
            betalimits = {}
        assert isinstance(prednames, list) or isinstance(prednames, set) or isinstance(prednames, tuple)
        self.prednames = prednames
        self.csvv = csvv
        self.betalimits = betalimits

        if not ignore_units:
            for ii, predname in enumerate(prednames):
                if predname not in csvv['variables']:
                    print(("WARNING: Predictor %s definition not found in CSVV." % predname))
                else:
                    if 'unit' in csvv['variables'][predname]:
                        assert checks.loosematch(csvv['variables'][predname]['unit'], indepunits[ii]), "Units error for %s: %s <> %s" % (predname, csvv['variables'][predname]['unit'], indepunits[ii])

            if 'outcome' not in csvv['variables']:
                print("WARNING: Dependent variable definition not in CSVV.")
            else:
                assert checks.loosematch(csvv['variables']['outcome']['unit'], depenunit), "Dependent units %s does not match %s." % (csvv['variables']['outcome']['unit'], depenunit)

        self.fill_marginals()

    def fill_marginals(self):
        # Preprocessing
        self.constant = {} # {predname: constant}
        self.predcovars = {} # {predname: [covarname]}
        self.predgammas = {} # {predname: np.array}
        for predname in set(self.prednames):
            self.predcovars[predname] = []
            self.predgammas[predname] = []

            indices = [ii for ii, xx in enumerate(self.csvv['prednames']) if xx == predname]
            for index in indices:
                if self.csvv['covarnames'][index] == '1':
                    assert predname not in self.constant
                    self.constant[predname] = self.csvv['gamma'][index]
                else:
                    self.predcovars[predname].append(self.csvv['covarnames'][index])
                    self.predgammas[predname].append(self.csvv['gamma'][index])

            self.predgammas[predname] = np.array(self.predgammas[predname])

    def get_coefficients(self, covariates, debug=False):
        """Calculate the beta coefficient for each predictor.

        Typically, self.constant[predname] is a number or missing, and
        self.predgammas[predname] is a sequence of gammas
        corresponding to self.predcovars[predname]. However, in the
        case of sum-by-time entries, self.constant[predname] is either
        0 or an array_like of T numbers, self.predcovars[predname] is
        a list of length K, and self.predgammas[predname] is a T x K
        np.array matrix of the corresponding gammas.

        Parameters
        ----------
        covariates : dict
            Dictionary with string variable keys and float values. The keys in
            `covariates` must correspond to keys in `self.predcovars` and
            items in `self.predname`.
        debug : bool, optional
            If True, prints intermediate terms for debugging.

        Returns
        -------
        coefficients : dict
            With str keys giving variable names and values giving the
            corresponding float coefficients.

        """
        coefficients = {} # {predname: sum}
        for predname in set(self.prednames):
            if len(self.predgammas[predname]) == 0:
                try:
                    coefficients[predname] = self.constant[predname]
                except KeyError as e:
                    print("ERROR: Cannot find the uninteracted value for %s; is it in the CSVV?" % predname)
                    raise
            else:
                try:
                    coefficients[predname] = self.constant.get(predname, 0) + np.dot(self.predgammas[predname], np.array([covariates[covar] for covar in self.predcovars[predname]]))
                    if predname in self.betalimits and not np.isnan(coefficients[predname]):
                        coefficients[predname] = np.minimum(np.maximum(self.betalimits[predname][0], coefficients[predname]), self.betalimits[predname][1])
                    
                    if debug:
                        print((predname, coefficients[predname], self.constant.get(predname, 0), self.predgammas[predname], np.array([covariates[covar] for covar in self.predcovars[predname]])))
                except Exception as e:
                    print("Available covariates:")
                    print(covariates)
                    print("Requested covariates:")
                    print((self.predcovars[predname]))
                    raise

        return coefficients

    def get_marginals(self, covar):
        marginals = {} # {predname: sum}
        for predname in set(self.prednames):
            marginals[predname] = self.predgammas[predname][self.predcovars[predname].index(covar)]
        return marginals

    def get_curve(self, region, year, covariates=None):
        if covariates is None:
            covariates = {}
        raise NotImplementedError()

    def get_lincom_terms(self, region, year, predictors):
        raise NotImplementedError()

    def get_lincom_terms_simple(self, predictors, covariates=None):
        # Return in the order of the CSVV
        if covariates is None:
            covariates = {}
        terms = []
        for ii in range(len(self.csvv['prednames'])):
            predname = self.csvv['prednames'][ii]
            covarname = self.csvv['covarnames'][ii]
            if predname in self.prednames:
                term = self.get_lincom_terms_simple_each(predname, covarname, predictors, covariates)
            else:
                term = 0.0
            terms.append(term)

        return np.array(terms)
    
class FarmerCurveGenerator(DelayedCurveGenerator):
    """Handles different adaptation assumptions.

    Parameters
    ----------
    curvegen : openest.generate.curvegen.CurveGenerator-like
    covariator : adaptation.covariates.CombinedCovariator
    farmer : {'full', 'noadapt', 'incadapt'}
        Type of farmer adaptation.
    save_curve : bool, optional
        Do you want to save this curve in `adaptation.region_curves`?
    endbaseline : int
        Final year of the baseline period.
    """
    def __init__(self, curvegen, covariator, farmer='full', save_curve=True, endbaseline=2015):
        super(FarmerCurveGenerator, self).__init__(curvegen)
        self.covariator = covariator
        self.farmer = farmer
        self.save_curve = save_curve
        self.lincom_last_covariates = {}
        self.lincom_last_year = {}
        self.endbaseline = endbaseline

    def get_next_curve(self, region, year, *args, **kwargs):
        """

        Parameters
        ----------
        region : str
            Region code
        year : int
        args :
            We do nothing with this.
        kwargs :
            If `self.farmer` is 'full', pass `kwargs['weather']` to
            `self.covariator.offer_update()` 'ds'.

        Returns
        -------
        openest.generate.SmartCurve-like

        """
        if year < self.endbaseline:
            if region not in self.last_curves:
                covariates = self.covariator.get_current(region)
                curve = self.curvegen.get_curve(region, year, covariates)

                if self.save_curve:
                    region_curves[region] = curve

                return curve

            return self.last_curves[region]

        if self.farmer == 'full':
            covariates = self.covariator.offer_update(region, year, kwargs['weather'])
            curve = self.curvegen.get_curve(region, year, covariates)
        elif self.farmer == 'noadapt':
            curve = self.last_curves[region]
        elif self.farmer == 'incadapt':
            covariates = self.covariator.offer_update(region, year, None)
            curve = self.curvegen.get_curve(region, year, covariates)
        else:
            raise ValueError("Unknown farmer type " + str(self.farmer))

        if self.save_curve:
            region_curves[region] = curve

        return curve

    def get_partial_derivative_curvegen(self, covariate, covarunit):
        """
        Returns a CurveGenerator that calculates the partial
        derivative with respect to a covariate.
        """
        if self.farmer in ['noadapt', 'incadapt']:
            return ConstantCurveGenerator(self.indepunits, self.depenunit + '/' + covarunit, FlatCurve(0))

        return FarmerCurveGenerator(self.curvegen.get_partial_derivative_curvegen(covariate, covarunit),
                                    self.covariator, self.farmer, self.save_curve)
        
    def get_lincom_terms(self, region, year, predictors=None, origds=None):
        # Get last covariates
        if predictors is None:
            predictors = {}
        if self.lincom_last_year.get(region, None) == year:
            covariates = self.lincom_last_covariates[region]
        else:
            if region not in self.lincom_last_covariates:
                covariates = self.covariator.get_current(region)
            else:
                covariates = self.lincom_last_covariates[region]

            # Prepare next covariates
            if year < 2015:
                nextcovariates = self.covariator.get_current(region)
            elif self.farmer == 'full':
                nextcovariates = self.covariator.offer_update(region, year, origds) # don't use summed
            elif self.farmer == 'noadapt':
                nextcovariates = self.covariator.get_current(region)
            elif self.farmer == 'incadapt':
                nextcovariates = self.covariator.offer_update(region, year, None)

            self.lincom_last_covariates[region] = nextcovariates
            self.lincom_last_year[region] = year
        
        return self.curvegen.get_lincom_terms_simple(predictors, covariates)

    def get_lincom_terms_simple(self, predictors, covariates=None):
        if covariates is None:
            covariates = {}
        raise NotImplementedError()
    
    def get_csvv_coeff(self):
        return self.curvegen.get_csvv_coeff()

    def get_csvv_vcv(self):
        return self.curvegen.get_csvv_vcv()

class DifferenceCurveGenerator(CurveGenerator):
    """Currently just useful for performing lincom calculations."""
    def __init__(self, one, two, prednames, covarnames, onefunc, twofunc):
        assert one.indepunits == two.indepunits
        assert one.depenunit == two.depenunit
        super(DifferenceCurveGenerator, self).__init__(one.indepunits, one.depenunit)

        self.one = one
        self.two = two
        self.prednames = prednames
        self.covarnames = covarnames
        self.onefunc = onefunc
        self.twofunc = twofunc

    def get_lincom_terms_simple(self, predictors, covariates):
        one_preds = fast_dataset.FastDataset.subset(predictors, list(map(self.onefunc, self.prednames)))
        one_covars = {covar: covariates[self.onefunc(covar)] if covar != '1' else 1 for covar in self.covarnames}
        one_terms = self.one.get_lincom_terms_simple(one_preds, one_covars)

        two_preds = fast_dataset.FastDataset.subset(predictors, list(map(self.twofunc, self.prednames))).rename({self.twofunc(name): name for name in set(self.prednames)})
        two_covars = {covar: covariates[self.twofunc(covar)] if covar != '1' else 1 for covar in self.covarnames}
        two_terms = self.two.get_lincom_terms_simple(two_preds, two_covars)
        
        return one_terms - two_terms

    def get_csvv_coeff(self):
        return self.one.get_csvv_coeff()

    def get_csvv_vcv(self):
        return self.one.get_csvv_vcv()
        
    def format_call(self, lang, *args):
        equation_one = self.one.format_call(lang, *args)
        equation_two = self.two.format_call(lang, *args)
        
        result = {}
        result.update(equation_one)
        result.update(equation_two)
        result['main'] = formatting.FormatElement("%s - %s" % (equation_one['main'].repstr, equation_two['main'].repstr), self.one.dependencies + self.two.dependencies)
        return result

class SumCurveGenerator(CurveGenerator):
    """
    Sum a list of CSVVCurveGenerators, where each applies coefficients with a different suffix
    """
    def __init__(self, csvvcurvegens, coeffsuffixes):
        super(SumCurveGenerator, self).__init__(csvvcurvegens[0].indepunits, csvvcurvegens[0].depenunit)
        curvegens = []
        for tt in range(len(coeffsuffixes)):
            curvegen = csvvcurvegens[tt]
            curvegen.prednames = [predname + "-%s" % coeffsuffixes[tt] for predname in curvegen.prednames]
            curvegen.fill_marginals()
            curvegens.append(curvegen)
        
        self.curvegens = curvegens
        self.coeffsuffixes = coeffsuffixes

    def get_curve(self, region, year, covariates=None, **kwargs):
        if covariates is None:
            covariates = {}
        curves = [curvegen.get_curve(region, year, covariates, **kwargs) for curvegen in self.curvegens]
        return smart_curve.SumCurve(curves)

    def format_call(self, lang, *args):
        elementsets = [curvegen.format_call(lang, *args) for curvegen in self.curvegens]
        return formattools.join(" + ", elementsets)
    
    def get_partial_derivative_curvegen(self, covariate, covarunit):
        """
        Returns a CurveGenerator that calculates the partial
        derivative with respect to a covariate.
        """
        return SumCurveGenerator([curvegen.get_partial_derivative_curvegen(covariate, covarunit) for curvegen in self.curvegens], self.coeffsuffixes)

class SeasonTriangleCurveGenerator(CurveGenerator):
    """Select a curve generator by region, depending on the length of that region's season.

    Constructor should be called with either curvegen_triangle keyword
    (to give the season-to-curvegen mapping directly), or both
    get_curvegen and suffix_triangle keywords (to have each curvegen
    returned by get_curvegen for a given item of the suffix_triangle).

    The suffix_triangle is a list-of-lists. Item k (at index k-1) of
    this list describes the coefficients suffixes to be used for a
    season of length k. As a result, item k (a list) should itself
    contain k strings, the suffixes for month 1 to k of the
    season. The length of suffix_triangle should be equal to the
    longest possible season length.

    Parameters
    ----------
    culture_map : dict of str -> pair
        Season timestep endpoints for each region, as returned by irvalues.load_culture_months
    curvegen_triangle : list of CurveGenerators
        Item s (1-indexed) of list corresponds to CurveGenerator for season length s
    get_curvegen : function(list of str) -> CurveGenerator
        Function that is called for each item of suffix_triangle to create/pull a CurveGenerator
    suffix_triangle : list of list of str
        Coefficient suffixes used for each season length, starting from a season of 1 timestep

    """
    def __init__(self, culture_map, curvegen_triangle=None, get_curvegen=None, suffix_triangle=None):
        self.culture_map = culture_map
        assert curvegen_triangle is not None or (get_curvegen is not None and suffix_triangle is not None)

        if curvegen_triangle is not None:
            self.curvegen_triangle = curvegen_triangle
        else:
            self.curvegen_triangle = []
            for row_suffixes in suffix_triangle:
                self.curvegen_triangle.append(get_curvegen(row_suffixes))

        super(SeasonTriangleCurveGenerator, self).__init__(self.curvegen_triangle[0].indepunits,
                                                                    self.curvegen_triangle[0].depenunit)

    def get_curve(self, region, year, covariates, recorddiag=True, *args, **kwargs):
        culture = self.culture_map.get(region, None)
        timesteps = culture[1] - culture[0] + 1
        return self.curvegen_triangle[timesteps - 1].get_curve(region, year, covariates, recorddiag=recorddiag, *args, **kwargs)

    def format_call(self, lang, *args):
        raise NotImplementedError()
        
    def get_partial_derivative_curvegen(self, covariate, covarunit):
        deriv_curvegen_triangle = []
        for curvegen in self.curvegen_triangle:
            deriv_curvegen_triangle.append(curvegen.get_partial_derivative_curvegen(covariate, covarunit))

        return SeasonTriangleCurveGenerator(self.culture_map, curvegen_triangle=deriv_curvegen_triangle)

class SumByTimeMixin:
    def fill_marginals(self, csvv, prednames, coeffsuffixes):
        # Preprocessing marginals
        self.constant = {} # {predname: 0 or T [constants_t]}
        self.predcovars = {} # {predname: K [covarname]}
        self.predgammas = {} # {predname: T x K np.array}
        for predname in set(prednames):
            assert predname not in self.constant
            self.constant[predname] = []
            self.predgammas[predname] = []

            # Check if coeffsuffixes starts with zeros
            preceding_zeros = 0
            for coeffsuffix in coeffsuffixes:
                if coeffsuffix != 0:
                    break
                preceding_zeros += 1

            covarorder = None
            for coeffsuffix in coeffsuffixes[preceding_zeros:]:
                if coeffsuffix == 0:
                    # We'll always have covarorder by now
                    if '1' in covarorder:
                        self.constant[predname].append(0)
                        self.predgammas[predname].append([0] * (len(covarorder)-1))
                    else:
                        self.predgammas[predname].append([0] * len(covarorder))
                    continue

                predname_time = predname + "-%s" % coeffsuffix if coeffsuffix != '' else predname

                if covarorder is None:
                    # Decide on the canonical order of covars
                    indices = [ii for ii, xx in enumerate(csvv['prednames']) if xx == predname_time]
                    covarorder = [csvv['covarnames'][index] for index in indices]
                else:
                    # Re-order indices to match canonical order
                    unordered = [ii for ii, xx in enumerate(csvv['prednames']) if xx == predname_time]
                    indices = []
                    for predcovar in covarorder:
                        for uu in unordered:
                            if csvv['covarnames'][uu] == predcovar:
                                indices.append(uu)
                                break
                    assert len(indices) == len(covarorder)

                constant_time = []  # make sure have 0 or 1
                predgammas_time = []
                for index in indices:
                    if csvv['covarnames'][index] == '1':
                        constant_time.append(csvv['gamma'][index])
                    else:
                        predgammas_time.append(csvv['gamma'][index])

                # If this is the first non-zero suffix
                if preceding_zeros > 0:
                    for kk in range(preceding_zeros):
                        if '1' in covarorder:
                            self.constant[predname].append(0)
                            self.predgammas[predname].append([0] * (len(covarorder)-1))
                        else:
                            self.predgammas[predname].append([0] * len(covarorder))
                    preceding_zeros = 0 # Disable this case
                        
                self.constant[predname] += constant_time
                self.predgammas[predname].append(predgammas_time)

            if len(self.constant[predname]) == 0:
                self.constant[predname] = 0
            else:
                assert len(self.constant[predname]) == len(coeffsuffixes)
                self.constant[predname] = np.array(self.constant[predname])
            
            self.predcovars[predname] = covarorder
            if '1' in covarorder:
                self.predcovars[predname].remove('1')
            self.predgammas[predname] = np.array(self.predgammas[predname])

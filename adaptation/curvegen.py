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
    def __init__(self, prednames, indepunits, depenunit, csvv, betalimits={}, ignore_units=False):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunit)

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
        """

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
                    coefficients[predname] = self.constant.get(predname, 0) + np.sum(self.predgammas[predname] * np.array([covariates[covar] for covar in self.predcovars[predname]]))
                    if not np.isscalar(coefficients[predname]):
                        coefficients[predname] = coefficients[predname][0]
                    if predname in self.betalimits and not np.isnan(coefficients[predname]):
                        coefficients[predname] = min(max(self.betalimits[predname][0], coefficients[predname]), self.betalimits[predname][1])
                    
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

    def get_curve(self, region, year, covariates={}):
        raise NotImplementedError()

    def get_lincom_terms(self, region, year, predictors):
        raise NotImplementedError()

    def get_lincom_terms_simple(self, predictors, covariates={}):
        # Return in the order of the CSVV
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
    """
    def __init__(self, curvegen, covariator, farmer='full', save_curve=True):
        super(FarmerCurveGenerator, self).__init__(curvegen)
        self.covariator = covariator
        self.farmer = farmer
        self.save_curve = save_curve
        self.lincom_last_covariates = {}
        self.lincom_last_year = {}

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
        if year < 2015:
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
        
    def get_lincom_terms(self, region, year, predictors={}, origds=None):
        # Get last covariates
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

    def get_lincom_terms_simple(self, predictors, covariates={}):
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

    def get_curve(self, region, year, covariates={}, **kwargs):
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

"""Classes for curve generation from general fitting methods.

This file defines sub-classes of the CSVVCurveGenerator class. For
more information, see the curvegen.py file.

In contrast to curvegen_known.py, the CurveGenerators defined below
take coefficients that are applied in the same way to all
predictors. For example, a SumCoefficientsCurveGenerator takes
coefficients from a regression, and assumes that predictors of the
same form as the regression will be applied to it during the
projection process. In this case, the entire projection calculation
reduces to a dot-product.

"""

import numpy as np
from openest.generate import formatting, diagnostic, selfdocumented
from openest.generate.smart_curve import TransformCoefficientsCurve
from . import curvegen, csvvfile

class LinearCSVVCurveGenerator(curvegen.CSVVCurveGenerator):
    def get_curve_parameters(self, region, year, covariates=None):
        if covariates is None:
            covariates = {}
        allcoeffs = self.get_coefficients(covariates)
        return [allcoeffs[predname] for predname in self.prednames]

class CoefficientsCurveGenerator(LinearCSVVCurveGenerator):
    """Wrapper class for an arbitrary curve generation function.
    
    The CSVV coefficients are assumed to be named either prefix0,
    prefix1, ..., prefixN or prefix, prefix2, ..., prefixN.

    Parameters
    ----------
    curvefunc : function(sequence of float) -> Curve
        Produces a curve for a given set of adaptation-adjusted coefficients (betas).
    indepunits : sequence of str
        The unit for each predictor variable.
    depenunit : str
        The unit for the outcome variable.
    prefix : str
        Prefix for naming the coefficients in the CSVV.
    order : int
        The number of coefficient terms.
    csvv : dict
        Dictionary returned by csvvfile.read.
    zerostart : bool
        If True, the first predictor is prefix0; otherwise it is prefix.
    betalimits : dict
        Dictionary of limits on the resulting betas; passed to CSVVCurveGenerator.

    """
    def __init__(self, curvefunc, indepunits, depenunit, prefix, order, csvv, zerostart=True, betalimits=None):
        self.curvefunc = curvefunc
        if zerostart:
            prednames = [prefix + str(ii) for ii in range(order)]
        else:
            prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]

        super(CoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits)

    def get_curve(self, region, year, covariates=None):
        if covariates is None:
            covariates = {}
        mycoeffs = self.get_curve_parameters(region, year, covariates)
        return self.curvefunc(mycoeffs)

class SumCoefficientsCurveGenerator(LinearCSVVCurveGenerator):
    """Arbitrary OLS gamma regression curve generator.

    Each predictor can be a transformation of the information in the
    weather xarray Dataset, although it is usually directly taken from
    the dataset since transformation is performed prior to spatial
    aggregation.

    Parameters
    ----------
    prednames : sequence of str
        The predictors as described in the CSVV file.
    ds_transforms : sequence of function(Dataset) -> array_like
        Functions to extract the relevant data from the xarray Dataset.
    transform_descriptions : sequence of str
        Description of what each ds_transform does.
    indepunits : sequence of str
        The unit for each predictor variable.
    depenunit : str
        The unit for the outcome variable.
    csvv : dict
        Dictionary returned by csvvfile.read.
    diagprefix : str
        The prefix for coefficient values as reported in the diagnostics file.
    betalimits : dict
        Dictionary of limits on the resulting betas; passed to CSVVCurveGenerator.

    """
    def __init__(self, prednames, ds_transforms, transform_descriptions, indepunits, depenunit, csvv, diagprefix='coeff-',
                 betalimits=None):
        super(SumCoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits)
        self.ds_transforms = ds_transforms
        self.transform_descriptions = transform_descriptions
        self.diagprefix = diagprefix
    
    def get_curve(self, region, year, covariates=None, recorddiag=True, **kwargs):
        if covariates is None:
            covariates = {}
        mycoeffs = self.get_curve_parameters(region, year, covariates)

        if recorddiag and diagnostic.is_recording():
            for ii in range(len(self.prednames)):
                diagnostic.record(region, covariates.get('year', 2000), self.diagprefix + self.prednames[ii], mycoeffs[ii])

        return TransformCoefficientsCurve(mycoeffs, [self.ds_transforms[predname] for predname in self.prednames], self.transform_descriptions, self.prednames if recorddiag and diagnostic.is_recording() else None)

    def get_lincom_terms_simple_each(self, predname, covarname, predictors, covariates=None):
        if covariates is None:
            covariates = {}
        pred = np.sum(predictors[predname]._values)
        covar = covariates[self.csvv['covarnames'][ii]] if self.csvv['covarnames'][ii] != '1' else 1
        return pred * covar

    def format_call(self, lang, *args):
        coeffs = [self.diagprefix + predname for predname in self.prednames]
        coeffreps = [formatting.get_parametername(coeff, lang) for coeff in coeffs]
        predreps = [formatting.get_parametername(predname, lang) for predname in self.prednames]
        transreps = [selfdocumented.get_repstr(self.ds_transforms[predname], lang) for predname in self.prednames]
        transdeps = [dep for predname in self.prednames for dep in selfdocumented.get_dependencies(self.ds_transforms[predname], lang)]

        if lang == 'latex':
            elts = {'main': formatting.FormatElement(r"\sum_{k=1}^%d \beta_k x_k" % len(self.prednames), coeffs + self.prednames + transdeps, is_primitive=True)}
        elif lang == 'julia':
            elts = {'main': formatting.FormatElement("sum(%s)" % ' + '.join(["%s * (%s)" % (coeffreps[ii], transreps[ii]) for ii in range(len(coeffs))]), coeffs + transdeps, is_primitive=True)}

        for ii in range(len(self.prednames)):
            elts[self.prednames[ii]] = formatting.ParameterFormatElement(self.prednames[ii], predreps[ii])
            elts[coeffs[ii]] = formatting.ParameterFormatElement(coeffs[ii], coeffreps[ii])
            elts.update(selfdocumented.format_nomain(self.ds_transforms[self.prednames[ii]], lang))

        return elts

    def get_partial_derivative_curvegen(self, covariate, covarunit):
        csvvpart = csvvfile.partial_derivative(self.csvv, covariate, covarunit)
        incpreds = [predname in csvvpart['prednames'] for predname in self.prednames]
        prednames = [self.prednames[ii] for ii in range(len(self.prednames)) if incpreds[ii]]
        indepunits = [self.indepunits[ii] for ii in range(len(self.prednames)) if incpreds[ii]]
        if not self.betalimits:
            return SumCoefficientsCurveGenerator(prednames, self.ds_transforms, self.transform_descriptions,
                                                 indepunits, self.depenunit + '/' + covarunit,
                                                 csvvpart, diagprefix=self.diagprefix + 'dd' + covariate)

        return BetaLimitsDerivativeSumCoefficientsCurveGenerator(self, prednames, self.ds_transforms, self.transform_descriptions,
                                                                 indepunits, self.depenunit + '/' + covarunit,
                                                                 csvvpart, diagprefix=self.diagprefix + 'dd' + covariate)

class BetaLimitsDerivativeSumCoefficientsCurveGenerator(SumCoefficientsCurveGenerator):
    def __init__(self, prederiv_curvegen, prednames, ds_transforms, transform_descriptions, indepunits, depenunit, csvv, diagprefix='coeff-'):
        super(BetaLimitsDerivativeSumCoefficientsCurveGenerator, self).__init__(prednames, ds_transforms, transform_descriptions, indepunits, depenunit, csvv, diagprefix)
        self.prederiv_curvegen = prederiv_curvegen

    def get_curve_parameters(self, region, year, covariates, **kwargs):
        prederiv_coeffs = self.prederiv_curvegen.get_coefficients(covariates)
        coeffs = self.get_coefficients(covariates)

        for predname in coeffs:
            if predname in self.prederiv_curvegen.betalimits:
                if prederiv_coeffs[predname] == self.prederiv_curvegen.betalimits[predname][0] or prederiv_coeffs[predname] == self.prederiv_curvegen.betalimits[predname][1]:
                    coeffs[predname] = 0

        return [coeffs[predname] for predname in self.prednames]
    
class MLECoefficientsCurveGenerator(CoefficientsCurveGenerator):
    """Implementation of CoefficientsCurveGenerator for standard MLE curves.

    MLE curves, as we use the term in CIL, use the functional form:
        y = sum_k gamma_k0 x_l exp(sum_l gamma_kl z_l)

    This needs an alternative implementation of the get_coefficients
    curve to replace the linear sum with the expression above.

    """

    def get_coefficients(self, covariates, debug=False):
        coefficients = {} # {predname: beta * exp(gamma z)}
        for predname in set(self.prednames):
            if len(self.predgammas[predname]) == 0:
                coefficients[predname] = np.nan
            else:
                try:
                    coefficients[predname] = self.constant[predname] * np.exp(np.sum(self.predgammas[predname] * np.array([covariates[covar] for covar in self.predcovars[predname]])))
                except Exception as e:
                    print("Available covariates:")
                    print(covariates)
                    raise e

        return coefficients

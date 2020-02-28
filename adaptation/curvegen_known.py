"""Subclasses of the CurveGenerator class for known specification types.

These classes defined here are common specification structures in
econometrics. Each curve generator class is based on a
CSVVCurveGenerator, should know how to calculate itself either with
pre-computed weather or on-the-fly, know how to determine its
delta-method vector, and be able to take the partial derivative with
respect to a covariate to produce another known CurveGenerator.
"""

import numpy as np
from . import csvvfile, curvegen
from openest.generate import diagnostic, formatting, selfdocumented
from openest.generate.smart_curve import ZeroInterceptPolynomialCurve, CubicSplineCurve
from openest.models.curve import StepCurve

class SmartCSVVCurveGenerator(curvegen.CSVVCurveGenerator):
    """Provides additional structure for CSVVCurveGenerators that produce SmartCurves.

    Parameters
    ----------
    indepunits : seq of str
        The units for each independent variable.
    depenunit : str
        The unit of the dependent variable.
    prefix : str
        The prefix used in the CSVV for all terms.
    knots : seq of float
        The location of the knots in the cubic spline
    variablename: str
        Variable to apply the spline to.
    csvv : csvv dictionary
        Source for all parameter calculations.
    diagprefix : str (optional)
        The prefix used in the diagnostics files.
    betalimits : dict of str -> float
        Requires that all calculated betas are clipped to these limits.
    """
    def __init__(self, prednames, indepunits, depenunit, csvv, diagprefix='coeff-', betalimits={}, ignore_units=False):
        super(SmartCSVVCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits, ignore_units=ignore_units)
        self.diagprefix = diagprefix

    def get_curve(self, region, year, covariates={}, recorddiag=True, **kwargs):
        """
        Parameters
        ----------
        regions : str
            Target region.
        year : int
            Target year.
        covariates : dict
            Input covariates. Dictionary keys are variable name (str) with float values.
        recorddiag : bool
            Should a record be sent to ``diagnostic``?
        kwargs :
            Unused.

        Returns
        -------
        openest.generate.smart_curve.SmartCurve
        """
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        if recorddiag and diagnostic.is_recording():
            for predname in self.prednames:
                if year < 2015: # Only called once, so make the most of it
                    for yr in range(year, 2015):
                        diagnostic.record(region, yr, self.diagprefix + predname, coefficients[predname])
                else:
                    diagnostic.record(region, year, self.diagprefix + predname, coefficients[predname])

        return self.get_smartcurve(yy)

    def get_smartcurve(self, yy):
        """
        Parameters
        ----------
        yy : sequence of float
            The coefficients for the polynomial curve.

        Returns
        -------
        openest.generate.smart_curve.SmartCurve
        """
        raise NotImplementedError()

    def format_call(self, lang, *args):
        coeffs = [self.diagprefix + predname for predname in self.prednames]
        coeffreps = [formatting.get_parametername(coeff, lang) for coeff in coeffs]

        weatherreps = []
        weatherdeps = []
        for weather in self.weathernames:
            if isinstance(weather, str):
                weatherreps.append(formatting.get_parametername(weather, lang))
                weatherdeps.append(weather)
            else:
                weatherreps.append(selfdocumented.get_repstr(weather, lang))
                weatherdeps.extend(selfdocumented.get_dependencies(weather, lang))
            
        if lang == 'latex':
            elements = {'main': formatting.FormatElement(' + '.join(["%s_k %s" % (beta, weatherreps[kk]) for kk in range(len(self.weathernames))]), coeffs + weatherdeps, is_primitive=True)}
        elif lang == 'julia':
            elements = {'main': formatting.FormatElement(' + '.join(["%s * %s" % (coeffreps[kk], weatherreps[kk]) for kk in range(len(self.weathernames))]), coeffs + weatherdeps, is_primitive=True)}

        for ii in range(len(coeffs)):
            elements[coeffs[ii]] = formatting.ParameterFormatElement(coeffs[ii], coeffreps[ii])
        for ii in range(len(self.weathernames)):
            if isinstance(self.weathernames[ii], str):
                elements[self.weathernames[ii]] = formatting.ParameterFormatElement(self.weathernames[ii], weatherreps[ii])
            
        return elements
    
class PolynomialCurveGenerator(SmartCSVVCurveGenerator):
    """A CurveGenerator for a series of polynomial terms. For a weather
    variable `T`, this consist of `T`, `T^2`, ..., `T^k`. Since this
    is a CSVVCurveGenerator, the PolynomialCurveGenerator defines how
    these will be named in the CSVV:
    `<prefix>`, `<prefix><predinfix>2`, ..., `<prefix><predinfix>k`.

    Parameters
    ----------
    indepunits : list of 1 str
        The full set of units will be duplicates of this unit.
    depenunit : str
        The unit of the dependent variable.
    prefix : str
        The prefix used in the CSVV for all terms.
    order : int
        The number of terms in the polynomial. A quadratic has 2 terms.
    csvv : csvv dictionary
        Source for all parameter calculations.
    diagprefix : str (optional)
        The prefix used in the diagnostics files.
    predindex : str (optional)
        Used to name CSVV prednames. Often this takes the value "-poly-", so the terms are `prefix`, `prefix-poly-2`, etc.
    weathernames : seq of str (optional)
        The names as identified in the weather Dataset.
    betalimits : dict of str -> float
        Requires that all calculated betas are clipped to these limits.
    allow_raising : bool
        If the required weather cannot be found, can we calculate the terms on-the-fly, or should we produce an error?
    ignore_units : bool
        If the units do not match, should we produce an error?
    """
    def __init__(self, indepunits, depenunit, prefix, order, csvv, diagprefix='coeff-', predinfix='', weathernames=None, betalimits={}, allow_raising=False, ignore_units=False):
        self.order = order
        prednames = [prefix + predinfix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        super(PolynomialCurveGenerator, self).__init__(prednames, indepunits * order, depenunit, csvv, betalimits=betalimits, ignore_units=ignore_units)
        self.diagprefix = diagprefix
        self.weathernames = weathernames
        self.allow_raising = allow_raising
        self.prefix = prefix
        self.predinfix = predinfix

    def get_smartcurve(self, yy):
        """
        Parameters
        ----------
        yy : sequence of float
            The coefficients for the polynomial curve.

        Returns
        -------
        openest.generate.smart_curve.ZeroInterceptPolynomialCurve
        """
        return ZeroInterceptPolynomialCurve(yy, self.weathernames, self.allow_raising)

    def get_lincom_terms_simple_each(self, predname, covarname, predictors, covariates={}):
        if predname not in list(predictors._variables.keys()):
            predname = predname[:-1] + '-poly-' + predname[-1]
            
        pred = np.sum(predictors[predname]._values)
        covar = covariates[covarname] if covarname != '1' else 1
        return pred * covar

    def get_csvv_coeff(self):
        return self.csvv['gamma']

    def get_csvv_vcv(self):
        return self.csvv['gammavcv']

    def format_call(self, lang, *args):
        if self.weathernames:
            return super(PolynomialCurveGenerator, self).format_call(lang, *args)

        coeffs = [self.diagprefix + predname for predname in self.prednames]
        coeffreps = [formatting.get_parametername(coeff, lang) for coeff in coeffs]

        if lang == 'latex':
            beta = formatting.get_beta(lang)
            elements = {'main': formatting.FormatElement(r"\sum_{k=1}^%d %s_k %s^k" % (self.order, beta, args[0]), [beta], is_primitive=True),
                        beta: formatting.FormatElement('[' + ', '.join(coeffreps) + ']', coeffs)}
        elif lang == 'julia':
            elements = {'main': formatting.FormatElement(' + '.join(["%s * %s^%d" % (coeffreps[kk], args[0], order+1) for kk in range(self.order)]), coeffs, is_primitive=True)}

        for ii in range(len(coeffs)):
            elements[coeffs[ii]] = formatting.ParameterFormatElement(coeffs[ii], coeffreps[ii])

        return elements

    def get_partial_derivative_curvegen(self, covariate, covarunit):
        csvvpart = csvvfile.partial_derivative(self.csvv, covariate, covarunit)
        return PolynomialCurveGenerator(self.indepunits, self.depenunit + '/' + covarunit, self.prefix,
                                        self.order, csvvpart, diagprefix=self.diagprefix + 'dd' + covariate, predinfix=self.predinfix,
                                        weathernames=self.weathernames, betalimits=self.betalimits,
                                        allow_raising=self.allow_raising)

class CubicSplineCurveGenerator(SmartCSVVCurveGenerator):
    """A CurveGenerator for a series of terms representing a restricted cubic spline.

    Currently, the code does not support the use of pre-computed terms.

    Parameters
    ----------
    indepunits : seq of str
        This is generally formed of a unit, followed by unit^3 for the remaining terms.
    depenunit : str
        The unit of the dependent variable.
    prefix : str
        The prefix used in the CSVV for all terms.
    knots : seq of float
        The location of the knots in the cubic spline
    variablename: str
        Variable to apply the spline to.
    csvv : csvv dictionary
        Source for all parameter calculations.
    diagprefix : str (optional)
        The prefix used in the diagnostics files.
    betalimits : dict of str -> float
        Requires that all calculated betas are clipped to these limits.
    """
    def __init__(self, indepunits, depenunit, prefix, knots, variablename, csvv, diagprefix='coeff-', betalimits={}, allow_raising=False):
        self.knots = knots
        self.variablename = str(variablename)
        prednames = [self.variablename] + [prefix + str(ii) for ii in range(1, len(knots)-1)]
        super(CubicSplineCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits)
        self.allow_raising = allow_raising
        self.weathernames = prednames

    def get_smartcurve(self, yy):
        return CubicSplineCurve(yy, self.knots, self.prednames, self.allow_raising)

    def format_call(self, lang, *args):
        assert self.weathernames, "Analytical representation of cubic spline not implemented."
        return super(CubicSplineCurveGenerator, self).format_call(lang, *args)
   
class BinnedStepCurveGenerator(curvegen.CSVVCurveGenerator):
    """A CurveGenerator for a series of cumulative bins.

    Currently, the code does not support the use of pre-computed terms.

    Parameters
    ----------
    xxlimits : seq of float
        The extremes and intermediate points for the bins; typically starts with -np.inf, ends with np.inf
    indepunits : list of 1 str
        The full set of units will be duplicates of this unit.
    depenunit : str
        The unit of the dependent variable.
    csvv : csvv dictionary
        Source for all parameter calculations.
    """
    def __init__(self, xxlimits, indepunits, depenunit, csvv):
        self.xxlimits = xxlimits
        prednames = csvvfile.binnames(xxlimits, 'bintas')
        super(BinnedStepCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)
        self.min_betas = {}

    def get_curve(self, region, year, covariates={}):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        min_beta = self.min_betas.get(region, None)

        if min_beta is None:
            self.min_betas[region] = np.minimum(0, np.nanmin(np.array(yy)[4:-2]))
        else:
            yy = np.maximum(min_beta, yy)

        return StepCurve(self.xxlimits, yy)

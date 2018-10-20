import numpy as np
import csvvfile, curvegen
from openest.generate import diagnostic, formatting, selfdocumented
from openest.models.curve import ZeroInterceptPolynomialCurve, CubicSplineCurve

class PolynomialCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, indepunits, depenunit, prefix, order, csvv, diagprefix='coeff-', predinfix='', weathernames=None, betalimits={}):
        self.order = order
        prednames = [prefix + predinfix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        super(PolynomialCurveGenerator, self).__init__(prednames, indepunits * order, depenunit, csvv, betalimits=betalimits)
        self.diagprefix = diagprefix
        self.weathernames = weathernames

    def get_curve(self, region, year, covariates={}, recorddiag=True, **kwargs):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        if recorddiag and diagnostic.is_recording():
            for predname in self.prednames:
                if year < 2015: # Only called once, so make the most of it
                    for yr in range(year, 2015):
                        diagnostic.record(region, yr, self.diagprefix + predname, coefficients[predname])
                else:
                    diagnostic.record(region, year, self.diagprefix + predname, coefficients[predname])

        return ZeroInterceptPolynomialCurve([-np.inf, np.inf], yy)

    def get_lincom_terms_simple_each(self, predname, covarname, predictors, covariates={}):
        if predname not in predictors._variables.keys():
            predname = predname[:-1] + '-poly-' + predname[-1]
                
        pred = np.sum(predictors[predname]._values)
        covar = covariates[covarname] if covarname != '1' else 1
        return pred * covar

    def get_csvv_coeff(self):
        return self.csvv['gamma']

    def get_csvv_vcv(self):
        return self.csvv['gammavcv']

    def format_call(self, lang, *args):
        coeffs = [self.diagprefix + predname for predname in self.prednames]
        coeffreps = [formatting.get_parametername(coeff, lang) for coeff in coeffs]
        if self.weathernames:
            weatherreps = []
            weatherdeps = []
            for weather in self.weathernames:
                if isinstance(weather, str):
                    weatherreps.append(formatting.get_parametername(weather, lang))
                    weatherdeps.append(weather)
                else:
                    weatherreps.append(selfdocumented.get_repstr(weather, lang))
                    weatherdeps.extend(selfdocumented.get_dependencies(weather, lang))
        else:
            weatherreps = None
            weatherdeps = []

        if lang == 'latex':
            if weatherreps is None:
                beta = formatting.get_beta(lang)
                elements = {'main': formatting.FormatElement(r"\sum_{k=1}^%d %s_k %s^k" % (self.order, beta, args[0]), [beta], is_primitive=True),
                            beta: formatting.FormatElement('[' + ', '.join(coeffreps) + ']', coeffs)}
            else:
                elements = {'main': formatting.FormatElement(' + '.join(["%s_k %s" % (beta, weatherreps[kk]) for kk in range(self.order)]), coeffs + weatherdeps, is_primitive=True)}
        elif lang == 'julia':
            if weatherreps is None:
                elements = {'main': formatting.FormatElement(' + '.join(["%s * %s^%d" % (coeffreps[kk], args[0], order+1) for kk in range(self.order)]), coeffs, is_primitive=True)}
            else:
                elements = {'main': formatting.FormatElement(' + '.join(["%s * %s" % (coeffreps[kk], weatherreps[kk]) for kk in range(self.order)]), coeffs + weatherdeps, is_primitive=True)}

        for ii in range(len(coeffs)):
            elements[coeffs[ii]] = formatting.ParameterFormatElement(coeffs[ii], coeffreps[ii])
        if weatherreps is not None:
            for ii in range(len(self.weathernames)):
                if isinstance(self.weathernames[ii], str):
                    elements[self.weathernames[ii]] = formatting.ParameterFormatElement(self.weathernames[ii], weatherreps[ii])
                else:
                    elements.update(selfdocumented.format_nomain(self.weathernames[ii], lang))

        return elements

class CubicSplineCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, indepunits, depenunit, prefix, knots, csvv, betalimits={}):
        self.knots = knots
        prednames = [prefix + str(ii) for ii in range(len(knots)-1)]
        super(CubicSplineCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits)

    def get_curve(self, region, year, covariates={}, recorddiag=True, **kwargs):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        if recorddiag and diagnostic.is_recording():
            for predname in self.prednames:
                if year < 2015: # Only called once, so make the most of it
                    for yr in range(year, 2015):
                        diagnostic.record(region, yr, predname, coefficients[predname])
                else:
                    diagnostic.record(region, year, predname, coefficients[predname])

        return CubicSplineCurve(self.knots, yy)

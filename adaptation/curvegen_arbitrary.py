import curvegen

class CoefficientsCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, curvefunc, indepunits, depenunit, prefix, order, csvv, zerostart=True):
        self.curvefunc = curvefunc
        if zerostart:
            prednames = [prefix + str(ii) for ii in range(order)]
        else:
            prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        
        super(CoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)

    def get_curve_parameters(self, region, covariates={}):
        allcoeffs = self.get_coefficients(covariates)
        return [allcoeffs[predname] for predname in self.prednames]
        
    def get_curve(self, region, covariates={}):
        mycoeffs = self.get_curve_parameters(region, covariates)
        return self.curvefunc(mycoeffs)


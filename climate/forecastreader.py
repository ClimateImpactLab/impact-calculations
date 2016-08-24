from netCDF4 import Dataset
from reader import WeatherReader
from scipy.stats import norm
import netcdfs, forecasts

class MonthlyForecastReader(WeatherReader):
    def __init__(self, filepath, variable, lead=0, qval=.5):
        version, units = netcdfs.readmeta(filepath, 'mean')
        super(MonthlyForecastReader, self).__init__(version, units)

        self.filepath = filepath
        self.variable = variable
        self.lead = lead
        self.qval = qval

    def get_times(self):
        """Return list of months"""
        rootgrp = Dataset(self.filepath, 'r', format='NETCDF4')
        months = rootgrp.variables['S'][:]
        rootgrp.close()

        return months

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        months = self.get_times()
        meansgen = forecasts.readncdf_allpred(self.filepath, "mean", self.lead)
        sdevsgen = forecasts.readncdf_allpred(self.filepath, "stddev", self.lead)
        for month in months:
            yield month, norm.ppf(self.qval, meansgen.next(), sdevsgen.next())

class MonthlyZScoreForecastReader(MonthlyForecastReader):
    """Translates into z-scores on-the-fly."""
    def __init__(self, filepath, climatepath, variable, lead=0, qval=.5):
        super(MonthlyZScoreForecastReader, self).__init__(filepath, variable, lead, qval)
        version_climate, units_climate = netcdfs.readmeta(climatepath, 'mean')
        assert self.units == units_climate

        self.climatepath = climatepath

    def get_dimension(self):
        return ['Z(' + self.variable + ')']

    def read_iterator(self):
        means = list(forecasts.readncdf_allpred(self.climatepath, "mean", self.lead))
        sdevs = list(forecasts.readncdf_allpred(self.climatepath, "stddev", self.lead))

        for month, weather in super(MonthlyZScoreForecastReader, self).read_iterator():
            yield month, (weather - means[month % 12]) / sdevs[month % 12]

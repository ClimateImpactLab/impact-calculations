from netCDF4 import Dataset
from reader import WeatherReader
from scipy.stats import norm
import netcdfs

class MonthlyForecastReader(WeatherReader):
    def __init__(self, filepath, variable, lead=0, qval=.5):
        version, units = netcdfs.readmeta(filepath, variable)
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
        meansgen = readncdf_allpred(self.filepath, "mean", self.lead)
        sdevsgen = readncdf_allpred(self.filepath, "stddev", self.lead)
        for month in months:
            yield month, norm.ppf(qval, meansgen.next(), sdevsgen.next())

class MonthlyZScoreForecastReader(MonthlyForecastReader):
    """Translates into z-scores on-the-fly."""
    def __init__(self, filepath, climatepath, variable, lead=0, qval=.5):
        super(MonthlyZScoreForecastReader, self).__init__(filepath, variable, lead, qval)
        version_climate, units_climate = netcdfs.readmeta(climatepath, variable)
        assert units == units_climate

        self.climatepath = climatepath

    def get_dimension(self):
        return ['Z(' + self.variable + ')']

    def read_iterator(self):
        meansgen = readncdf_allpred(self.filepath, "mean", self.lead)
        sdevsgen = readncdf_allpred(self.filepath, "stddev", self.lead)

        for month, weather in super(MonthlyZScoreForecastReader, self).read_iterator():
            yield month, (weather - meansgen.next()) / sdevsgen.next()

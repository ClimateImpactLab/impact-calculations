import numpy as np
import xarray as xr
import metacsv
import income, spacetime
from impactlab_tools.utils import files

gdppc_growth_filepath = 'social/baselines/gdppc-growth.csv'
baseline_end_year = 2010

class DynamicIncomeSmoothed(object):
    def __init__(self, model, scenario, dependencies):
        self.model = model
        self.scenario = scenario
        
        # Load the baseline income data
        self.current_year = baseline_end_year
        self.current_income = self.get_baseline_income(model, scenario, dependencies)

        # Load the growth matrix
        self.growth_country_by_year = self.get_growth_country_by_year(model, scenario, dependencies)
        
    def get_income(self, region, year):
        if year > self.current_year:
            # Update by one year
            country_growth = self.get_all_country_growth(year - 1) # growth in previous year
            for reg in self.current_income:
                self.current_income[reg] = self.current_income[reg] * country_growth.get(reg[:3], country_growth['mean'])
            self.current_year = self.current_year + 1

            # Recurse, in case there are more years to do
            return self.get_income(region, year)

        assert year == self.current_year or (self.current_year == baseline_end_year and year < self.current_year), "Year mismatch: %d <> %d" % (year, self.current_year)

        return self.current_income.get(region, None)

    def reset(self, dependencies):
        if self.current_year == baseline_end_year:
            return # Already reset
        
        self.current_year = baseline_end_year
        self.current_income = self.get_baseline_income(self.model, self.scenario, dependencies)
    
    def get_baseline_income(self, model, scenario, dependencies):
        baseline_income = {}
        for region, year, value in income.each_gdppc_nightlight(model, scenario, dependencies, income.gdppc_baseline_filepath):
            baseline_income[region] = value

        return baseline_income

    def get_growth_country_by_year(self, model, scenario, dependencies):
        """
        Return an xarray of [countries] rows and [years / 5] colums
        """
        df = metacsv.read_csv(files.sharedpath(gdppc_growth_filepath))
        subdf = df.loc[(df['model'] == model) & (df['scenario'] == scenario)]
        countries = subdf['iso'].unique()
        country_indexes = {countries[ii]: ii for ii in range(len(countries))}

        data = np.zeros((len(countries), len(subdf['year'].unique())))
        for index, row in subdf.iterrows():
            if row['year'] < baseline_end_year:
                continue

            data[country_indexes[row['iso']], (row['year'] - baseline_end_year) / 5] = row['growth']

        return xr.DataArray(data, coords={'country': countries}, dims=('country', 'year'))
    
    def get_all_country_growth(self, year):
        """
        Return a dictionary {ISO3 => growth} for the given year.  Always includes a mean level (in file after baseline_end_year).
        If year < baseline_end_year (baseline period), only report mean growth of 0.
        """
        if year < baseline_end_year:
            return dict(mean=0) # allow no growth
        
        yearindex = (year - baseline_end_year) / 5
        growths = self.growth_country_by_year[:, yearindex]

        country_growth = {}
        for country in self.growth_country_by_year.coords['country'].values:
            country_growth[country] = growths.sel(country=country).values

        return country_growth

class SpaceTimeBipartiteData(spacetime.SpaceTimeUnipartiteData):
    def __init__(self, year0, year1, regions):
        loader = lambda year0, year1, regions, model, scenario: SpaceTimeLoadedData(year0, year1, regions, model, scenario, [])
        super(SpaceTimeBipartiteData, self).__init__(year0, year1, regions, loader)

class SpaceTimeLoadedData(spacetime.SpaceTimeLoadedData):
    def __init__(self, year0, year1, regions, model, scenario, dependencies):
        # Load all data
        source = DynamicIncomeSmoothed(model, scenario, dependencies)
        if regions is None:
            regions = source.current_income.keys()
            
        array = np.zeros((year1 - year0 + 1, len(regions)))
        for year in range(year0, year1 + 1):
            for ii in range(len(regions)):
                array[year - year0, ii] = source.get_income(regions[ii], year)
        
        super(SpaceTimeLoadedData, self).__init__(year0, year1, regions, array, ifmissing='logmean')
    
if __name__ == '__main__':
    dependencies = []
    income = DynamicIncomeSmoothed('high', 'SSP3', dependencies)

    print "year,ZWE.2.2,ABW,XYZ.1.2"
    for year in range(2010, 2099):
        print ','.join(map(str, [year, income.get_income('ZWE.2.2', year), income.get_income('ABW', year),
                                 income.get_income('XYZ.1.2', year)]))
        

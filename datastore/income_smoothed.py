import xarray as xr
import metacsv
import income

gdppc_growth_filepath = 'social/baselines/gdppc-growth.csv'
baseline_end_year = 2010

class DynamicIncomeSmoothed(object):
    def __init__(self, model, scenario, dependencies):
        # Load the baseline income data
        self.current_year = baseline_end_year
        self.current_income = self.get_baseline_income(model, scenario, dependencies)

        # Load the growth matrix
        self.growth_country_by_year = get_growth_country_by_year(model, scenario, dependencies)
        
    def get_income(self, region, year):
        if year > self.current_year:
            # Update by one year
            country_growth = self.get_all_country_growth(self, year - 1) # growth in previous year
            for region in regions:
                self.current_income[region] = self.current_income[region] * country_growth.get(region[:3], country_growth['mean'])

            # Recurse, in case there are more years to do
            return self.get_income(region, year)

        assert year == self.current

        return self.current_income[region]

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
        subdf = df.loc[(df['model'] == model) && (df['scenario'] == scenario)]
        countries = subdf['iso'].unique()

        data = xr.DataArray(np.zeros((len(countries), len(subdf['year'].unique()))), coords={'country': countries}, dims=('country', 'year'))
        for index, row in subdf.iterrows():
            if row['year'] < baseline_end_year:
                continue

            data.isel[row['iso'], (row['year'] - baseline_end_year) / 5] = row['growth']

        return data
    
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
        for country in self.growth_country_by_year.coords['countries']
            country_growth[country] = growths[country]

        return country_growth

if __name__ == '__main__':
    dependencies = []
    income = DynamicIncomeSmoothed('low', 'SSP4', dependencies)

    for year in range(2000, 2020):
        print income.get_income('ARG.22.469', year)

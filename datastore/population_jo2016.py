import numpy as np
import pandas as pd
import scipy.interpolate
import spacetime

class SpaceTimeBipartiteData(spacetime.SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions):
        self.dependencies = ['Jones_ONeill_pop']

        df = pd.read_csv(files.sharedpath('social/weightlines/Jones_ONeill_pop.csv'))
        self.df = df.set_index('hierid')

        if regions is None:
            regions = df.index.unique()

        super(SpaceTimeBipartiteData, self).__init__(year0, year1, regions)

    def load(self, year0, year1, model, scenario):
        popout = np.ones((year1 - year0 + 1, len(regions))) * np.nan

        for ii, region in enumerate(self.regions):
            subdf = self.df.loc[region]
            filler = scipy.interpolate.interp1d(subdf.year, subdf.sum_value, kind='zero', fill_value="extrapolate")
            popout[:, ii] = filler(np.arange(year0, year1 + 1))

        return spacetime.SpaceTimeLoadedData(year0, year1, self.regions, popout)

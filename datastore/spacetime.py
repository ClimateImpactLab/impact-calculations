class SpaceTimeData(object):
    def __init__(self, year0, year1, regions):
        self.year0 = year0
        self.year1 = year1
        self.regions = regions

class SpaceTimeLoadedData(SpaceTimeData):
    def __init__(self, year0, year1, regions, array):
        super(SpaceTimeLoadedData, self).__init__(year0, year1, regions)
        self.array = array # as YEAR x REGION
        self.indices = {regions[ii]: ii for ii in range(len(regions))}
        
    def get_time(self, region):
        #ii = self.regions.index(region)
        ii = self.indices[region]
        return self.array[:, ii]

from autodoc.lib import *

def get_weather(weathertemplate, years, shapenum, show_all_years=[], variable='tas', regindex='hierid', subset=None):
    weather = {}
    for year in years:
        filepath = weathertemplate.format('historical' if year < 2006 else 'rcp85', year)
        assert os.path.exists(filepath), "Cannot find %s" % filepath
        ds = xr.open_dataset(filepath)
        if isinstance(shapenum, str):
            regions = list(ds[regindex].values)
            shapenum = regions.index(shapenum)
            
        data = ds[variable].isel(**{regindex: shapenum})
        if subset is None:
            data = data.values
        else:
            data = data[subset].values

        if year in show_all_years:
            print str(year) + ': ' + ','.join(map(str, data))
        else:
            print str(year) + ': ' + ','.join(map(str, data[:10])) + '...'
        weather[year] = data

    return weather

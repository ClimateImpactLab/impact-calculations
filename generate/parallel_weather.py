"""
WeatherBundle object used by slaves during parallel processing runs.
"""

import numpy as np
from . import multithread, weather

def is_parallel(weatherbundle):
    return isinstance(weatherbundle, SlaveParallelWeatherBundle)

class SlaveParallelWeatherBundle(weather.WeatherBundle):
    """Thread-safe WeatherBundle, which allows any thread to request year bundles first."""
    def __init__(self, master, local):
        self.master = master
        self.local = local
        
    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        while True:
            outputs = self.master.request_action(self.local, 'yearbundles', maxyear=maxyear, variable_ofinterest=variable_ofinterest)
            if 'ds' not in outputs:
                self.master.end_timestep(self.local) # Acknowledge end
                break
            yield outputs['year'], outputs['ds']
            self.master.end_timestep(self.local)

    def __getattr__(self, name):
        return getattr(self.master.weatherbundle, name)
    

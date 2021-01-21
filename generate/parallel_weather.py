"""
WeatherBundle object used by workers during parallel processing runs.
"""

import numpy as np
from . import multithread, weather

def is_parallel(weatherbundle):
    return isinstance(weatherbundle, WorkerParallelWeatherBundle)

class WorkerParallelWeatherBundle(weather.WeatherBundle):
    """Thread-safe WeatherBundle, which allows any thread to request year bundles first."""
    def __init__(self, driver, local):
        self.driver = driver
        self.local = local
        
    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        while True:
            outputs = self.driver.request_action(self.local, 'yearbundles', maxyear=maxyear, variable_ofinterest=variable_ofinterest)
            if 'ds' not in outputs:
                self.driver.end_timestep(self.local) # Acknowledge end
                break
            yield outputs['year'], outputs['ds']
            self.driver.end_timestep(self.local)

    def __getattr__(self, name):
        return getattr(self.driver.weatherbundle, name)
    

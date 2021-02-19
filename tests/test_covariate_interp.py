import numpy as np
import pandas as pd
from openest.generate.fast_dataset import FastDataset
from impactlab_tools.utils import files
import adaptation
from generate import weather
from climate import discover
from interpret import specification

def test_climtasclip(monkeypatch):
    monkeypatch.setattr(files, 'server_config', {'shareddir': 'tests/testdata'})
    bundleiterator = weather.iterate_bundles(discover.standard_variable('tas', 'year'))
    scenario, model, weatherbundle = next(bundleiterator)

    covardef = [{'climtasclip': [0.64, 29.01]}, {'(climtas^2)clip': [0.4096, 841.5801]}]

    covariator = specification.create_covariator({'covariates': covardef}, weatherbundle, None)
    assert isinstance(covariator.covariators[0], adaptation.covariates.ClipCovariator)
    assert isinstance(covariator.covariators[1], adaptation.covariates.ClipCovariator)

    for tt in range(2016, 2021):
        covariator.get_update('CAN.1.2.28', 2016, FastDataset({'dailytas': (['time'], -10*np.ones(365))},
                                                              coords={'time': np.arange(365)}))
    assert covariator.get_current('CAN.1.2.28')['climtas'] == 0.64
    assert covariator.get_current('CAN.1.2.28')['climtas^2'] == 0.4096

    for tt in range(2021, 2036):
        covariator.get_update('CAN.1.2.28', 2016, FastDataset({'dailytas': (['time'], 50*np.ones(365))},
                                                              coords={'time': np.arange(365)}))
    assert covariator.get_current('CAN.1.2.28')['climtas'] == 29.01
    assert covariator.get_current('CAN.1.2.28')['climtas^2'] == 841.5801

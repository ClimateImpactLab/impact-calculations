import mortality_helper
from helpers import files

def prepare_interp_raw(weatherbundle, economicmodel, pvals, get_data):
    predictorsdir = files.sharedpath('social/adaptation/predictors-space-65+')
    return mortality_helper.prepare_interp_raw(predictorsdir, weatherbundle, economicmodel, pvals, get_data, farmer='dumb')

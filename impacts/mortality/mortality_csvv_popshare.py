import mortality_helper
from helpers import files

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer):
    return mortality_helper.prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer=farmer, ageshare=True)

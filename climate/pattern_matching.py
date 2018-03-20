rcp_models = {
    'rcp45': {x[0]: x[1] for x in [
        ('pattern1', 'MRI-CGCM3'),
        ('pattern2', 'GFDL-ESM2G'),
        ('pattern3', 'MRI-CGCM3'),
        ('pattern4', 'GFDL-ESM2G'),
        ('pattern5', 'MRI-CGCM3'),
        ('pattern6', 'GFDL-ESM2G'),
        ('pattern27', 'GFDL-CM3'),
        ('pattern28', 'CanESM2'),
        ('pattern29', 'GFDL-CM3'),
        ('pattern30', 'CanESM2'),
        ('pattern31', 'GFDL-CM3'),
        ('pattern32', 'CanESM2')]},

    'rcp85': {x[0]: x[1] for x in [
        ('pattern1', 'MRI-CGCM3'),
        ('pattern2', 'GFDL-ESM2G'),
        ('pattern3', 'MRI-CGCM3'),
        ('pattern4', 'GFDL-ESM2G'),
        ('pattern5', 'MRI-CGCM3'),
        ('pattern6', 'GFDL-ESM2G'),
        ('pattern28', 'GFDL-CM3'),
        ('pattern29', 'CanESM2'),
        ('pattern30', 'GFDL-CM3'),
        ('pattern31', 'CanESM2'),
        ('pattern32', 'GFDL-CM3'),
        ('pattern33', 'CanESM2')]}}

rcp_models_new = {
    'rcp45': {
        'surrogate_CanESM2_89': 'CanESM2',
        'surrogate_CanESM2_94': 'CanESM2',
        'surrogate_CanESM2_99': 'CanESM2',
        'surrogate_GFDL-CM3_89': 'GFDL-CM3',
        'surrogate_GFDL-CM3_94': 'GFDL-CM3',
        'surrogate_GFDL-CM3_99': 'GFDL-CM3',
        'surrogate_GFDL-ESM2G_01': 'GFDL-ESM2G',
        'surrogate_GFDL-ESM2G_06': 'GFDL-ESM2G',
        'surrogate_GFDL-ESM2G_11': 'GFDL-ESM2G',
        'surrogate_MRI-CGCM3_01': 'MRI-CGCM3',
        'surrogate_MRI-CGCM3_06': 'MRI-CGCM3',
        'surrogate_MRI-CGCM3_11': 'MRI-CGCM3'},
    
    'rcp85': {
        'surrogate_CanESM2_89': 'CanESM2',
        'surrogate_CanESM2_94': 'CanESM2',
        'surrogate_CanESM2_99': 'CanESM2',
        'surrogate_GFDL-CM3_89': 'GFDL-CM3',
        'surrogate_GFDL-CM3_94': 'GFDL-CM3',
        'surrogate_GFDL-CM3_99': 'GFDL-CM3',
        'surrogate_GFDL-ESM2G_01': 'GFDL-ESM2G',
        'surrogate_GFDL-ESM2G_06': 'GFDL-ESM2G',
        'surrogate_GFDL-ESM2G_11': 'GFDL-ESM2G',
        'surrogate_MRI-CGCM3_01': 'MRI-CGCM3',
        'surrogate_MRI-CGCM3_06': 'MRI-CGCM3',
        'surrogate_MRI-CGCM3_11': 'MRI-CGCM3'}}


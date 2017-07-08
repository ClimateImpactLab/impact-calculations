#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 10 22:45:55 2017

@author: theodorkulczycki
"""

import os
import numpy as np
import pandas as pd
from glob import glob
from numpy import nan
from joblib import Parallel, delayed
import time

def calculate_damages(rcp, ssp):
    
    ### Preliminaries
    print('---Preliminaries')
    tic = time.time()
    
    moddict = {'high' : 'OECD Env-Growth', 'low' : 'IIASA GDP'}
    
    path_data = '/shares/gcp/social/processed/vsl'
    path_regions = '/shares/gcp/regions'
    path_climate = '/shares/gcp/climate/global_tas'
    
    file_vsletc = os.path.join(path_data, 'impactregion_pop_share_gdp_vsl.csv')
    file_regions = os.path.join(path_regions, 'region-attributes.csv')
    
    ages = ['young', 'older', 'oldest']
    
    
    ### Load regions
    reg = pd.read_csv(file_regions)['hierid']
    reg.name = 'region'
    
    
    ### Load gdp, vsl, age and share data
    vsletc = pd.read_csv(file_vsletc, index_col=0)
    vsletc = vsletc.loc[(vsletc.ssp==ssp), :]
    vsletc.set_index(['region', 'year'], inplace=True)
    

    ### Load results
    print('---Loading results')
    results = {}
    with Parallel(n_jobs=12) as parallelize:
        for age in ages:
            for suff in [age, age+'_incadapt', age+'_noadapt', age+'_histclim', age+'_costs_lb', age+'_costs_ub']:
                print('---{}'.format(suff))
                file_results = file_results_blank.format(rcp, ssp, suff)
                rf = pd.DataFrame()
                reader = pd.read_csv(file_results, chunksize=256)
                for chunk in reader:
                    rf = rf.append(chunk)
                for mod, ss1 in rf.groupby(['iam']):
                    if mod not in results.keys():
                        results[mod] = {}
                    for gcm, ss2 in ss1.groupby('gcm'):
                        print('{} - {}'.format(mod, gcm))
                        if gcm not in results[mod].keys():
                            results[mod][gcm] = []
                        dflist = parallelize(delayed(expand_rows)(row, suff, reg) for ix, row in ss2.iterrows())
                        df = pd.concat(dflist, axis=0)
                        df.set_index(['region', 'year'], inplace=True)
                        if suff in [age+'_costs_lb', age+'_costs_ub']:
                            df['impact_'+suff] = df['impact_'+suff] / 100000.
                        results[mod][gcm] += [df]
    
    
    ### Aggregate damages
    print('---Aggregating damages')
    damlist = []
    with Parallel(n_jobs=8) as parallelize:
        for mod, modres in results.items():
            model = moddict[mod]
            gcmlist = parallelize(delayed(aggregate_damages)(mod, model, gcm, dflist, rcp, ssp, vsletc, path_data, path_climate) for gcm, dflist in modres.items())
            damlist += [pd.concat(gcmlist, axis=0)]
    damdf = pd.concat(damlist, axis=0)
    damdf.to_csv(path_data + '/damages/global_damages_{}_{}.csv'.format(rcp, ssp))
    
    toc = time.time()
    print('TOTAL TIME: {:.2f}s'.format(toc-tic))
    

def expand_rows(row, suff, reg):
    df = pd.DataFrame()
    df['region'] = reg
    df['impact_'+suff] = eval(row.value)
    df['year'] = row.year
    return df


def aggregate_damages(mod, model, gcm, dflist, rcp, ssp, vsletc, path_data, path_climate):
    write_country = False
    
    ages = ['young', 'older', 'oldest']

    if len(dflist) == 18:
        print('---concatenating {} {}'.format(mod, gcm))
        effect = pd.concat(dflist, axis=1)
        for age in ['young', 'older', 'oldest']:
            effect['effect_'+age] = effect['impact_'+age] - effect['impact_'+age+'_histclim']
            effect['effect_incadapt_'+age] = effect['impact_'+age+'_incadapt'] - effect['impact_'+age+'_histclim']
            effect['effect_noadapt_'+age] = effect['impact_'+age+'_noadapt'] - effect['impact_'+age+'_histclim']
            effect['effect_costs_ub_'+age] = effect['effect_'+age] + effect['impact_'+age+'_costs_ub']
            effect['effect_costs_lb_'+age] = effect['effect_'+age] + effect['impact_'+age+'_costs_lb']
    
        effect = effect.merge(vsletc.loc[(vsletc.model==model), :], how='left', left_index=True, right_index=True)
        effect.reset_index(inplace=True)
    
        vslcols = ['vsl_epa', 'vsl_epa_scaled', 'vsl_epa_popavg', 'vsl_epa_median', 'vsl_ag02', 'vsl_ag02_scaled', 'vsl_ag02_popavg', 'vsl_ag02_median']
        
        for vsl in vslcols:
            for age in ['young', 'older', 'oldest']:
                effect['monetized_effect_'+age+'_'+vsl] = effect['effect_'+age] * effect[vsl]
                effect['monetized_costs_ub_'+age+'_'+vsl] = effect['impact_'+age+'_costs_ub'] * effect[vsl]
                effect['monetized_costs_lb_'+age+'_'+vsl] = effect['impact_'+age+'_costs_lb'] * effect[vsl]
                effect['monetized_effect_costs_ub_'+age+'_'+vsl] = effect['effect_costs_ub_'+age] * effect[vsl]
                effect['monetized_effect_costs_lb_'+age+'_'+vsl] = effect['effect_costs_lb_'+age] * effect[vsl]
        
        effect.to_csv(path_data + '/impactregion_effects/{}/impactregion_effects_{}_{}_{}_{}.csv'.format(ssp, rcp, mod, ssp, gcm))
        
        aggcols = list(effect.columns[[any([age in col for age in ages]) for col in effect.columns]]) + ['gdp', 'pop', 'pop0to4', 'pop5to64', 'pop65plus']
        
        if write_country == True:
            dam = effect.groupby(['iso', 'year'])[aggcols].aggregate(sum).merge(effect.groupby(['iso', 'year'])[vslcols].aggregate(np.mean), left_index=True, right_index=True).reset_index()
            for vsl in vslcols:
                dam['damages_wo_costs_'+vsl] = (dam['monetized_effect_young_'+vsl] + dam['monetized_effect_older_'+vsl] + dam['monetized_effect_oldest_'+vsl]) / dam['gdp']
                dam['damages_costs_ub_'+vsl] = (dam['monetized_effect_costs_ub_young_'+vsl] + dam['monetized_effect_costs_ub_older_'+vsl] + dam['monetized_effect_costs_ub_oldest_'+vsl]) / dam['gdp']
                dam['damages_costs_lb_'+vsl] = (dam['monetized_effect_costs_lb_young_'+vsl] + dam['monetized_effect_costs_lb_older_'+vsl] + dam['monetized_effect_costs_lb_oldest_'+vsl]) / dam['gdp']
            dam.to_csv(path_data + '/damages/{}/country_damages_{}_{}_{}_{}.csv'.format(ssp, rcp, mod, ssp, gcm))
        
        dam = effect.groupby(['year'])[aggcols].aggregate(sum).merge(effect.groupby(['year'])[vslcols].aggregate(np.mean), left_index=True, right_index=True).reset_index()
        for vsl in vslcols:
            dam['damages_wo_costs_'+vsl] = (dam['monetized_effect_young_'+vsl] + dam['monetized_effect_older_'+vsl] + dam['monetized_effect_oldest_'+vsl]) / dam['gdp']
            dam['damages_costs_ub_'+vsl] = (dam['monetized_effect_costs_ub_young_'+vsl] + dam['monetized_effect_costs_ub_older_'+vsl] + dam['monetized_effect_costs_ub_oldest_'+vsl]) / dam['gdp']
            dam['damages_costs_lb_'+vsl] = (dam['monetized_effect_costs_lb_young_'+vsl] + dam['monetized_effect_costs_lb_older_'+vsl] + dam['monetized_effect_costs_lb_oldest_'+vsl]) / dam['gdp']
        gcmlwr = gcm.lower()
        file_climate = glob(os.path.join(path_climate, '{}/{}/global_mean_tas/global_tas_aann_{}_{}_r1i1p1_*.txt'.format(rcp, gcmlwr, gcmlwr, rcp)))[0]
        cli = pd.read_csv(file_climate, skiprows=1, header=None, names=['year', 'globa_tas', 'anomaly'])
        dam = dam.merge(cli, how='inner', on='year')
        dam.to_csv(path_data + '/damages/{}/global_damages_{}_{}_{}_{}.csv'.format(ssp, rcp, mod, ssp, gcm))
        dam['rcp'] = rcp
        dam['mod'] = mod
        dam['ssp'] = ssp
        dam['gcm'] = gcm
        return dam


def main(rcp = 'rcp85', ssp='SSP4'):
    """
    """

    calculate_damages(rcp, ssp)

if __name__ == '__main__':
        
    main()



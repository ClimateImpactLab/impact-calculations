#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  9 19:20:31 2017

@author: theodorkulczycki
"""

import os
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
import time

def calculate_vsl():
    tic = time.time()
    
    def group_wavg(df, valuecol, weightcol, bycols):
        return (df[valuecol] * df[weightcol]).groupby([df[col] for col in bycols]).transform(sum) / df[weightcol].groupby([df[col] for col in bycols]).transform(sum)
    
    
    ### Preliminaries
    vsl = {'epa' : 7400000., 'ag02' : 2097000., 'ag02_d97' : 1540000.}
    moddict = {'high' : 'OECD Env-Growth', 'low' : 'IIASA GDP'}
    
    path_data = os.path.expanduser('~/Dropbox/Work/GCP_Reanalysis/RA_Files/Theo/mortality/damage_function/data')
    path_baselines = '/shares/gcp/social/baselines'
#    path_baselines = os.path.join(path_data, 'baselines')
    
    file_gdppc = os.path.join(path_baselines, 'gdppc.csv')
    file_ageshare = os.path.join(path_baselines, 'cohort_population_aggr.csv')
    file_population = os.path.join(path_baselines, 'population/future/population-future.csv')
    file_output = os.path.join(path_data, 'impactregion_pop_share_gdp_vsl.csv')
    file_zeros = os.path.join(path_data, 'zeros-{}.csv')
    
    
    ### Load number of clipped days data
    dfzsp = pd.read_csv(file_zeros.format('spline'))
    dfzsp.rename(columns={'zero.young':'zero_spline_young', 'zero.older':'zero_spline_older', 'zero.oldest':'zero_spline_oldest'}, inplace=True)
    dfzp5 = pd.read_csv(file_zeros.format('poly5'))
    dfzp5.rename(columns={'zero.young':'zero_poly5_young', 'zero.older':'zero_poly5_older', 'zero.oldest':'zero_poly5_oldest'}, inplace=True)
    dfzp4 = pd.read_csv(file_zeros.format('poly4'))
    dfzp4.rename(columns={'zero.young':'zero_poly4_young', 'zero.older':'zero_poly4_older', 'zero.oldest':'zero_poly4_oldest'}, inplace=True)
    dfz = dfzsp.merge(dfzp5, how='inner', on='year').merge(dfzp4, how='inner', on='year')
    
    ### Load population data
    dfp = pd.read_csv(file_population, skiprows=13)
    dfp = dfp.loc[dfp.model.apply(lambda x: x in moddict.values()), :]
    dfp.rename(columns={'value':'pop'}, inplace=True)
    
    
    ### Load income data
    dfg = pd.read_csv(file_gdppc, skiprows=10)
    dfg = dfg.loc[dfg.model.apply(lambda x: x in moddict.values()), :]
    dfg.rename(columns={'value':'gdppc', 'hierid':'region'}, inplace=True)
    
    
    ### Load age share data
    dfs = pd.read_csv(file_ageshare, delimiter=' *, *', engine='python')
    dfs.rename(columns={'YEAR':'year', 'REGION':'iso', 'MODEL':'model', 'Scenario':'scenario'}, inplace=True)
    dfs.rename(columns={'age0-4':'share0to4', 'age5-64':'share5to64', 'age65+':'share65plus'}, inplace=True)
    dfs = dfs.loc[dfs.model=='IIASA-WiC POP', :]
    dfs = dfs.loc[(dfs.year>=2010) & (dfs.year<=2100), :]
    dfs['ssp'] = dfs.scenario.apply(lambda x: x[:4])
    dfs.drop(['model', 'scenario'], axis=1, inplace=True)
    
    print('data loaded')
    
    ### Merge population, income, and age share data
    df = dfp.merge(dfg, how='inner', on=['year', 'region', 'model', 'scenario'])
    df['iso'] = df.region.apply(lambda x: x[:3])
    df['ssp'] = df.scenario.apply(lambda x: x[:4])
    df.drop(['scenario', 'notes'], axis=1, inplace=True)
    df = df.merge(dfs, how='inner', on=['year', 'iso', 'ssp'])
    df['pop0to4'] = df['pop'] * df.share0to4
    df['pop5to64'] = df['pop'] * df.share5to64
    df['pop65plus'] = df['pop'] * df.share65plus
    #del dfp, dfg, dfs
    
    
    ### Calculate VSL using GDPPC relative to USA 2010
    df['gdp'] = df['gdppc'] * df['pop']
    grouped = df.groupby(['model', 'ssp'])
    for stat in ['gdp', 'pop']:
        groupsum = grouped.apply(lambda x: x.loc[(x['iso']=='USA') & (x['year']==2010), stat].sum())
        groupsum = groupsum.reset_index().rename(columns={0:'usa2010'+stat})
        df = df.merge(groupsum, how='inner', on=['model', 'ssp'])
    #del grouped
    df['usa2010gdppc'] = df.usa2010gdp / df.usa2010pop
    df['ratio'] = df.gdppc / df.usa2010gdppc
    df['vsl_epa'] = vsl['epa']
    df['vsl_epa_scaled'] = df.ratio * vsl['epa']
    df['vsl_epa_unwavg'] = df.groupby(['model', 'ssp', 'year'])['vsl_epa_scaled'].transform(np.mean)
    df['vsl_epa_median'] = df.groupby(['model', 'ssp', 'year'])['vsl_epa_scaled'].transform(np.median)
    df['vsl_epa_popavg'] = group_wavg(df, 'vsl_epa_scaled', 'pop', ['model', 'ssp', 'year'])
    df['vsl_ag02'] = vsl['ag02']
    df['vsl_ag02_scaled'] = df.ratio * vsl['ag02']
    df['vsl_ag02_unwavg'] = df.groupby(['model', 'ssp', 'year'])['vsl_ag02_scaled'].transform(np.mean)
    df['vsl_ag02_median'] = df.groupby(['model', 'ssp', 'year'])['vsl_ag02_scaled'].transform(np.median)
    df['vsl_ag02_popavg'] = group_wavg(df, 'vsl_ag02_scaled', 'pop', ['model', 'ssp', 'year'])
    
    print('vsl calculated')
    
    
    def fill_years(year, yeardf):
        if year != 2100:
            print(year)
            tmp = pd.DataFrame()
            for addyear in range(year, year+5):
                yeardf.drop('year', axis=1, inplace=True)
                yeardf['year'] = addyear
                tmp = tmp.append(yeardf)
        else:
            tmp = yeardf.copy()
        return tmp
    
    ### Fill data between 5 year intervals
    with Parallel(n_jobs=18) as parallelize:
        dflist = parallelize(delayed(fill_years)(year, yeardf.copy()) for year, yeardf in df.groupby('year'))
    
    vsldf = pd.concat(dflist, axis=0)
    vsldf = vsldf.merge(dfz, how='left', on='year')
    vsldf = vsldf.sort_values(['region', 'year']).reset_index(drop=True)
    vsldf.index.name = 'index'
    vsldf.to_csv(file_output)
    
    toc = time.time()
    print('TOTAL TIME: {:.2f}s'.format(toc-tic))


def main():
    """
    """

    calculate_vsl()

if __name__ == '__main__':
        
    main()


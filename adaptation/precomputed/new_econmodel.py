"""NewSSPEconomicModel and iterate_econmodels_new.

Drop-in replacements for SSPEconomicModel and iterate_econmodels that
read pre-computed annual socioeconomic data from the new ir_combined CSV
files instead of reconstructing GDPpc from growth rates and nightlights.

Population is also loaded from the same CSV, replacing the old separate
population data store.

Population-weighted population density (popop) continues to come from
the existing popop_baseline.csv, unchanged.
"""

import os
import numpy as np
import pandas as pd

from impactcommon.exogenous_economy.provider import BySpaceTimeFromSpaceProvider
from .precomputed_provider import PrecomputedGDPpcProvider, _build_filepath
from datastore import popdensity


# The four SSP/IAM combinations available in the new data.
_COMBINATIONS = [
    ("high", "SSP2"),
    ("low", "SSP2"),
    ("high", "SSP3"),
    ("low", "SSP3"),
]


class NewSSPEconomicModel(object):
    """Economic model backed by pre-computed ir_combined CSV data.

    Preserves the full public interface of the original SSPEconomicModel:
        .model, .scenario, .dependencies
        reset()
        baseline_prepared(maxbaseline, numeconyears, func, country_level_gdppc)
        get_loggdppc_year(region, year)
        get_popop_year(region, year)
        get_population_year(region, year)

    Parameters
    ----------
    model : str
        IAM label: "high" (OECD) or "low" (IIASA).
    scenario : str
        SSP label: "SSP2" or "SSP3".
    data_dir : str
        Directory containing the ir_combined_*_v4.csv files.
    config : dict, optional
        Run configuration.  Recognised keys:
        - endbaseline (int, default 2015): last year for baseline pop data.
        - startyear (int, default 2010): first year of GDPpc series.
        - stopyear (int, default 2100): last year of GDPpc series.
    """

    def __init__(self, model, scenario, data_dir, config=None):
        if config is None:
            config = {}

        self.model = model
        self.scenario = scenario
        self.dependencies = []
        self.endbaseline = config.get("endbaseline", 2015)

        startyear = config.get("startyear", 2010)
        stopyear = config.get("stopyear", 2100)

        # -- GDPpc provider --------------------------------------------------
        self._gdppc_provider = PrecomputedGDPpcProvider.from_config(
            iam=model, ssp=scenario, data_dir=data_dir,
            startyear=startyear, stopyear=stopyear,
        )
        self.income_model = BySpaceTimeFromSpaceProvider(self._gdppc_provider)

        # -- Population -------------------------------------------------------
        filepath = _build_filepath(data_dir, scenario, model)
        df = pd.read_csv(filepath)

        self.pop_future_years = {
            hierid: dict(zip(g["year"].values, g["pop"].values))
            for hierid, g in df.groupby("hierid")
        }

        # -- Age cohorts (vectorized) -----------------------------------------
        age_cols = ["pop0to4", "pop5to64", "pop65plus"]
        total_pop = df["pop"].values.astype(np.float64)
        safe_total = np.where(total_pop > 0, total_pop, 1.0)
        shares_arr = df[age_cols].values.astype(np.float64) / safe_total[:, np.newaxis]
        shares_arr[total_pop <= 0] = 0.0

        year_col = df["year"].values.astype(int)
        self._age_shares = {}
        for hierid, g in df.groupby("hierid"):
            idx = g.index.values
            years = year_col[idx]
            self._age_shares[hierid] = {
                int(years[i]): shares_arr[idx[i]] for i in range(len(idx))
            }

        # -- ISO index for age share fallback ---------------------------------
        self._iso_to_hierids = {}
        for hierid in self._age_shares:
            iso = hierid[:3]
            if iso not in self._iso_to_hierids:
                self._iso_to_hierids[iso] = []
            self._iso_to_hierids[iso].append(hierid)

        # -- Popop (population-weighted population density) -------------------
        self.densities = {}

    def reset(self):
        """Reset cached income timeseries."""
        self.income_model.reset()

    def baseline_prepared(self, maxbaseline, numeconyears, func,
                          country_level_gdppc=False):
        """Return {region: {loggdppc: <averaged>, popop: <averaged>}}.

        Mirrors SSPEconomicModel.baseline_prepared: iterates all regions,
        retrieves GDPpc timeseries, computes log, slices to the baseline
        window, and passes through the averaging function (typically a
        Bartlett smoother).
        """
        if not self.densities:
            self.densities = popdensity.load_popop()
        mean_density = np.mean(list(self.densities.values()))

        econ_predictors = {}

        for region in list(self.pop_future_years.keys()):
            query_region = str(region.split(".")[0]) if country_level_gdppc else region

            gdppcs = self.income_model.get_timeseries(query_region)

            startyear = self.income_model.get_startyear()
            if maxbaseline < startyear:
                baseline_gdppcs = [gdppcs[0]]
            else:
                baseline_gdppcs = gdppcs[:maxbaseline - startyear]

            baseline_gdppcs = np.array(baseline_gdppcs, dtype=np.float64)
            baseline_gdppcs[baseline_gdppcs <= 0] = np.nan
            if np.all(np.isnan(baseline_gdppcs)):
                baseline_gdppcs = np.array([1.0])

            popop = self.densities.get(region, mean_density)

            econ_predictors[region] = dict(
                loggdppc=func(np.log(baseline_gdppcs[np.isfinite(baseline_gdppcs)])),
                popop=func([popop]),
            )

        return econ_predictors

    def get_loggdppc_year(self, region, year):
        """Return log GDPpc for a region and year."""
        gdppc = self.income_model.get_value(region, year)
        if gdppc is None or gdppc <= 0:
            return None
        return np.log(gdppc)

    def get_popop_year(self, region, year):
        """Return population-weighted population density for a region and
        year.

        Scales the base popop density by the ratio of the region's
        population in the given year to its population in 2010, matching
        the original SSPEconomicModel behavior.
        """
        if not self.densities:
            self.densities = popdensity.load_popop()

        if region not in self.pop_future_years:
            if region in self.densities:
                return self.densities[region]
            return None
        if region not in self.densities:
            return None

        pop_dict = self.pop_future_years[region]
        if year in pop_dict:
            in2010 = pop_dict.get(2010, 0)
            if in2010 > 0:
                return pop_dict[year] * self.densities[region] / in2010

        return None

    def get_population_year(self, region, year):
        """Return total population for a region and year."""
        if region not in self.pop_future_years:
            return np.nan
        pop_dict = self.pop_future_years[region]
        if year not in pop_dict:
            return np.nan
        return pop_dict[year]

    def get_age_shares(self, region, year):
        """Return age cohort shares [age0-4, age5-64, age65+] for a region
        and year.

        Returns
        -------
        np.array of float
            [share_0to4, share_5to64, share_65plus], or None if unavailable.
        """
        if region not in self._age_shares:
            iso = region[:3]
            candidates = self._iso_to_hierids.get(iso, [])
            for h in candidates:
                if year in self._age_shares[h]:
                    return self._age_shares[h][year]
            return None

        shares = self._age_shares[region]
        if year in shares:
            return shares[year]

        available = sorted(shares.keys())
        if not available:
            return None
        if year < available[0]:
            return shares[available[0]]
        return shares[available[-1]]


def iterate_econmodels_new(config, data_dir):
    """Yield (model, scenario, NewSSPEconomicModel) for each SSP/IAM
    combination.

    Parameters
    ----------
    config : dict
        Run configuration (passed through to NewSSPEconomicModel).
    data_dir : str
        Directory containing ir_combined_*_v4.csv files.

    Yields
    ------
    tuple of (str, str, NewSSPEconomicModel)
        (model, scenario, economic_model) where model is "high"/"low"
        and scenario is "SSP2"/"SSP3".
    """
    for model, scenario in _COMBINATIONS:
        yield model, scenario, NewSSPEconomicModel(model, scenario, data_dir, config)

"""NewSSPEconomicModel and iterate_econmodels_new.

Drop-in replacements for SSPEconomicModel and iterate_econmodels that
read pre-computed annual socioeconomic data from the new ir_combined CSV
files instead of reconstructing GDPpc from growth rates and nightlights.

Population is also loaded from the same CSV, replacing the old separate
population data store.

Population density (popop) is read from the year-2020 row of the same
CSV (GHS-POP base year), eliminating the dependency on popop_baseline.csv.
"""

import os
from collections.abc import Mapping

import numpy as np
import pandas as pd

from impactcommon.exogenous_economy.provider import BySpaceTimeFromSpaceProvider
from .precomputed_provider import PrecomputedGDPpcProvider, _build_filepath


# The four SSP/IAM combinations available in the new data
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
        Directory containing the ir_combined CSV files.
    config : dict, optional
        Run configuration.  Recognised keys:
        - endbaseline (int, default 2015): last year for baseline pop data.
        - startyear (int, default 2010): first year of GDPpc series.
        - stopyear (int, default 2100): last year of GDPpc series.
        - socioeconomic_filename (str, optional): explicit CSV filename
          pattern with {ssp} and {iam_label} slots; defaults to probing
          the known patterns.
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
        filename_pattern = config.get("socioeconomic_filename")

        # -- GDPpc provider --------------------------------------------------
        self._gdppc_provider = PrecomputedGDPpcProvider.from_config(
            iam=model, ssp=scenario, data_dir=data_dir,
            startyear=startyear, stopyear=stopyear,
            filename_pattern=filename_pattern,
        )
        self.income_model = BySpaceTimeFromSpaceProvider(self._gdppc_provider)

        # -- Population -------------------------------------------------------
        filepath = _build_filepath(data_dir, scenario, model, filename_pattern)
        df = pd.read_csv(filepath)

        # One regions x years array instead of a dict per region.
        self.pop_future_years = _PopulationTable(df)

        # -- Age cohorts ------------------------------------------------------
        # Only mortality reads the age shares. Built for every model they
        # take about 0.5 GB each, so they are read from the CSV on first use
        # (see the _age_shares property).
        self._age_shares_path = filepath
        self._age_shares_cache = None

        # -- ISO index for age share fallback ---------------------------------
        # The age shares have the same regions as the population, in the
        # same order.
        self._iso_to_hierids = {}
        for hierid in self.pop_future_years:
            iso = hierid[:3]
            if iso not in self._iso_to_hierids:
                self._iso_to_hierids[iso] = []
            self._iso_to_hierids[iso].append(hierid)

        # -- Popop (population density from GHS-POP base year 2020) -----------
        baseline = df[df["year"] == 2020]
        self.densities = dict(zip(baseline["hierid"], baseline["pop_wtd_density"]))

    @property
    def _age_shares(self):
        """{hierid: {year: [share 0-4, 5-64, 65+]}}, read from the CSV on first use."""
        if self._age_shares_cache is None:
            self._age_shares_cache = _age_shares_from_frame(pd.read_csv(self._age_shares_path))
        return self._age_shares_cache

    @_age_shares.setter
    def _age_shares(self, value):
        self._age_shares_cache = value

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

        Scales the base popop density (from year 2020) by the ratio of
        the region's population in the given year to its population in
        2020, so that get_popop_year(region, 2020) == densities[region].
        """
        if region not in self.pop_future_years:
            if region in self.densities:
                return self.densities[region]
            return None
        if region not in self.densities:
            return None

        pop = self.pop_future_years.value(region, year, _MISSING)
        if pop is not _MISSING:
            in2020 = self.pop_future_years.value(region, 2020, 0)
            if in2020 > 0:
                return pop * self.densities[region] / in2020

        return None

    def get_population_year(self, region, year):
        """Return total population for a region and year (NaN when missing)."""
        return self.pop_future_years.value(region, year, np.nan)

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


# Default for lookups that find nothing, distinct from any stored value.
_MISSING = object()


class _PopulationTable(Mapping):
    """Population by region and year, held in one regions x years array.

    Replaces a {hierid: {year: pop}} dict per region, which kept a numpy
    scalar for every region-year (about 300 MB for each economic model).
    value() returns the same numpy values the dicts held. It reads like the
    old dict: `hierid in table`, iteration in the same region order, and
    table[hierid] gives that region's {year: pop} dict (years in order).

    Parameters
    ----------
    df : pandas.DataFrame
        ir_combined rows with hierid, year (integers) and pop columns.
    """

    def __init__(self, df):
        grouped = df.groupby("hierid")
        # Group numbers follow the order of iterating over the groupby. Rows
        # without a hierid get no group, as in the groupby.
        codes = np.asarray(grouped.ngroup(), dtype=np.float64)
        keep = codes >= 0
        codes = codes[keep].astype(np.int64)
        hierids = np.asarray(df["hierid"].values, dtype=object)[keep]
        years = np.asarray(df["year"].values)[keep]
        pops = np.asarray(df["pop"].values)[keep]
        if years.dtype.kind not in "iu":
            raise ValueError("ir_combined years must be integers, not %s" % years.dtype)

        _, first = np.unique(codes, return_index=True)
        self._hierids = list(hierids[first])
        self._row = {hierid: row for row, hierid in enumerate(self._hierids)}
        self._year_dtype = years.dtype
        self._year0 = int(years.min()) if len(years) else 0
        self._ncols = int(years.max()) - self._year0 + 1 if len(years) else 0

        # A repeated (hierid, year) keeps its last row, as dict(zip()) did.
        cells = codes * self._ncols + (years.astype(np.int64) - self._year0)
        _, last_reversed = np.unique(cells[::-1], return_index=True)
        last = len(cells) - 1 - last_reversed
        shape = (len(self._hierids), self._ncols)
        values = np.zeros(shape[0] * shape[1], dtype=pops.dtype)
        present = np.zeros(shape[0] * shape[1], dtype=bool)
        values[cells[last]] = pops[last]
        present[cells[last]] = True
        self._values = values.reshape(shape)
        self._present = present.reshape(shape)

    def value(self, hierid, year, default=None):
        """Population of hierid in year, or default when the CSV has no such row."""
        row = self._row.get(hierid)
        if row is None:
            return default
        col = self._column(year)
        if col is None or not self._present[row, col]:
            return default
        return self._values[row, col]

    def _column(self, year):
        """Column of year, or None when no row can have it (like 2020.5 or '2020')."""
        try:
            col = int(year) - self._year0
        except (TypeError, ValueError, OverflowError):
            return None
        if not 0 <= col < self._ncols or year != col + self._year0:
            return None
        return col

    def __getitem__(self, hierid):
        row = self._row[hierid]
        cols = np.flatnonzero(self._present[row])
        years = (cols + self._year0).astype(self._year_dtype)
        return dict(zip(years, self._values[row, cols]))

    def __contains__(self, hierid):
        return hierid in self._row

    def __iter__(self):
        return iter(self._hierids)

    def __len__(self):
        return len(self._hierids)


def _age_shares_from_frame(df):
    """{hierid: {year: [share 0-4, 5-64, 65+]}} from ir_combined rows.

    One numpy row view per region-year, as NewSSPEconomicModel always built.
    """
    age_cols = ["pop0to4", "pop5to64", "pop65plus"]
    total_pop = df["pop"].values.astype(np.float64)
    safe_total = np.where(total_pop > 0, total_pop, 1.0)
    shares_arr = df[age_cols].values.astype(np.float64) / safe_total[:, np.newaxis]
    shares_arr[total_pop <= 0] = 0.0

    year_col = df["year"].values.astype(int)
    age_shares = {}
    for hierid, g in df.groupby("hierid"):
        idx = g.index.values
        years = year_col[idx]
        age_shares[hierid] = {
            int(years[i]): shares_arr[idx[i]] for i in range(len(idx))
        }
    return age_shares


class PrecomputedAgeShareBipartiteData(object):
    """Drop-in replacement for agecohorts.SpaceTimeBipartiteData backed by
    hierid-level annual age shares from NewSSPEconomicModel.

    Only supports shareonly=True (the case used by mortality).
    """

    _col_map = {'age0-4': 0, 'age5-64': 1, 'age65+': 2}

    def __init__(self, economicmodel):
        self.economicmodel = economicmodel
        self.regions = list(economicmodel._age_shares.keys())
        self.dependencies = []

    def load(self, year0, year1, model, scenario, agegroup, shareonly=False):
        """Return SpaceTimeLazyData with age shares for one age group.

        Parameters
        ----------
        year0, year1 : int
            Year range (inclusive).
        model, scenario : str
            Ignored (data already loaded from the correct SSP/IAM).
        agegroup : str
            One of 'age0-4', 'age5-64', 'age65+'.
        shareonly : bool
            Must be True (population-weighted shares not implemented).
        """
        assert shareonly, "PrecomputedAgeShareBipartiteData only supports shareonly=True"
        col_idx = self._col_map[agegroup]

        # Precompute all timeseries up front for O(1) lookup in get_time
        all_ts = {}
        for region in self.regions:
            all_ts[region] = self._build_timeseries(region, year0, year1, col_idx)

        # Mean across all regions for fallback
        valid = [ts for ts in all_ts.values() if ts is not None]
        mean_ts = np.mean(valid, axis=0) if valid else np.zeros(year1 - year0 + 1)

        def get_time(region):
            ts = all_ts.get(region)
            if ts is not None:
                return ts
            # Try ISO3 fallback
            iso = region[:3]
            candidates = self.economicmodel._iso_to_hierids.get(iso, [])
            for h in candidates:
                if h in all_ts:
                    return all_ts[h]
            return mean_ts

        from datastore.spacetime import SpaceTimeLazyData
        return SpaceTimeLazyData(year0, year1, self.regions, get_time)

    def _build_timeseries(self, region, year0, year1, col_idx):
        """Build annual timeseries array for one region and age column."""
        shares = self.economicmodel._age_shares.get(region)
        if shares is None:
            return None

        n_years = year1 - year0 + 1
        result = np.zeros(n_years)
        available = sorted(shares.keys())
        if not available:
            return result

        last_val = shares[available[0]][col_idx]
        for i, year in enumerate(range(year0, year1 + 1)):
            if year in shares:
                last_val = shares[year][col_idx]
            elif year < available[0]:
                last_val = shares[available[0]][col_idx]
            result[i] = last_val

        return result


class PrecomputedAgeCohortBipartiteData(object):
    """Drop-in replacement for agecohorts.SpaceTimeBipartiteData that reads
    hierid-level annual population by age cohort from ir_combined CSVs.

    Unlike PrecomputedAgeShareBipartiteData (which wraps a NewSSPEconomicModel
    and only supports shareonly=True), this class reads directly from CSV files
    and supports both shareonly=True (age shares) and shareonly=False
    (age-specific population counts), plus agegroup='total'.

    Intended for use by the aggregation step (generate/aggregate.py) where no
    NewSSPEconomicModel instance is available.

    Parameters
    ----------
    data_dir : str
        Directory containing the ir_combined CSV files.
    filename_pattern : str, optional
        Explicit filename pattern (the socioeconomic_filename config key);
        defaults to probing the known patterns.
    """

    _col_map = {'age0-4': 'pop0to4', 'age5-64': 'pop5to64', 'age65+': 'pop65plus'}

    def __init__(self, data_dir, filename_pattern=None):
        self.data_dir = data_dir
        self.filename_pattern = filename_pattern
        self.year0 = 1981
        self.year1 = 2100
        self.regions = None  # lazily populated on first load
        self.dependencies = []
        self._csv_cache = {}  # (model, scenario) -> DataFrame

    def _load_csv(self, model, scenario):
        """Load and cache the CSV for a given model/scenario."""
        key = (model, scenario)
        if key not in self._csv_cache:
            filepath = _build_filepath(self.data_dir, scenario, model,
                                       self.filename_pattern)
            self._csv_cache[key] = pd.read_csv(filepath)
        return self._csv_cache[key]

    def load(self, year0, year1, model, scenario, agegroup='total', shareonly=False):
        """Return a SpaceTimeLazyData with population weights.

        Parameters
        ----------
        year0, year1 : int
            Year range (inclusive).
        model : str
            IAM label: "high" or "low".
        scenario : str
            SSP label: "SSP2" or "SSP3".
        agegroup : str
            One of 'age0-4', 'age5-64', 'age65+', or 'total'.
        shareonly : bool
            If True, return age share (fraction of total pop).
            If False, return age-specific population count.
            Ignored when agegroup='total'.
        """
        df = self._load_csv(model, scenario)

        if self.regions is None:
            self.regions = df['hierid'].unique().tolist()

        # Build per-hierid timeseries
        all_ts = {}
        iso_to_hierids = {}
        for hierid, g in df.groupby('hierid'):
            g = g.sort_values('year')
            years = g['year'].values.astype(int)
            pop = g['pop'].values.astype(np.float64)

            if agegroup == 'total':
                values = pop
            else:
                col = self._col_map[agegroup]
                age_pop = g[col].values.astype(np.float64)
                if shareonly:
                    safe_pop = np.where(pop > 0, pop, 1.0)
                    values = age_pop / safe_pop
                    values[pop <= 0] = 0.0
                else:
                    values = age_pop

            all_ts[hierid] = _expand_to_annual(years, values, year0, year1)

            iso = hierid[:3]
            if iso not in iso_to_hierids:
                iso_to_hierids[iso] = []
            iso_to_hierids[iso].append(hierid)

        # Mean across all regions for fallback
        valid = [ts for ts in all_ts.values() if ts is not None]
        mean_ts = np.mean(valid, axis=0) if valid else np.zeros(year1 - year0 + 1)

        def get_time(region):
            ts = all_ts.get(region)
            if ts is not None:
                return ts
            # ISO3 fallback
            iso = region[:3]
            candidates = iso_to_hierids.get(iso, [])
            for h in candidates:
                if h in all_ts:
                    return all_ts[h]
            return mean_ts

        from datastore.spacetime import SpaceTimeLazyData
        return SpaceTimeLazyData(year0, year1, self.regions, get_time)


def _expand_to_annual(csv_years, csv_values, year0, year1):
    """Expand year/value pairs to a contiguous annual array [year0, year1].

    Forward-fills gaps; back-fills years before the first available value.
    """
    n = year1 - year0 + 1
    result = np.zeros(n)
    lookup = dict(zip(csv_years, csv_values))
    available = sorted(lookup.keys())
    if not available:
        return result
    last_val = lookup[available[0]]
    for i, yr in enumerate(range(year0, year1 + 1)):
        if yr in lookup:
            last_val = lookup[yr]
        elif yr < available[0]:
            last_val = lookup[available[0]]
        result[i] = last_val
    return result


def iterate_econmodels_new(config, data_dir):
    """Yield (model, scenario, NewSSPEconomicModel) for each SSP/IAM
    combination.

    Parameters
    ----------
    config : dict
        Run configuration (passed through to NewSSPEconomicModel).
    data_dir : str
        Directory containing the ir_combined CSV files.

    Yields
    ------
    tuple of (str, str, NewSSPEconomicModel)
        (model, scenario, economic_model) where model is "high"/"low"
        and scenario is "SSP2"/"SSP3".
    """
    for model, scenario in _COMBINATIONS:
        yield model, scenario, NewSSPEconomicModel(model, scenario, data_dir, config)

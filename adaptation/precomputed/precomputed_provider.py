"""PrecomputedGDPpcProvider: reads pre-computed annual GDPpc at the hierid
level from the new ir_combined CSV files.

Replaces the old HierarchicalGDPpcProvider which reconstructed annual GDPpc
from baseline + quinquennial growth rates + nightlight ratios.
"""

import os
from functools import lru_cache
import numpy as np
import pandas as pd

from impactcommon.exogenous_economy.provider import BySpaceProvider


# Map (ssp, iam) to filename pattern.
# iam "high" = OECD, iam "low" = IIASA (Carleton et al. convention).
_IAM_TO_LABEL = {"high": "OECD", "low": "IIASA"}

# Filename patterns tried in order; {ssp} and {iam_label} are substituted at
# runtime. The first is what the CIL 2.0 pipeline writes; the second is the
# book-reproduction naming.
_FILENAME_PATTERNS = [
    "ir_combined_{ssp}_{iam_label}.csv",
    "ir_combined_{ssp}_{iam_label}_v4.csv",
]


def _build_filepath(data_dir, ssp, iam, pattern=None):
    """Return the full path to the CSV for a given SSP/IAM combination.

    With an explicit pattern (the socioeconomic_filename config key), only
    that pattern is used; otherwise the known patterns are probed in order
    and the first existing file wins.
    """
    iam_label = _IAM_TO_LABEL[iam]
    patterns = [pattern] if pattern else _FILENAME_PATTERNS
    for pat in patterns:
        path = os.path.join(data_dir, pat.format(ssp=ssp, iam_label=iam_label))
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "no socioeconomic CSV for %s/%s in %s; tried %s" % (
            ssp, iam_label, data_dir,
            ", ".join(p.format(ssp=ssp, iam_label=iam_label)
                      for p in patterns)))


class PrecomputedGDPpcProvider(BySpaceProvider):
    """Provider of pre-computed annual GDPpc at the hierid level.

    Reads a single CSV with columns:
        hierid, iso3, year, gdppc, gdppc_raw, gdppc_raw0, gdp, pop,
        area_km2, pop_density, pop0to4, pop5to64, pop65plus

    Uses the ``gdppc_raw`` column as the primary income input to avoid
    double Bartlett smoothing (the projection system applies its own
    Bartlett filter over ln(GDPpc)).

    For years where ``gdppc_raw`` is NA (1981-1989), falls back to the
    ``gdppc`` column (which contains Bartlett-smoothed values).  This is
    acceptable because those early years only enter the Bartlett window
    during the baseline period and the smoothed values are the best
    available estimate for that range.

    Parameters
    ----------
    iam : str
        "high" (OECD) or "low" (IIASA).
    ssp : str
        "SSP2" or "SSP3".
    df : pd.DataFrame
        The loaded CSV data.
    startyear : int
        First year of the returned timeseries.
    stopyear : int
        Last year of the returned timeseries (inclusive).
    """

    def __init__(self, iam, ssp, df, startyear=2010, stopyear=2100):
        super().__init__(iam, ssp, startyear)
        self.stopyear = stopyear

        # Build the GDPpc column: prefer gdppc_raw, fall back to gdppc.
        df = df.copy()
        if "gdppc_raw" in df.columns:
            df["gdppc_use"] = df["gdppc_raw"].fillna(df["gdppc"])
        else:
            # v3 files lack gdppc_raw; use gdppc directly.
            df["gdppc_use"] = df["gdppc"]

        # Filter to the requested year range.
        df = df[(df["year"] >= startyear) & (df["year"] <= stopyear)]

        # Pivot to {hierid: np.array} for fast lookup.
        self._by_hierid = {}
        self._by_hierid_pop = {}  # population arrays, same shape as gdppc
        self._hierid_to_iso = {}
        self._iso_hierids = {}  # {iso: [hierid, ...]}

        for hierid, group in df.groupby("hierid"):
            group = group.sort_values("year")
            values = group["gdppc_use"].values.astype(np.float64)
            pop_values = group["pop"].values.astype(np.float64)

            # Replace any remaining zeros or negatives with NaN, then
            # forward-fill from the nearest valid value.
            values[values <= 0] = np.nan
            mask = np.isnan(values)
            if mask.all():
                # Uninhabited IR -- keep zeros.
                values = np.zeros(len(values))
            elif mask.any():
                # Forward-fill, then back-fill for leading NaNs.
                idx = pd.Series(values)
                idx = idx.ffill().bfill().values
                values = idx

            self._by_hierid[hierid] = values
            self._by_hierid_pop[hierid] = pop_values
            iso = group["iso3"].iloc[0]
            self._hierid_to_iso[hierid] = iso
            if iso not in self._iso_hierids:
                self._iso_hierids[iso] = []
            self._iso_hierids[iso].append(hierid)

        # Pre-compute population-weighted global mean for fallback.
        n_years = stopyear - startyear + 1
        global_weighted_sum = np.zeros(n_years)
        global_pop_sum = np.zeros(n_years)
        for hierid, gdppc_arr in self._by_hierid.items():
            pop_arr = self._by_hierid_pop[hierid]
            inhabited = pop_arr > 0
            global_weighted_sum[inhabited] += gdppc_arr[inhabited] * pop_arr[inhabited]
            global_pop_sum += pop_arr
        safe_global_pop = np.where(global_pop_sum > 0, global_pop_sum, 1.0)
        self._global_mean = global_weighted_sum / safe_global_pop

    @classmethod
    def from_config(cls, iam, ssp, data_dir, startyear=2010, stopyear=2100,
                    filename_pattern=None):
        """Construct from config parameters by loading the appropriate CSV.

        Parameters
        ----------
        iam : str
            "high" or "low".
        ssp : str
            "SSP2" or "SSP3".
        data_dir : str
            Directory containing the ir_combined CSV files.
        startyear : int, optional
        stopyear : int, optional
        filename_pattern : str, optional
            Explicit filename pattern with {ssp} and {iam_label} slots
            (the socioeconomic_filename config key); defaults to probing
            the known patterns.

        Returns
        -------
        PrecomputedGDPpcProvider
        """
        filepath = _build_filepath(data_dir, ssp, iam, filename_pattern)
        df = pd.read_csv(filepath)
        return cls(iam=iam, ssp=ssp, df=df, startyear=startyear, stopyear=stopyear)

    def get_timeseries(self, hierid):
        """Return an np.array of annual GDPpc for the given hierid.

        Fallback chain: hierid -> ISO country mean -> global mean.
        """
        if hierid in self._by_hierid:
            return self._by_hierid[hierid]

        # Fall back through get_iso_timeseries (which is cached).
        iso = hierid[:3]
        return self.get_iso_timeseries(iso)

    @lru_cache(maxsize=None)
    def get_iso_timeseries(self, iso):
        """Return an np.array of population-weighted mean GDPpc for an ISO
        country.

        Falls back to global mean if the ISO is entirely absent.
        """
        hierids = self._iso_hierids.get(iso)
        if hierids is None:
            return self._global_mean.copy()

        n_years = self.stopyear - self.startyear + 1
        weighted_sum = np.zeros(n_years)
        pop_sum = np.zeros(n_years)

        for h in hierids:
            gdppc_arr = self._by_hierid[h]
            pop_arr = self._by_hierid_pop[h]
            inhabited = pop_arr > 0
            weighted_sum[inhabited] += gdppc_arr[inhabited] * pop_arr[inhabited]
            pop_sum += pop_arr

        if pop_sum.sum() == 0:
            return self._global_mean.copy()

        safe_pop = np.where(pop_sum > 0, pop_sum, 1.0)
        return weighted_sum / safe_pop

    @property
    def hierids(self):
        """List of all hierids available in this provider."""
        return list(self._by_hierid.keys())

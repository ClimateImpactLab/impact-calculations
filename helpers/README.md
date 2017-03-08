# Check CSVV Tool

The `checkcsvv.py` checks the formatting of CSVV files.  To use, you
will need to download the entire `impact-calculations` repository, and
install `metacsv` using `pip install metacsv`.

The run `checkcsvv.py` as follows:
```
python -m helpers.checkcsvv CSVV_PATH CLIMATE_DATA_PATH ...
```

 - `CSVV_PATH` is the path to the CSVV file
 - `CLIMATE_DATA_PATH` is a path to any specific NetCDF file containing the predictors, or to a model-specific folder containing individual years.  e.g., either `/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/rcp85/ACCESS1-0/tasmax` or `/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/rcp85/ACCESS1-0/tasmax/tasmax_day_aggregated_rcp85_r1i1p1_ACCESS1-0_2042.nc`


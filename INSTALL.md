Required internal packages (consider using `python setup.py develop`):

 - impact-common
 - impactlab-tools
 - metacsv
 - open-estimate

Required external packages (beyond those required by the internal above):

 - numpy
 - xarray
 - netCDF4
 - gspread
 - statsmodels
 - scipy
 - oauth2client==1.5.2

Server Configuration:

Place a file `server.yml` on directory up, with the location of the GCP shared directory (e.g., `/shares/gcp`).
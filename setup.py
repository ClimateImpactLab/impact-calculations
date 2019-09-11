from setuptools import setup, find_packages


setup(name='impactcalculations',
      version='0.1',
      description='Launch impact projection calculations.',
      url='https://gitlab.com/ClimateImpactLab/Impacts/impact-calculations',
      author='Impacts Team',
      packages=find_packages(),
      license='GNU v. 3',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      install_requires=['numpy', 'xarray', 'netCDF4', 'gspread', 'statsmodels',
                        'scipy', 'oauth2client', 'click', 'impactcommon',
                        'impactlab-tools', 'openest', 'metacsv'],
      tests_require=['pytest'],
      entry_points={
            'console_scripts': [
                  'imperics = cli:impactcalculations_cli',
            ]
      },
      )



def test_mortality():
    return # Incomplete!

    weatherbundle = get_weatherbundle("hadgem2-es").subset("USA")
    economicmodel = StaticModel()

    calculation, dependencies = caller.call_prepare('impacts.health.ACRA_mortality_temperature', weatherbundle, economicmodel, pvals['ACRA_mortality_temperature'])
    results = effectset.generate(targetdir, "ACPMortality", weatherbundle, calculation, None, "Mortality using the ACP response function.", dependencies + weatherbundle.dependencies + economicmodel.dependencies)

if __name__ == '__main__':
    test_mortality()

import re, json
import server, effectset
from openest.models.univariate_model import UnivariateModel
from openest.models.memoizable import MemoizableUnivariate

class UnivariateModelDescriber(UnivariateModel, MemoizableUnivariate):
    def __init__(self, colldict):
        if colldict['xx_is_categorical']:
            super(UnivariateModelDescriber, self).__init__(colldict['xx_is_categorical'], colldict['xx_text'])
        else:
            super(UnivariateModelDescriber, self).__init__(colldict['xx_is_categorical'], list(map(float, colldict['xx_text'])))

        self.colldict = colldict

    def eval_pval_index(self, ii, p, threshold=1e-3):
        return 0

    def __str__(self):
        return str(self.colldict['_id'])

def get_model_info(id):
    result = re.search(r"collection_id=([a-z0-9]+)", id)
    if result:
        fp = server.open_url("/collection/get_collection_info?id=" + result.group(1))
        colldict = json.load(fp)['collection']
        fp.close()

        return UnivariateModelDescriber(colldict)

def get_data_info(id, units):
    """
    Returns data, version
    """
    return dict(id=id), id + ".UNKNOWN"

class PvalsInfoItem:
    def __init__(self, name):
        self.name = name

class PvalsInfoDictionary:
    def __getitem__(self, name):
        return PvalsInfoItem(name)

pvals = PvalsInfoDictionary()

def latex(prepare):
    calculation, dependencies = prepare(pvals, get_model_info, get_data_info)
    for (key, value, units) in calculation.latex():
        print((key + ": " + str(value) + ' [' + units + ']'))

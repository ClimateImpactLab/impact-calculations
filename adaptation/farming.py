"""Functions to support different adaptation scenarios.
"""

def interpret(config):
    """Determine the adaptation scenario from a configuration.

    Parameters
    ----------
    config : dict-like
        A configuration dictionary

    Returns
    -------
    tuple of suffix, adaptation name
    """

    if 'adaptation' not in config or config['adaptation'] == 'fulladapt':
        return '', 'full'
    
    if config['adaptation'] == 'noadapt':
        return 'noadapt', 'noadapt'
    
    if config['adaptation'] == 'incadapt':
        return 'incadapt', 'incadapt'

    raise ValueError("Unknown adaptation scheme " + config['adaptation'])

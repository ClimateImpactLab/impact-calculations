def interpret(config):
    if 'adaptation' not in config or config['adaptation'] == 'fulladapt':
        return '', 'full'
    
    if config['adaptation'] == 'noadapt':
        return 'noadapt', 'noadapt'
    
    if config['adaptation'] == 'incadapt':
        return 'incadapt', 'incadapt'

    raise ValueError("Unknown adaptation scheme " + config['adaptation'])

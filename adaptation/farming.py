def interpret(config):
    if 'adaptation' not in config or config['adaptation'] == 'fulladapt':
        return '', 'full'
    
    if config['adaptation'] == 'noadapt':
        return 'noadapt', 'coma'
    
    if config['adaptation'] == 'incadapt':
        return 'incadapt', 'dumb'

    raise ValueError("Unknown adaptation scheme " + config['adaptation'])

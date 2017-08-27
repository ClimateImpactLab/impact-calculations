def interpret(config):
    assert 'adaptation' in config

    if config['adaptation'] == 'noadapt':
        return 'noadapt', 'coma'
    
    if config['adaptation'] == 'incadapt':
        return 'incadapt', 'dumb'

    if config['adaptation'] == 'fulladapt':
        return '', 'full'
            
    raise ValueError("Unknown adaptation plan.")

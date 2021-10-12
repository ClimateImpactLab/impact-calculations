class UserException(Exception):
    def __init__(self, message, internalexception):
        self.message = message
        self.internalexception = internalexception

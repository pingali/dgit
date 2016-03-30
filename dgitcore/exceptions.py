
class UnknownRepository(Exception):
    """
    Requested repo does not exist
    """
    pass 



class RepositoryExists(Exception):
    """
    Requested repo does not exist
    """
    pass 


class IncompleteParameters(Exception):
    """
    Incomplete parameters
    """
    def __init__(self, missing): 
        super(IncompleteParameters, self).__init__()
        self.missing = missing 


class InvalidParameters(Exception):
    """
    Incomplete parameters
    """
    def __init__(self, invalid): 
        super(InvalidParameters, self).__init__()
        self.invalid = invalid

class NotImplemented(Exception): 
    
    def __init__(self, message): 
        super(NotImplemented, self).__init__()
        self.message = message 

"""
Exceptions
"""
class UnknownRepository(Exception):
    """
    Requested repo does not exist
    """
    pass


class RepositoryExists(Exception):
    """
    Repo already exists
    """
    pass

class IntegrityFailure(Exception):
    """
    Internal integrity checker has failed
    """
    def __init__(self, missing):
        super(IntegrityFailure, self).__init__()
        self.message = message

class IncompleteParameters(Exception):
    """
    Incomplete parameters
    """
    def __init__(self, missing):
        super(IncompleteParameters, self).__init__()
        self.missing = missing


class InvalidParameters(Exception):
    """
    Invalid parameters
    """
    def __init__(self, invalid):
        super(InvalidParameters, self).__init__()
        self.invalid = invalid

class NotImplemented(Exception):
    """
    Functionality not implemented yet
    """
    def __init__(self, message):
        super(NotImplemented, self).__init__()
        self.message = message

class InvalidFilenamePattern(Exception):
    """
    Filename/pattern specified is invalid
    """
    def __init__(self, pattern):
        super(InvalidFilePattern, self).__init__()
        self.pattern = pattern

class InvalidFileContent(Exception):
    """
    Content of the file is not what is expected
    """
    def __init__(self, message):
        super(InvalidFileContent, self).__init__()
        self.message = message

class NetworkError(Exception):
    pass

class NetworkInvalidConfiguration(Exception):

    def __init__(self, message):
        super(NetworkInvalidConfiguration, self).__init__()
        self.message = message


class Fail(Exception):
    pass

class InvalidArgument(Fail):
    pass

class UserFail(Fail):
    pass

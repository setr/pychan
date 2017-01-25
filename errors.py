class e404(Exception):
    def __init__(self):
        self.message = "404 - Page Not Found"


class DNE(Exception):
    def __init__(self, message):
        self.message = message


class Forbidden(Exception):
    def __init__(self, message):
        self.message = message


class PermDenied(Exception):
    def __init__(self, message):
        self.message = message


class BadMedia(Exception):
    def __init__(self, message):
        self.message = message


class BadInput(Exception):
    def __init__(self, message):
        self.message = message

class ImpressionMessageException(Exception):
    """
    Base exception for errors in constructing a message.
    """


class RateLimitException(Exception):
    """
    The rate limit of the service has been reached.
    """


class JSONBodyRequired(Exception):
    """
    The JSON policy requires the body be a JSON object.
    """

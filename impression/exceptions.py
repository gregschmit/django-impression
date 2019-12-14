class RateLimitException(Exception):
    """
    This should be raised when a message cannot be constructed due to the rate limit on
    the service.
    """

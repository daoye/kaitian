from core.exceptions import BrowserError as CoreBrowserError, SessionError, TimeoutError


class BrowserError(CoreBrowserError):
    pass


class BrowserLaunchError(BrowserError):
    pass


class BrowserContextError(BrowserError):
    pass


class BrowserPageError(BrowserError):
    pass


class BrowserCookieError(BrowserError):
    pass


class BrowserSessionError(SessionError):
    pass


class BrowserTimeoutError(TimeoutError):
    pass


class BrowserCdpError(BrowserError):
    """CDP 会话错误"""

    pass

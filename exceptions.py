class InvalidResponseCode(Exception):
    """Неверный код ответа."""

    pass


class ConnectinError(Exception):
    """Неверный код ответа."""

    pass


class NotForSending(Exception):
    """Не для пересылки в телеграм."""

    pass


class EmptyResponseFromAPI(NotForSending):
    """Jт API пришёл пустой ответ."""

    pass

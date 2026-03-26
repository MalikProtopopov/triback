"""Errors for export endpoints."""


class ExportTooLargeError(Exception):
    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(str(count))

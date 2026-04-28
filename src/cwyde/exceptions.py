class CwydeError(Exception):
    pass


class GamenError(CwydeError):
    pass


class GamenBinaryNotFound(GamenError):
    """Raised when no gamen-validate binary can be located."""

    def __init__(self, searched: list[str]):
        self.searched = searched
        paths = "\n  ".join(searched)
        super().__init__(f"gamen-validate not found. Searched:\n  {paths}")


class GamenInvocationError(GamenError):
    """Raised when the gamen-validate process crashes or returns unparseable output."""

    pass


class GamenSemanticError(GamenError):
    """Raised when gamen-validate returns ok=false — indicates a translator bug."""

    def __init__(self, message: str, request: dict):
        self.request = request
        super().__init__(f"gamen-validate semantic error: {message}\nRequest: {request}")


class GamenTimeout(GamenError):
    pass


class KBValidationError(CwydeError):
    pass


class UnknownLanguage(CwydeError):
    pass


class PipelineError(CwydeError):
    pass

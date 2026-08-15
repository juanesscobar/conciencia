"""Custom exceptions for Lead Hunter module.

Permiten categorizar errores para respuestas API estructuradas y retry logic.
"""


class LeadHunterError(Exception):
    """Base exception para errores del Lead Hunter."""

    def __init__(self, message: str, error_type: str = "lead_hunter_error", retry_after: int | None = None):
        self.message = message
        self.error_type = error_type
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d = {"type": self.error_type, "message": self.message}
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


class SourceTimeoutError(LeadHunterError):
    """Timeout al conectar con una fuente externa."""

    def __init__(self, source: str, timeout: int):
        super().__init__(
            message=f"Timeout ({timeout}s) al conectar con fuente '{source}'",
            error_type="source_timeout",
        )
        self.source = source
        self.timeout = timeout


class RateLimitError(LeadHunterError):
    """Rate limit excedido en una fuente externa (HTTP 429)."""

    def __init__(self, source: str, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit excedido en fuente '{source}'",
            error_type="rate_limit",
            retry_after=retry_after,
        )
        self.source = source


class SourceUnavailableError(LeadHunterError):
    """Fuente no disponible (todos los endpoints fallaron)."""

    def __init__(self, source: str, detail: str = ""):
        msg = f"Fuente '{source}' no disponible"
        if detail:
            msg += f": {detail}"
        super().__init__(message=msg, error_type="source_unavailable")
        self.source = source


class InvalidCriteriaError(LeadHunterError):
    """Criterios de busqueda invalidos."""

    def __init__(self, detail: str):
        super().__init__(
            message=f"Criterios invalidos: {detail}",
            error_type="invalid_criteria",
        )


class PartialFailureError(LeadHunterError):
    """Algunas fuentes fallaron pero otras tuvieron exito."""

    def __init__(self, failed_sources: list[str], successful_sources: list[str]):
        self.failed_sources = failed_sources
        self.successful_sources = successful_sources
        msg = f"Fuentes fallidas: {', '.join(failed_sources)}"
        if successful_sources:
            msg += f". Exitosas: {', '.join(successful_sources)}"
        super().__init__(message=msg, error_type="partial_failure")

"""Actionable exception hierarchy for the Change Order Copilot."""


class ChangeOrderCopilotError(Exception):
    """Base class for errors safe to translate into a friendly UI card."""


class DocumentParseError(ChangeOrderCopilotError):
    """Raised when a document cannot be decoded or segmented."""


class ExtractionError(ChangeOrderCopilotError):
    """Raised when a document cannot yield a usable extraction result."""


class ComplianceRuleError(ChangeOrderCopilotError):
    """Raised when metadata is insufficient to apply a compliance rule."""


class ValidationError(ChangeOrderCopilotError):
    """Raised when an input violates a documented safety or schema rule."""


class LLMNotConfigured(ChangeOrderCopilotError):
    """Raised only by strict callers when no optional provider key exists."""


class LLMProviderError(ChangeOrderCopilotError):
    """Raised when an optional provider fails after bounded retries."""

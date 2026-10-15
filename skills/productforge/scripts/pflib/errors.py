"""Exception types and their CLI exit codes.

Exit codes: 0 ok, 1 check failed, 2 usage error / not implemented.
"""

from __future__ import annotations

from typing import Any

EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_USAGE = 2


class PFError(Exception):
    """Base class for every error the CLI reports to the user."""

    exit_code: int = EXIT_USAGE
    code: str = "PF_ERROR"

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code
        if code is not None:
            self.code = code
        self.details: dict[str, Any] = details or {}

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details:
            out["details"] = self.details
        return out


class UsageError(PFError):
    """The command was invoked incorrectly."""

    exit_code = EXIT_USAGE
    code = "USAGE_ERROR"


class CheckFailed(PFError):
    """A validation, gate or lint check did not pass."""

    exit_code = EXIT_CHECK_FAILED
    code = "CHECK_FAILED"


class NotImplementedPF(PFError):
    """The subcommand exists in the CLI contract but is not built yet."""

    exit_code = EXIT_USAGE
    code = "NOT_IMPLEMENTED"

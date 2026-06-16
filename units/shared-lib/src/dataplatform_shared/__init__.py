"""Shared library for the internal data analytics platform.

All other units depend on this package. See aidlc-docs/construction/shared-lib/ for design.
"""

__version__ = "0.1.0"

from dataplatform_shared.errors import DomainError, safe_boundary
from dataplatform_shared.result import Err, Ok, Result, and_then, map_ok

__all__ = [
    "Ok",
    "Err",
    "Result",
    "map_ok",
    "and_then",
    "DomainError",
    "safe_boundary",
    "__version__",
]

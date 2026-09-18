"""
Data module for the contract analyzer.
Contains DTOs and data classes.
"""

from data.models import (
    SourceReference,
    ExtractedField,
    ExtractedData,
    ClauseDTO,
    FindingDTO,
    AnalysisResult,
)

__all__ = [
    "SourceReference",
    "ExtractedField",
    "ExtractedData",
    "ClauseDTO",
    "FindingDTO",
    "AnalysisResult",
]

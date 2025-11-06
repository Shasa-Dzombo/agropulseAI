"""
Search Package

Provides full-text search, indexing, and search analytics capabilities.
"""

from .search_engine import (
    SearchEngine,
    IndexManager,
    QueryBuilder,
    SearchAnalyzer,
    FacetedSearch,
    AutoCompleteEngine,
    GeoSearch
)

__all__ = [
    'SearchEngine',
    'IndexManager',
    'QueryBuilder',
    'SearchAnalyzer',
    'FacetedSearch',
    'AutoCompleteEngine',
    'GeoSearch'
]

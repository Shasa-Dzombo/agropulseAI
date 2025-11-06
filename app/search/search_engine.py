"""
Search & Indexing Engine

Elasticsearch-inspired full-text search system providing:
- Full-text search with BM25 ranking
- Faceted search and aggregations
- Geo-spatial search
- Autocomplete and fuzzy matching
- Search analytics and query logging
- Index management and sharding
- Custom analyzers and tokenizers
- Query DSL (Domain Specific Language)
- Real-time indexing
- Search suggestions and spell correction

This module implements a complete search infrastructure similar to Elasticsearch
but optimized for agricultural data search use cases.
"""

import os
import re
import json
import math
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, Counter
import logging
from pathlib import Path
import threading

import numpy as np
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean,
    ForeignKey, JSON, create_engine, Index as SQLIndex
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)
Base = declarative_base()


class FieldType(Enum):
    """Document field types"""
    TEXT = "text"
    KEYWORD = "keyword"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    GEO_POINT = "geo_point"
    NESTED = "nested"


class QueryType(Enum):
    """Search query types"""
    MATCH = "match"
    TERM = "term"
    RANGE = "range"
    PREFIX = "prefix"
    WILDCARD = "wildcard"
    FUZZY = "fuzzy"
    BOOL = "bool"
    MULTI_MATCH = "multi_match"
    GEO_DISTANCE = "geo_distance"
    GEO_BOUNDING_BOX = "geo_bounding_box"


class AggregationType(Enum):
    """Aggregation types"""
    TERMS = "terms"
    RANGE = "range"
    HISTOGRAM = "histogram"
    DATE_HISTOGRAM = "date_histogram"
    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    STATS = "stats"
    GEO_DISTANCE = "geo_distance"


# Database Models
class SearchIndex(Base):
    """Search index metadata"""
    __tablename__ = 'search_indexes'
    
    index_name = Column(String(256), primary_key=True)
    settings = Column(JSON)
    mappings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    document_count = Column(Integer, default=0)
    size_bytes = Column(Integer, default=0)
    shards = Column(Integer, default=1)
    replicas = Column(Integer, default=0)


class Document(Base):
    """Indexed document"""
    __tablename__ = 'documents'
    
    id = Column(String(256), primary_key=True)
    index_name = Column(String(256), nullable=False)
    source = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)
    
    __table_args__ = (
        SQLIndex('idx_index_name', 'index_name'),
    )


class SearchQuery(Base):
    """Search query log"""
    __tablename__ = 'search_queries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    index_name = Column(String(256), nullable=False)
    query = Column(JSON, nullable=False)
    query_string = Column(Text)
    results_count = Column(Integer)
    execution_time_ms = Column(Float)
    user_id = Column(String(256))
    timestamp = Column(DateTime, default=datetime.utcnow)
    filters = Column(JSON)


@dataclass
class IndexSettings:
    """Index settings configuration"""
    number_of_shards: int = 1
    number_of_replicas: int = 0
    refresh_interval: str = "1s"
    max_result_window: int = 10000
    analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldMapping:
    """Field mapping configuration"""
    type: FieldType
    index: bool = True
    store: bool = False
    analyzer: Optional[str] = None
    search_analyzer: Optional[str] = None
    fields: Dict[str, 'FieldMapping'] = field(default_factory=dict)


@dataclass
class SearchQuery:
    """Search query definition"""
    query: Dict[str, Any]
    size: int = 10
    from_: int = 0
    sort: List[Dict[str, str]] = field(default_factory=list)
    _source: Union[bool, List[str]] = True
    highlight: Dict[str, Any] = field(default_factory=dict)
    aggregations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    post_filter: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Search result"""
    total: int
    max_score: float
    hits: List[Dict[str, Any]]
    aggregations: Dict[str, Any] = field(default_factory=dict)
    took_ms: float = 0


class TextAnalyzer:
    """
    Text analyzer for tokenization and normalization
    
    Supports various analysis strategies like Elasticsearch analyzers.
    """
    
    def __init__(self, analyzer_type: str = "standard"):
        """
        Initialize analyzer
        
        Args:
            analyzer_type: Type of analyzer (standard, simple, whitespace, keyword)
        """
        self.analyzer_type = analyzer_type
        self.stop_words = self._load_stop_words()
    
    def _load_stop_words(self) -> Set[str]:
        """Load English stop words"""
        return {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by', 'for',
            'if', 'in', 'into', 'is', 'it', 'no', 'not', 'of', 'on', 'or',
            'such', 'that', 'the', 'their', 'then', 'there', 'these', 'they',
            'this', 'to', 'was', 'will', 'with'
        }
    
    def analyze(self, text: str) -> List[str]:
        """
        Analyze text into tokens
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        if self.analyzer_type == "standard":
            return self._standard_analyzer(text)
        elif self.analyzer_type == "simple":
            return self._simple_analyzer(text)
        elif self.analyzer_type == "whitespace":
            return self._whitespace_analyzer(text)
        elif self.analyzer_type == "keyword":
            return [text]
        else:
            return self._standard_analyzer(text)
    
    def _standard_analyzer(self, text: str) -> List[str]:
        """Standard analyzer: lowercase, remove punctuation, remove stop words"""
        # Lowercase
        text = text.lower()
        
        # Tokenize on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', text)
        
        # Remove stop words
        tokens = [t for t in tokens if t not in self.stop_words and len(t) > 1]
        
        return tokens
    
    def _simple_analyzer(self, text: str) -> List[str]:
        """Simple analyzer: lowercase, split on non-letter"""
        text = text.lower()
        tokens = re.findall(r'[a-z]+', text)
        return [t for t in tokens if len(t) > 1]
    
    def _whitespace_analyzer(self, text: str) -> List[str]:
        """Whitespace analyzer: split on whitespace only"""
        return text.split()
    
    def ngrams(self, text: str, n: int = 3) -> List[str]:
        """Generate character n-grams for fuzzy matching"""
        text = text.lower()
        if len(text) < n:
            return [text]
        return [text[i:i+n] for i in range(len(text) - n + 1)]


class InvertedIndex:
    """
    Inverted index data structure
    
    Maps terms to documents containing those terms.
    """
    
    def __init__(self):
        """Initialize inverted index"""
        self.index: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
        self.doc_lengths: Dict[str, int] = {}
        self.doc_count: int = 0
        self.avg_doc_length: float = 0
        self.analyzer = TextAnalyzer()
    
    def add_document(self, doc_id: str, field: str, text: str):
        """
        Add document to index
        
        Args:
            doc_id: Document ID
            field: Field name
            text: Text content
        """
        if not text:
            return
        
        tokens = self.analyzer.analyze(text)
        
        # Track document length
        if doc_id not in self.doc_lengths:
            self.doc_lengths[doc_id] = 0
            self.doc_count += 1
        
        self.doc_lengths[doc_id] += len(tokens)
        
        # Add to inverted index with positions
        for pos, token in enumerate(tokens):
            self.index[field][token].append((doc_id, pos))
        
        # Update average document length
        self._update_avg_doc_length()
    
    def _update_avg_doc_length(self):
        """Update average document length"""
        if self.doc_count > 0:
            total_length = sum(self.doc_lengths.values())
            self.avg_doc_length = total_length / self.doc_count
    
    def remove_document(self, doc_id: str):
        """Remove document from index"""
        if doc_id in self.doc_lengths:
            del self.doc_lengths[doc_id]
            self.doc_count -= 1
            
            # Remove from inverted index
            for field in self.index:
                for term in list(self.index[field].keys()):
                    self.index[field][term] = [
                        (did, pos) for did, pos in self.index[field][term]
                        if did != doc_id
                    ]
                    if not self.index[field][term]:
                        del self.index[field][term]
            
            self._update_avg_doc_length()
    
    def search(self, field: str, term: str) -> Set[str]:
        """
        Search for documents containing term
        
        Args:
            field: Field name
            term: Search term
            
        Returns:
            Set of document IDs
        """
        tokens = self.analyzer.analyze(term)
        if not tokens:
            return set()
        
        # Get documents for first token
        result = set()
        if tokens[0] in self.index.get(field, {}):
            result = {doc_id for doc_id, _ in self.index[field][tokens[0]]}
        
        # Intersect with documents for other tokens
        for token in tokens[1:]:
            if token in self.index.get(field, {}):
                token_docs = {doc_id for doc_id, _ in self.index[field][token]}
                result &= token_docs
            else:
                return set()
        
        return result
    
    def get_term_frequency(self, doc_id: str, field: str, term: str) -> int:
        """Get term frequency in document"""
        tokens = self.analyzer.analyze(term)
        if not tokens:
            return 0
        
        count = 0
        for token in tokens:
            if token in self.index.get(field, {}):
                count += sum(1 for did, _ in self.index[field][token] if did == doc_id)
        
        return count
    
    def get_document_frequency(self, field: str, term: str) -> int:
        """Get number of documents containing term"""
        tokens = self.analyzer.analyze(term)
        if not tokens or tokens[0] not in self.index.get(field, {}):
            return 0
        
        return len(set(doc_id for doc_id, _ in self.index[field][tokens[0]]))
    
    def save(self, filepath: str):
        """Save index to file"""
        data = {
            'index': dict(self.index),
            'doc_lengths': self.doc_lengths,
            'doc_count': self.doc_count,
            'avg_doc_length': self.avg_doc_length
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, filepath: str):
        """Load index from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.index = defaultdict(lambda: defaultdict(list), data['index'])
        self.doc_lengths = data['doc_lengths']
        self.doc_count = data['doc_count']
        self.avg_doc_length = data['avg_doc_length']


class BM25Scorer:
    """
    BM25 scoring algorithm
    
    Best Match 25 - probabilistic relevance ranking function.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 scorer
        
        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
    
    def score(self, tf: int, df: int, doc_length: int, 
             avg_doc_length: float, total_docs: int) -> float:
        """
        Calculate BM25 score
        
        Args:
            tf: Term frequency in document
            df: Document frequency of term
            doc_length: Length of document
            avg_doc_length: Average document length
            total_docs: Total number of documents
            
        Returns:
            BM25 score
        """
        # IDF component
        idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
        
        # Term frequency component with length normalization
        norm = 1 - self.b + self.b * (doc_length / avg_doc_length)
        tf_component = (tf * (self.k1 + 1)) / (tf + self.k1 * norm)
        
        return idf * tf_component


class QueryBuilder:
    """
    Query DSL builder
    
    Provides fluent API for building complex queries.
    """
    
    def __init__(self):
        self.query_dict: Dict[str, Any] = {}
    
    def match(self, field: str, query: str, operator: str = "or") -> 'QueryBuilder':
        """Full-text match query"""
        self.query_dict = {
            "match": {
                field: {
                    "query": query,
                    "operator": operator
                }
            }
        }
        return self
    
    def term(self, field: str, value: Any) -> 'QueryBuilder':
        """Exact term query"""
        self.query_dict = {
            "term": {
                field: value
            }
        }
        return self
    
    def range(self, field: str, gte: Any = None, lte: Any = None,
             gt: Any = None, lt: Any = None) -> 'QueryBuilder':
        """Range query"""
        range_params = {}
        if gte is not None:
            range_params["gte"] = gte
        if lte is not None:
            range_params["lte"] = lte
        if gt is not None:
            range_params["gt"] = gt
        if lt is not None:
            range_params["lt"] = lt
        
        self.query_dict = {
            "range": {
                field: range_params
            }
        }
        return self
    
    def prefix(self, field: str, value: str) -> 'QueryBuilder':
        """Prefix query"""
        self.query_dict = {
            "prefix": {
                field: value
            }
        }
        return self
    
    def wildcard(self, field: str, value: str) -> 'QueryBuilder':
        """Wildcard query"""
        self.query_dict = {
            "wildcard": {
                field: value
            }
        }
        return self
    
    def fuzzy(self, field: str, value: str, fuzziness: int = 2) -> 'QueryBuilder':
        """Fuzzy query"""
        self.query_dict = {
            "fuzzy": {
                field: {
                    "value": value,
                    "fuzziness": fuzziness
                }
            }
        }
        return self
    
    def bool_query(self, must: List[Dict] = None, should: List[Dict] = None,
                  must_not: List[Dict] = None, filter: List[Dict] = None) -> 'QueryBuilder':
        """Boolean query"""
        bool_params = {}
        if must:
            bool_params["must"] = must
        if should:
            bool_params["should"] = should
        if must_not:
            bool_params["must_not"] = must_not
        if filter:
            bool_params["filter"] = filter
        
        self.query_dict = {
            "bool": bool_params
        }
        return self
    
    def multi_match(self, query: str, fields: List[str], 
                   operator: str = "or") -> 'QueryBuilder':
        """Multi-field match query"""
        self.query_dict = {
            "multi_match": {
                "query": query,
                "fields": fields,
                "operator": operator
            }
        }
        return self
    
    def geo_distance(self, field: str, distance: str, 
                    lat: float, lon: float) -> 'QueryBuilder':
        """Geo distance query"""
        self.query_dict = {
            "geo_distance": {
                "distance": distance,
                field: {
                    "lat": lat,
                    "lon": lon
                }
            }
        }
        return self
    
    def geo_bounding_box(self, field: str, top_left: Tuple[float, float],
                        bottom_right: Tuple[float, float]) -> 'QueryBuilder':
        """Geo bounding box query"""
        self.query_dict = {
            "geo_bounding_box": {
                field: {
                    "top_left": {
                        "lat": top_left[0],
                        "lon": top_left[1]
                    },
                    "bottom_right": {
                        "lat": bottom_right[0],
                        "lon": bottom_right[1]
                    }
                }
            }
        }
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build final query"""
        return self.query_dict


class FacetedSearch:
    """
    Faceted search implementation
    
    Provides aggregations and facets for filtering.
    """
    
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
    
    def terms_aggregation(self, field: str, size: int = 10) -> Dict[str, int]:
        """
        Terms aggregation
        
        Args:
            field: Field to aggregate
            size: Maximum number of buckets
            
        Returns:
            Dictionary of term counts
        """
        counts = Counter()
        
        for doc in self.documents:
            value = self._get_nested_value(doc, field)
            if value is not None:
                if isinstance(value, list):
                    counts.update(value)
                else:
                    counts[str(value)] += 1
        
        return dict(counts.most_common(size))
    
    def range_aggregation(self, field: str, 
                         ranges: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Range aggregation
        
        Args:
            field: Field to aggregate
            ranges: List of range definitions
            
        Returns:
            Dictionary of range counts
        """
        buckets = defaultdict(int)
        
        for doc in self.documents:
            value = self._get_nested_value(doc, field)
            if value is None:
                continue
            
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            
            for range_def in ranges:
                key = range_def.get('key', '')
                from_val = range_def.get('from', float('-inf'))
                to_val = range_def.get('to', float('inf'))
                
                if from_val <= value < to_val:
                    buckets[key] += 1
        
        return dict(buckets)
    
    def stats_aggregation(self, field: str) -> Dict[str, float]:
        """
        Statistics aggregation
        
        Args:
            field: Field to aggregate
            
        Returns:
            Statistics dictionary
        """
        values = []
        
        for doc in self.documents:
            value = self._get_nested_value(doc, field)
            if value is not None:
                try:
                    values.append(float(value))
                except (ValueError, TypeError):
                    pass
        
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'sum': sum(values)
        }
    
    def date_histogram_aggregation(self, field: str, 
                                   interval: str = "day") -> Dict[str, int]:
        """
        Date histogram aggregation
        
        Args:
            field: Date field
            interval: Interval (day, week, month, year)
            
        Returns:
            Dictionary of date buckets
        """
        buckets = defaultdict(int)
        
        for doc in self.documents:
            value = self._get_nested_value(doc, field)
            if value is None:
                continue
            
            try:
                if isinstance(value, str):
                    date = datetime.fromisoformat(value)
                else:
                    date = value
                
                # Create bucket key based on interval
                if interval == "day":
                    key = date.strftime("%Y-%m-%d")
                elif interval == "week":
                    key = date.strftime("%Y-W%W")
                elif interval == "month":
                    key = date.strftime("%Y-%m")
                elif interval == "year":
                    key = date.strftime("%Y")
                else:
                    key = date.strftime("%Y-%m-%d")
                
                buckets[key] += 1
            except (ValueError, TypeError, AttributeError):
                pass
        
        return dict(sorted(buckets.items()))
    
    def _get_nested_value(self, doc: Dict[str, Any], field: str) -> Any:
        """Get nested field value from document"""
        keys = field.split('.')
        value = doc
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value


class AutoCompleteEngine:
    """
    Autocomplete and suggestion engine
    
    Provides search-as-you-type functionality.
    """
    
    def __init__(self):
        self.trie = {}
        self.suggestions: Dict[str, int] = defaultdict(int)
        self.analyzer = TextAnalyzer()
    
    def add_phrase(self, phrase: str, weight: int = 1):
        """
        Add phrase to autocomplete index
        
        Args:
            phrase: Phrase to index
            weight: Importance weight
        """
        phrase_lower = phrase.lower()
        self.suggestions[phrase_lower] += weight
        
        # Add to trie
        node = self.trie
        for char in phrase_lower:
            if char not in node:
                node[char] = {}
            node = node[char]
        
        # Mark end of phrase
        node['$'] = phrase_lower
    
    def suggest(self, prefix: str, max_results: int = 10) -> List[Tuple[str, int]]:
        """
        Get autocomplete suggestions
        
        Args:
            prefix: Input prefix
            max_results: Maximum suggestions
            
        Returns:
            List of (suggestion, weight) tuples
        """
        prefix_lower = prefix.lower()
        
        # Navigate to prefix node
        node = self.trie
        for char in prefix_lower:
            if char not in node:
                return []
            node = node[char]
        
        # Collect all phrases with this prefix
        phrases = []
        self._collect_phrases(node, phrases)
        
        # Sort by weight and return top results
        weighted = [(p, self.suggestions[p]) for p in phrases]
        weighted.sort(key=lambda x: x[1], reverse=True)
        
        return weighted[:max_results]
    
    def _collect_phrases(self, node: Dict, phrases: List[str]):
        """Recursively collect phrases from trie"""
        if '$' in node:
            phrases.append(node['$'])
        
        for key, child in node.items():
            if key != '$':
                self._collect_phrases(child, phrases)
    
    def fuzzy_suggest(self, query: str, max_distance: int = 2,
                     max_results: int = 10) -> List[Tuple[str, int]]:
        """
        Fuzzy autocomplete suggestions
        
        Args:
            query: Search query
            max_distance: Maximum edit distance
            max_results: Maximum suggestions
            
        Returns:
            List of (suggestion, score) tuples
        """
        query_lower = query.lower()
        candidates = []
        
        for phrase, weight in self.suggestions.items():
            distance = self._levenshtein_distance(query_lower, phrase)
            if distance <= max_distance:
                # Score combines weight and edit distance
                score = weight / (1 + distance)
                candidates.append((phrase, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:max_results]
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]


class GeoSearch:
    """
    Geo-spatial search
    
    Search based on geographic coordinates.
    """
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def geo_distance_filter(documents: List[Dict[str, Any]], 
                           field: str,
                           center_lat: float,
                           center_lon: float,
                           distance_km: float) -> List[Dict[str, Any]]:
        """
        Filter documents by distance from center point
        
        Args:
            documents: List of documents
            field: Geo point field name
            center_lat, center_lon: Center coordinates
            distance_km: Maximum distance in km
            
        Returns:
            Filtered documents
        """
        filtered = []
        
        for doc in documents:
            geo_point = doc.get(field)
            if not geo_point:
                continue
            
            doc_lat = geo_point.get('lat')
            doc_lon = geo_point.get('lon')
            
            if doc_lat is None or doc_lon is None:
                continue
            
            dist = GeoSearch.haversine_distance(
                center_lat, center_lon, doc_lat, doc_lon
            )
            
            if dist <= distance_km:
                doc['_distance'] = dist
                filtered.append(doc)
        
        # Sort by distance
        filtered.sort(key=lambda x: x['_distance'])
        return filtered
    
    @staticmethod
    def geo_bounding_box_filter(documents: List[Dict[str, Any]],
                               field: str,
                               top_left: Tuple[float, float],
                               bottom_right: Tuple[float, float]) -> List[Dict[str, Any]]:
        """
        Filter documents within bounding box
        
        Args:
            documents: List of documents
            field: Geo point field name
            top_left: (lat, lon) of top-left corner
            bottom_right: (lat, lon) of bottom-right corner
            
        Returns:
            Filtered documents
        """
        filtered = []
        
        for doc in documents:
            geo_point = doc.get(field)
            if not geo_point:
                continue
            
            doc_lat = geo_point.get('lat')
            doc_lon = geo_point.get('lon')
            
            if doc_lat is None or doc_lon is None:
                continue
            
            # Check if within bounding box
            if (bottom_right[0] <= doc_lat <= top_left[0] and
                top_left[1] <= doc_lon <= bottom_right[1]):
                filtered.append(doc)
        
        return filtered


class SearchAnalyzer:
    """
    Search analytics and query analysis
    
    Tracks search patterns and provides insights.
    """
    
    def __init__(self, session_maker):
        self.Session = session_maker
    
    def log_query(self, index_name: str, query: Dict[str, Any],
                 query_string: str, results_count: int,
                 execution_time_ms: float, user_id: Optional[str] = None,
                 filters: Dict[str, Any] = None):
        """Log search query"""
        session = self.Session()
        try:
            query_log = SearchQuery(
                index_name=index_name,
                query=query,
                query_string=query_string,
                results_count=results_count,
                execution_time_ms=execution_time_ms,
                user_id=user_id,
                filters=filters
            )
            session.add(query_log)
            session.commit()
        finally:
            session.close()
    
    def get_popular_queries(self, index_name: str, 
                           limit: int = 10,
                           time_range: Optional[timedelta] = None) -> List[Tuple[str, int]]:
        """
        Get most popular queries
        
        Args:
            index_name: Index name
            limit: Number of results
            time_range: Time range for analysis
            
        Returns:
            List of (query, count) tuples
        """
        session = self.Session()
        try:
            query = session.query(SearchQuery).filter_by(index_name=index_name)
            
            if time_range:
                cutoff = datetime.utcnow() - time_range
                query = query.filter(SearchQuery.timestamp >= cutoff)
            
            queries = query.all()
            
            # Count query strings
            query_counts = Counter(q.query_string for q in queries if q.query_string)
            
            return query_counts.most_common(limit)
        finally:
            session.close()
    
    def get_zero_result_queries(self, index_name: str,
                               limit: int = 10) -> List[str]:
        """Get queries that returned no results"""
        session = self.Session()
        try:
            queries = session.query(SearchQuery).filter_by(
                index_name=index_name,
                results_count=0
            ).order_by(SearchQuery.timestamp.desc()).limit(limit).all()
            
            return [q.query_string for q in queries if q.query_string]
        finally:
            session.close()
    
    def get_slow_queries(self, index_name: str,
                        threshold_ms: float = 1000,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries"""
        session = self.Session()
        try:
            queries = session.query(SearchQuery).filter(
                SearchQuery.index_name == index_name,
                SearchQuery.execution_time_ms >= threshold_ms
            ).order_by(SearchQuery.execution_time_ms.desc()).limit(limit).all()
            
            return [{
                'query': q.query_string,
                'execution_time_ms': q.execution_time_ms,
                'timestamp': q.timestamp
            } for q in queries]
        finally:
            session.close()
    
    def get_search_metrics(self, index_name: str,
                          time_range: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """Get search metrics summary"""
        session = self.Session()
        try:
            cutoff = datetime.utcnow() - time_range
            queries = session.query(SearchQuery).filter(
                SearchQuery.index_name == index_name,
                SearchQuery.timestamp >= cutoff
            ).all()
            
            if not queries:
                return {}
            
            execution_times = [q.execution_time_ms for q in queries if q.execution_time_ms]
            results_counts = [q.results_count for q in queries if q.results_count is not None]
            
            return {
                'total_queries': len(queries),
                'unique_queries': len(set(q.query_string for q in queries if q.query_string)),
                'avg_execution_time_ms': sum(execution_times) / len(execution_times) if execution_times else 0,
                'avg_results': sum(results_counts) / len(results_counts) if results_counts else 0,
                'zero_result_rate': sum(1 for c in results_counts if c == 0) / len(results_counts) if results_counts else 0
            }
        finally:
            session.close()


class IndexManager:
    """
    Index management
    
    Creates and manages search indexes.
    """
    
    def __init__(self, session_maker, storage_path: str = "./indexes"):
        self.Session = session_maker
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.indexes: Dict[str, InvertedIndex] = {}
        self._lock = threading.Lock()
    
    def create_index(self, index_name: str, settings: IndexSettings,
                    mappings: Dict[str, FieldMapping]) -> bool:
        """
        Create a new index
        
        Args:
            index_name: Index name
            settings: Index settings
            mappings: Field mappings
            
        Returns:
            True if created successfully
        """
        session = self.Session()
        try:
            # Check if exists
            existing = session.query(SearchIndex).filter_by(
                index_name=index_name
            ).first()
            
            if existing:
                logger.warning(f"Index already exists: {index_name}")
                return False
            
            # Create index metadata
            index_model = SearchIndex(
                index_name=index_name,
                settings=asdict(settings),
                mappings={k: asdict(v) for k, v in mappings.items()},
                shards=settings.number_of_shards,
                replicas=settings.number_of_replicas
            )
            
            session.add(index_model)
            session.commit()
            
            # Create inverted index
            with self._lock:
                self.indexes[index_name] = InvertedIndex()
            
            logger.info(f"Created index: {index_name}")
            return True
            
        finally:
            session.close()
    
    def delete_index(self, index_name: str) -> bool:
        """Delete an index"""
        session = self.Session()
        try:
            # Delete metadata
            index_model = session.query(SearchIndex).filter_by(
                index_name=index_name
            ).first()
            
            if not index_model:
                return False
            
            session.delete(index_model)
            
            # Delete documents
            session.query(Document).filter_by(index_name=index_name).delete()
            
            session.commit()
            
            # Delete inverted index
            with self._lock:
                if index_name in self.indexes:
                    del self.indexes[index_name]
            
            # Delete index file
            index_file = self.storage_path / f"{index_name}.idx"
            if index_file.exists():
                index_file.unlink()
            
            logger.info(f"Deleted index: {index_name}")
            return True
            
        finally:
            session.close()
    
    def get_index(self, index_name: str) -> Optional[SearchIndex]:
        """Get index metadata"""
        session = self.Session()
        try:
            return session.query(SearchIndex).filter_by(
                index_name=index_name
            ).first()
        finally:
            session.close()
    
    def list_indexes(self) -> List[SearchIndex]:
        """List all indexes"""
        session = self.Session()
        try:
            return session.query(SearchIndex).all()
        finally:
            session.close()
    
    def load_index(self, index_name: str) -> Optional[InvertedIndex]:
        """Load inverted index from disk"""
        with self._lock:
            if index_name in self.indexes:
                return self.indexes[index_name]
            
            index_file = self.storage_path / f"{index_name}.idx"
            if not index_file.exists():
                self.indexes[index_name] = InvertedIndex()
                return self.indexes[index_name]
            
            inverted_index = InvertedIndex()
            inverted_index.load(str(index_file))
            self.indexes[index_name] = inverted_index
            
            return inverted_index
    
    def save_index(self, index_name: str):
        """Save inverted index to disk"""
        with self._lock:
            if index_name not in self.indexes:
                return
            
            index_file = self.storage_path / f"{index_name}.idx"
            self.indexes[index_name].save(str(index_file))


class SearchEngine:
    """
    Main search engine
    
    Orchestrates indexing and searching operations.
    """
    
    def __init__(self, db_uri: str = "sqlite:///search.db",
                 storage_path: str = "./indexes"):
        """
        Initialize search engine
        
        Args:
            db_uri: Database connection string
            storage_path: Index storage path
        """
        self.engine = create_engine(db_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        self.index_manager = IndexManager(self.Session, storage_path)
        self.scorer = BM25Scorer()
        self.analyzer = SearchAnalyzer(self.Session)
        self.autocomplete = AutoCompleteEngine()
    
    def create_index(self, index_name: str, settings: IndexSettings = None,
                    mappings: Dict[str, FieldMapping] = None) -> bool:
        """Create a new index"""
        settings = settings or IndexSettings()
        mappings = mappings or {}
        
        return self.index_manager.create_index(index_name, settings, mappings)
    
    def index_document(self, index_name: str, doc_id: str, 
                      document: Dict[str, Any]) -> bool:
        """
        Index a document
        
        Args:
            index_name: Index name
            doc_id: Document ID
            document: Document to index
            
        Returns:
            True if indexed successfully
        """
        session = self.Session()
        try:
            # Load inverted index
            inverted_index = self.index_manager.load_index(index_name)
            if not inverted_index:
                logger.error(f"Index not found: {index_name}")
                return False
            
            # Index document
            for field, value in document.items():
                if isinstance(value, str):
                    inverted_index.add_document(doc_id, field, value)
                    # Add to autocomplete
                    self.autocomplete.add_phrase(value)
            
            # Store document
            doc_model = Document(
                id=doc_id,
                index_name=index_name,
                source=document
            )
            
            session.merge(doc_model)
            
            # Update index stats
            index_model = session.query(SearchIndex).filter_by(
                index_name=index_name
            ).first()
            
            if index_model:
                index_model.document_count = inverted_index.doc_count
                index_model.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Save inverted index periodically
            if inverted_index.doc_count % 100 == 0:
                self.index_manager.save_index(index_name)
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to index document: {e}")
            return False
        finally:
            session.close()
    
    def bulk_index(self, index_name: str, 
                   documents: List[Tuple[str, Dict[str, Any]]]) -> int:
        """
        Bulk index documents
        
        Args:
            index_name: Index name
            documents: List of (doc_id, document) tuples
            
        Returns:
            Number of documents indexed
        """
        indexed = 0
        for doc_id, document in documents:
            if self.index_document(index_name, doc_id, document):
                indexed += 1
        
        # Save index after bulk operation
        self.index_manager.save_index(index_name)
        
        return indexed
    
    def search(self, index_name: str, query: Dict[str, Any],
              size: int = 10, from_: int = 0,
              sort: List[Dict[str, str]] = None,
              aggregations: Dict[str, Dict[str, Any]] = None) -> SearchResult:
        """
        Execute search query
        
        Args:
            index_name: Index name
            query: Query definition
            size: Number of results
            from_: Offset
            sort: Sort specifications
            aggregations: Aggregation definitions
            
        Returns:
            Search results
        """
        start_time = datetime.utcnow()
        
        try:
            # Load inverted index
            inverted_index = self.index_manager.load_index(index_name)
            if not inverted_index:
                return SearchResult(total=0, max_score=0, hits=[])
            
            # Get all documents
            session = self.Session()
            all_docs = session.query(Document).filter_by(
                index_name=index_name
            ).all()
            session.close()
            
            # Execute query
            scored_docs = self._execute_query(query, inverted_index, all_docs)
            
            # Sort results
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Apply pagination
            paginated = scored_docs[from_:from_ + size]
            
            # Build hits
            hits = []
            max_score = scored_docs[0][1] if scored_docs else 0
            
            for doc, score in paginated:
                hit = {
                    '_id': doc.id,
                    '_score': score,
                    '_source': doc.source
                }
                hits.append(hit)
            
            # Execute aggregations
            agg_results = {}
            if aggregations:
                sources = [doc.source for doc, _ in scored_docs]
                faceted = FacetedSearch(sources)
                
                for agg_name, agg_def in aggregations.items():
                    agg_type = list(agg_def.keys())[0]
                    agg_params = agg_def[agg_type]
                    
                    if agg_type == "terms":
                        agg_results[agg_name] = faceted.terms_aggregation(
                            agg_params['field'],
                            agg_params.get('size', 10)
                        )
                    elif agg_type == "stats":
                        agg_results[agg_name] = faceted.stats_aggregation(
                            agg_params['field']
                        )
            
            # Calculate execution time
            took_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log query
            query_string = self._extract_query_string(query)
            self.analyzer.log_query(
                index_name=index_name,
                query=query,
                query_string=query_string,
                results_count=len(scored_docs),
                execution_time_ms=took_ms
            )
            
            return SearchResult(
                total=len(scored_docs),
                max_score=max_score,
                hits=hits,
                aggregations=agg_results,
                took_ms=took_ms
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return SearchResult(total=0, max_score=0, hits=[])
    
    def _execute_query(self, query: Dict[str, Any], 
                      inverted_index: InvertedIndex,
                      all_docs: List[Document]) -> List[Tuple[Document, float]]:
        """Execute query and score documents"""
        query_type = list(query.keys())[0]
        query_params = query[query_type]
        
        if query_type == "match":
            return self._match_query(query_params, inverted_index, all_docs)
        elif query_type == "term":
            return self._term_query(query_params, inverted_index, all_docs)
        elif query_type == "bool":
            return self._bool_query(query_params, inverted_index, all_docs)
        elif query_type == "multi_match":
            return self._multi_match_query(query_params, inverted_index, all_docs)
        else:
            return []
    
    def _match_query(self, params: Dict[str, Any],
                    inverted_index: InvertedIndex,
                    all_docs: List[Document]) -> List[Tuple[Document, float]]:
        """Execute match query"""
        field = list(params.keys())[0]
        query_text = params[field]['query'] if isinstance(params[field], dict) else params[field]
        
        # Find matching documents
        matching_doc_ids = inverted_index.search(field, query_text)
        
        # Score documents
        scored = []
        for doc in all_docs:
            if doc.id in matching_doc_ids:
                # Calculate BM25 score
                tf = inverted_index.get_term_frequency(doc.id, field, query_text)
                df = inverted_index.get_document_frequency(field, query_text)
                doc_length = inverted_index.doc_lengths.get(doc.id, 0)
                
                score = self.scorer.score(
                    tf=tf,
                    df=df,
                    doc_length=doc_length,
                    avg_doc_length=inverted_index.avg_doc_length,
                    total_docs=inverted_index.doc_count
                )
                
                scored.append((doc, score))
        
        return scored
    
    def _term_query(self, params: Dict[str, Any],
                   inverted_index: InvertedIndex,
                   all_docs: List[Document]) -> List[Tuple[Document, float]]:
        """Execute term query"""
        field = list(params.keys())[0]
        value = params[field]
        
        scored = []
        for doc in all_docs:
            doc_value = doc.source.get(field)
            if doc_value == value:
                scored.append((doc, 1.0))
        
        return scored
    
    def _bool_query(self, params: Dict[str, Any],
                   inverted_index: InvertedIndex,
                   all_docs: List[Document]) -> List[Tuple[Document, float]]:
        """Execute boolean query"""
        must = params.get('must', [])
        should = params.get('should', [])
        must_not = params.get('must_not', [])
        
        # Start with all documents
        candidates = {doc.id: doc for doc in all_docs}
        scores = defaultdict(float)
        
        # Process must clauses
        for clause in must:
            clause_results = self._execute_query(clause, inverted_index, all_docs)
            clause_ids = {doc.id for doc, _ in clause_results}
            candidates = {id: doc for id, doc in candidates.items() if id in clause_ids}
            
            for doc, score in clause_results:
                scores[doc.id] += score
        
        # Process must_not clauses
        for clause in must_not:
            clause_results = self._execute_query(clause, inverted_index, all_docs)
            exclude_ids = {doc.id for doc, _ in clause_results}
            candidates = {id: doc for id, doc in candidates.items() if id not in exclude_ids}
        
        # Process should clauses
        for clause in should:
            clause_results = self._execute_query(clause, inverted_index, all_docs)
            for doc, score in clause_results:
                if doc.id in candidates:
                    scores[doc.id] += score
        
        # Build final results
        return [(doc, scores[doc.id]) for doc in candidates.values()]
    
    def _multi_match_query(self, params: Dict[str, Any],
                          inverted_index: InvertedIndex,
                          all_docs: List[Document]) -> List[Tuple[Document, float]]:
        """Execute multi-match query"""
        query_text = params['query']
        fields = params['fields']
        
        # Search across multiple fields
        all_scores = defaultdict(float)
        
        for field in fields:
            field_query = {'match': {field: query_text}}
            field_results = self._execute_query(field_query, inverted_index, all_docs)
            
            for doc, score in field_results:
                all_scores[doc.id] = max(all_scores[doc.id], score)
        
        # Build results
        doc_map = {doc.id: doc for doc in all_docs}
        return [(doc_map[doc_id], score) for doc_id, score in all_scores.items()]
    
    def _extract_query_string(self, query: Dict[str, Any]) -> str:
        """Extract human-readable query string"""
        query_type = list(query.keys())[0]
        params = query[query_type]
        
        if query_type == "match":
            field = list(params.keys())[0]
            value = params[field]['query'] if isinstance(params[field], dict) else params[field]
            return f"{field}:{value}"
        elif query_type == "term":
            field = list(params.keys())[0]
            return f"{field}={params[field]}"
        else:
            return json.dumps(query)
    
    def suggest(self, prefix: str, max_results: int = 10) -> List[str]:
        """Get autocomplete suggestions"""
        suggestions = self.autocomplete.suggest(prefix, max_results)
        return [phrase for phrase, _ in suggestions]
    
    def delete_document(self, index_name: str, doc_id: str) -> bool:
        """Delete a document"""
        session = self.Session()
        try:
            # Delete from database
            doc = session.query(Document).filter_by(
                index_name=index_name,
                id=doc_id
            ).first()
            
            if not doc:
                return False
            
            session.delete(doc)
            session.commit()
            
            # Remove from inverted index
            inverted_index = self.index_manager.load_index(index_name)
            if inverted_index:
                inverted_index.remove_document(doc_id)
                self.index_manager.save_index(index_name)
            
            return True
            
        finally:
            session.close()


# Example usage
def example_usage():
    """Demonstrate search engine usage"""
    
    # Initialize search engine
    engine = SearchEngine(
        db_uri="sqlite:///search.db",
        storage_path="./indexes"
    )
    
    # Create index
    settings = IndexSettings(number_of_shards=1)
    mappings = {
        'title': FieldMapping(type=FieldType.TEXT),
        'description': FieldMapping(type=FieldType.TEXT),
        'category': FieldMapping(type=FieldType.KEYWORD),
        'price': FieldMapping(type=FieldType.FLOAT)
    }
    
    engine.create_index("products", settings, mappings)
    
    # Index documents
    documents = [
        ("1", {"title": "Organic Fertilizer", "description": "Natural NPK fertilizer", "category": "fertilizer", "price": 25.99}),
        ("2", {"title": "Pesticide Spray", "description": "Organic pest control", "category": "pesticide", "price": 15.50}),
        ("3", {"title": "Soil Tester", "description": "Digital pH meter", "category": "equipment", "price": 45.00})
    ]
    
    engine.bulk_index("products", documents)
    
    # Search
    query = QueryBuilder().match("description", "organic").build()
    results = engine.search("products", query, size=10)
    
    print(f"Found {results.total} results in {results.took_ms:.2f}ms")
    for hit in results.hits:
        print(f"- {hit['_source']['title']} (score: {hit['_score']:.2f})")
    
    # Faceted search
    query_with_aggs = {
        "match_all": {},
        "aggs": {
            "categories": {
                "terms": {"field": "category", "size": 10}
            },
            "price_stats": {
                "stats": {"field": "price"}
            }
        }
    }
    
    results = engine.search("products", {"match_all": {}}, 
                          aggregations=query_with_aggs.get("aggs"))
    
    print(f"\nAggregations:")
    print(f"Categories: {results.aggregations.get('categories', {})}")
    print(f"Price stats: {results.aggregations.get('price_stats', {})}")
    
    # Autocomplete
    suggestions = engine.suggest("org", max_results=5)
    print(f"\nAutocomplete suggestions for 'org': {suggestions}")
    
    logger.info("Example complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()

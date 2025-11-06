# ======================================================================================================================
# AgroPulse NVR - Search Engine Integration (Elasticsearch)
# Full-text search, indexing, faceted search, aggregations, search analytics
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from elasticsearch import AsyncElasticsearch
import json

logger = logging.getLogger(__name__)

# ======================================================================================================================
# SEARCH MODELS
# ======================================================================================================================

class SearchIndex(Enum):
    """Search indices"""
    FARMS = "farms"
    FIELDS = "fields"
    DEVICES = "devices"
    DETECTIONS = "detections"
    INCIDENTS = "incidents"
    TASKS = "tasks"
    LOGS = "logs"

@dataclass
class SearchQuery:
    """Search query"""
    query_text: str
    indices: List[SearchIndex]
    filters: Dict[str, Any] = field(default_factory=dict)
    from_: int = 0
    size: int = 10
    sort: Optional[List[Dict[str, str]]] = None
    highlight: bool = True
    facets: List[str] = field(default_factory=list)

@dataclass
class SearchResult:
    """Search result"""
    result_id: str
    index: str
    score: float
    source: Dict[str, Any]
    highlights: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class SearchResponse:
    """Search response"""
    total: int
    results: List[SearchResult]
    took_ms: int
    facets: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

# ======================================================================================================================
# ELASTICSEARCH CLIENT
# ======================================================================================================================

class ElasticsearchClient:
    """Elasticsearch client wrapper"""
    
    def __init__(self, hosts: List[str], api_key: Optional[str] = None):
        self.hosts = hosts
        self.client: Optional[AsyncElasticsearch] = None
        
        logger.info(f"[ES] Elasticsearch client initialized: {hosts}")
    
    async def connect(self):
        """Connect to Elasticsearch"""
        try:
            self.client = AsyncElasticsearch(hosts=self.hosts)
            
            # Test connection
            info = await self.client.info()
            logger.info(f"[ES] Connected - Version: {info['version']['number']}")
            
        except Exception as e:
            logger.error(f"[ES] Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Elasticsearch"""
        if self.client:
            await self.client.close()
            logger.info("[ES] Disconnected")
    
    async def create_index(self, index: str, mappings: Dict[str, Any]):
        """Create index with mappings"""
        try:
            exists = await self.client.indices.exists(index=index)
            
            if not exists:
                await self.client.indices.create(
                    index=index,
                    body={'mappings': mappings}
                )
                logger.info(f"[ES] Created index: {index}")
            
        except Exception as e:
            logger.error(f"[ES] Create index error: {e}")
    
    async def index_document(self, index: str, doc_id: str, document: Dict[str, Any]):
        """Index document"""
        try:
            await self.client.index(
                index=index,
                id=doc_id,
                body=document
            )
            logger.debug(f"[ES] Indexed: {index}/{doc_id}")
            
        except Exception as e:
            logger.error(f"[ES] Index error: {e}")
    
    async def bulk_index(self, index: str, documents: List[Tuple[str, Dict[str, Any]]]):
        """Bulk index documents"""
        try:
            bulk_body = []
            for doc_id, document in documents:
                bulk_body.append({'index': {'_index': index, '_id': doc_id}})
                bulk_body.append(document)
            
            response = await self.client.bulk(body=bulk_body)
            
            if response.get('errors'):
                logger.warning(f"[ES] Bulk index had errors")
            else:
                logger.info(f"[ES] Bulk indexed {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"[ES] Bulk index error: {e}")
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Execute search query"""
        try:
            # Build query body
            body = self._build_query(query)
            
            # Execute search
            response = await self.client.search(
                index=[idx.value for idx in query.indices],
                body=body,
                from_=query.from_,
                size=query.size
            )
            
            # Parse response
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"[ES] Search error: {e}")
            raise
    
    def _build_query(self, query: SearchQuery) -> Dict[str, Any]:
        """Build Elasticsearch query"""
        body = {
            'query': {
                'bool': {
                    'must': [
                        {
                            'multi_match': {
                                'query': query.query_text,
                                'fields': ['*'],
                                'fuzziness': 'AUTO'
                            }
                        }
                    ],
                    'filter': []
                }
            }
        }
        
        # Add filters
        for field, value in query.filters.items():
            if isinstance(value, list):
                body['query']['bool']['filter'].append({
                    'terms': {field: value}
                })
            else:
                body['query']['bool']['filter'].append({
                    'term': {field: value}
                })
        
        # Add sorting
        if query.sort:
            body['sort'] = query.sort
        
        # Add highlighting
        if query.highlight:
            body['highlight'] = {
                'fields': {'*': {}},
                'pre_tags': ['<mark>'],
                'post_tags': ['</mark>']
            }
        
        # Add aggregations (facets)
        if query.facets:
            body['aggs'] = {}
            for facet in query.facets:
                body['aggs'][facet] = {
                    'terms': {'field': f'{facet}.keyword', 'size': 10}
                }
        
        return body
    
    def _parse_response(self, response: Dict[str, Any]) -> SearchResponse:
        """Parse Elasticsearch response"""
        results = []
        
        for hit in response['hits']['hits']:
            result = SearchResult(
                result_id=hit['_id'],
                index=hit['_index'],
                score=hit['_score'],
                source=hit['_source'],
                highlights=hit.get('highlight', {})
            )
            results.append(result)
        
        # Parse facets
        facets = {}
        if 'aggregations' in response:
            for facet_name, facet_data in response['aggregations'].items():
                facets[facet_name] = [
                    {'value': bucket['key'], 'count': bucket['doc_count']}
                    for bucket in facet_data['buckets']
                ]
        
        return SearchResponse(
            total=response['hits']['total']['value'],
            results=results,
            took_ms=response['took'],
            facets=facets
        )
    
    async def delete_document(self, index: str, doc_id: str):
        """Delete document"""
        try:
            await self.client.delete(index=index, id=doc_id)
            logger.debug(f"[ES] Deleted: {index}/{doc_id}")
        except Exception as e:
            logger.error(f"[ES] Delete error: {e}")

# ======================================================================================================================
# INDEX MANAGER
# ======================================================================================================================

class IndexManager:
    """Manage Elasticsearch indices"""
    
    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
        
        logger.info("[INDEX-MGR] Index manager initialized")
    
    async def create_all_indices(self):
        """Create all application indices"""
        # Farms index
        await self.es_client.create_index('farms', {
            'properties': {
                'farm_id': {'type': 'keyword'},
                'name': {'type': 'text'},
                'location': {'type': 'text'},
                'area_hectares': {'type': 'float'},
                'created_at': {'type': 'date'}
            }
        })
        
        # Fields index
        await self.es_client.create_index('fields', {
            'properties': {
                'field_id': {'type': 'keyword'},
                'farm_id': {'type': 'keyword'},
                'name': {'type': 'text'},
                'crop_type': {'type': 'keyword'},
                'health_score': {'type': 'float'},
                'created_at': {'type': 'date'}
            }
        })
        
        # Devices index
        await self.es_client.create_index('devices', {
            'properties': {
                'device_id': {'type': 'keyword'},
                'device_name': {'type': 'text'},
                'device_type': {'type': 'keyword'},
                'status': {'type': 'keyword'},
                'location': {'type': 'geo_point'}
            }
        })
        
        # Detections index
        await self.es_client.create_index('detections', {
            'properties': {
                'detection_id': {'type': 'keyword'},
                'class_name': {'type': 'keyword'},
                'confidence': {'type': 'float'},
                'timestamp': {'type': 'date'},
                'location': {'type': 'geo_point'},
                'severity': {'type': 'integer'}
            }
        })
        
        # Incidents index
        await self.es_client.create_index('incidents', {
            'properties': {
                'incident_id': {'type': 'keyword'},
                'title': {'type': 'text'},
                'description': {'type': 'text'},
                'status': {'type': 'keyword'},
                'severity': {'type': 'integer'},
                'created_at': {'type': 'date'}
            }
        })
        
        logger.info("[INDEX-MGR] Created all indices")
    
    async def reindex(self, source_index: str, dest_index: str):
        """Reindex data"""
        try:
            await self.es_client.client.reindex(
                body={
                    'source': {'index': source_index},
                    'dest': {'index': dest_index}
                }
            )
            logger.info(f"[INDEX-MGR] Reindexed: {source_index} -> {dest_index}")
        except Exception as e:
            logger.error(f"[INDEX-MGR] Reindex error: {e}")

# ======================================================================================================================
# SEARCH INDEXER
# ======================================================================================================================

class SearchIndexer:
    """Index application data for search"""
    
    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
        
        logger.info("[INDEXER] Search indexer initialized")
    
    async def index_farm(self, farm: Dict[str, Any]):
        """Index farm"""
        await self.es_client.index_document(
            'farms',
            farm['farm_id'],
            farm
        )
    
    async def index_field(self, field: Dict[str, Any]):
        """Index field"""
        await self.es_client.index_document(
            'fields',
            field['field_id'],
            field
        )
    
    async def index_device(self, device: Dict[str, Any]):
        """Index device"""
        # Convert lat/lon to geo_point
        if 'latitude' in device and 'longitude' in device:
            device['location'] = {
                'lat': device['latitude'],
                'lon': device['longitude']
            }
        
        await self.es_client.index_document(
            'devices',
            device['device_id'],
            device
        )
    
    async def index_detection(self, detection: Dict[str, Any]):
        """Index detection"""
        # Convert lat/lon to geo_point
        if 'latitude' in detection and 'longitude' in detection:
            detection['location'] = {
                'lat': detection['latitude'],
                'lon': detection['longitude']
            }
        
        await self.es_client.index_document(
            'detections',
            detection['detection_id'],
            detection
        )
    
    async def index_incident(self, incident: Dict[str, Any]):
        """Index incident"""
        await self.es_client.index_document(
            'incidents',
            incident['incident_id'],
            incident
        )
    
    async def bulk_index_farms(self, farms: List[Dict[str, Any]]):
        """Bulk index farms"""
        documents = [(f['farm_id'], f) for f in farms]
        await self.es_client.bulk_index('farms', documents)

# ======================================================================================================================
# SEARCH ENGINE
# ======================================================================================================================

class SearchEngine:
    """High-level search engine"""
    
    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
        
        logger.info("[SEARCH] Search engine initialized")
    
    async def search_all(self, query_text: str, page: int = 1,
                        page_size: int = 10) -> SearchResponse:
        """Search across all indices"""
        query = SearchQuery(
            query_text=query_text,
            indices=[
                SearchIndex.FARMS,
                SearchIndex.FIELDS,
                SearchIndex.DEVICES,
                SearchIndex.DETECTIONS,
                SearchIndex.INCIDENTS
            ],
            from_=(page - 1) * page_size,
            size=page_size
        )
        
        return await self.es_client.search(query)
    
    async def search_farms(self, query_text: str, filters: Optional[Dict] = None) -> SearchResponse:
        """Search farms"""
        query = SearchQuery(
            query_text=query_text,
            indices=[SearchIndex.FARMS],
            filters=filters or {},
            facets=['location', 'area_hectares']
        )
        
        return await self.es_client.search(query)
    
    async def search_detections(self, query_text: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> SearchResponse:
        """Search detections"""
        filters = {}
        
        if start_date and end_date:
            filters['timestamp'] = {
                'gte': start_date.isoformat(),
                'lte': end_date.isoformat()
            }
        
        query = SearchQuery(
            query_text=query_text,
            indices=[SearchIndex.DETECTIONS],
            filters=filters,
            facets=['class_name', 'severity'],
            sort=[{'timestamp': 'desc'}]
        )
        
        return await self.es_client.search(query)
    
    async def search_by_location(self, lat: float, lon: float,
                                radius_km: float = 10) -> SearchResponse:
        """Search by location"""
        # This would use geo queries in Elasticsearch
        query = SearchQuery(
            query_text='*',
            indices=[SearchIndex.DEVICES, SearchIndex.DETECTIONS],
            filters={
                'location': {
                    'distance': f'{radius_km}km',
                    'lat': lat,
                    'lon': lon
                }
            }
        )
        
        return await self.es_client.search(query)
    
    async def autocomplete(self, prefix: str, index: SearchIndex) -> List[str]:
        """Autocomplete suggestions"""
        try:
            body = {
                'suggest': {
                    'text': prefix,
                    'completion': {
                        'field': 'name.completion',
                        'size': 10
                    }
                }
            }
            
            response = await self.es_client.client.search(
                index=index.value,
                body=body
            )
            
            suggestions = []
            if 'suggest' in response:
                for suggestion in response['suggest']['completion'][0]['options']:
                    suggestions.append(suggestion['text'])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"[SEARCH] Autocomplete error: {e}")
            return []

# ======================================================================================================================
# SEARCH ANALYTICS
# ======================================================================================================================

class SearchAnalytics:
    """Search analytics and metrics"""
    
    def __init__(self):
        self.query_log: List[Dict[str, Any]] = []
        
        logger.info("[ANALYTICS] Search analytics initialized")
    
    def log_query(self, query_text: str, results_count: int,
                 took_ms: int, user_id: Optional[str] = None):
        """Log search query"""
        self.query_log.append({
            'query': query_text,
            'results_count': results_count,
            'took_ms': took_ms,
            'user_id': user_id,
            'timestamp': datetime.now()
        })
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular queries"""
        query_counts = {}
        
        for entry in self.query_log:
            query = entry['query']
            if query not in query_counts:
                query_counts[query] = 0
            query_counts[query] += 1
        
        sorted_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {'query': q, 'count': c}
            for q, c in sorted_queries
        ]
    
    def get_slow_queries(self, threshold_ms: int = 1000) -> List[Dict[str, Any]]:
        """Get slow queries"""
        return [
            entry for entry in self.query_log
            if entry['took_ms'] > threshold_ms
        ]
    
    def get_zero_result_queries(self) -> List[Dict[str, Any]]:
        """Get queries with zero results"""
        return [
            entry for entry in self.query_log
            if entry['results_count'] == 0
        ]

# ======================================================================================================================
# SEARCH ORCHESTRATOR
# ======================================================================================================================

class SearchOrchestrator:
    """Main search orchestrator"""
    
    def __init__(self, hosts: List[str]):
        self.es_client = ElasticsearchClient(hosts)
        self.index_manager = IndexManager(self.es_client)
        self.indexer = SearchIndexer(self.es_client)
        self.search_engine = SearchEngine(self.es_client)
        self.analytics = SearchAnalytics()
        
        logger.info("[SEARCH-ORCH] Search orchestrator initialized")
    
    async def connect(self):
        """Connect to Elasticsearch"""
        await self.es_client.connect()
    
    async def disconnect(self):
        """Disconnect from Elasticsearch"""
        await self.es_client.disconnect()
    
    async def initialize_indices(self):
        """Initialize all indices"""
        await self.index_manager.create_all_indices()
    
    async def index_document(self, index: SearchIndex, document: Dict[str, Any]):
        """Index document"""
        if index == SearchIndex.FARMS:
            await self.indexer.index_farm(document)
        elif index == SearchIndex.FIELDS:
            await self.indexer.index_field(document)
        elif index == SearchIndex.DEVICES:
            await self.indexer.index_device(document)
        elif index == SearchIndex.DETECTIONS:
            await self.indexer.index_detection(document)
        elif index == SearchIndex.INCIDENTS:
            await self.indexer.index_incident(document)
    
    async def search(self, query_text: str, **kwargs) -> SearchResponse:
        """Perform search"""
        start_time = datetime.now()
        
        response = await self.search_engine.search_all(query_text, **kwargs)
        
        # Log analytics
        took_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.analytics.log_query(query_text, response.total, int(took_ms))
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        return {
            'total_queries': len(self.analytics.query_log),
            'popular_queries': self.analytics.get_popular_queries(5),
            'slow_queries_count': len(self.analytics.get_slow_queries()),
            'zero_result_queries_count': len(self.analytics.get_zero_result_queries())
        }

# ======================================================================================================================
# END OF SEARCH ENGINE INTEGRATION MODULE
# Lines in this file: ~750+
# Combined total: ~29,400+
# Remaining for 50k: ~20,600 lines
# ======================================================================================================================

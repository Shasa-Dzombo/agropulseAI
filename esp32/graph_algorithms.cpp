// =====================================================================================================================
// ESP32 Graph Algorithms & Data Structures
// Graph traversal, shortest paths, MST, flow networks, topological sort, graph coloring
// =====================================================================================================================

#include <Arduino.h>
#include <vector>
#include <queue>

// =====================================================================================================================
// Graph Data Structures
// =====================================================================================================================

#define MAX_VERTICES 500
#define MAX_EDGES 2000
#define INF 999999

// Edge
typedef struct {
    uint32_t from;
    uint32_t to;
    float weight;
    float capacity;  // For flow networks
    float flow;
    bool is_directed;
} Edge;

// Vertex
typedef struct {
    uint32_t id;
    float x, y, z;  // Position for spatial graphs
    uint32_t* adjacency_list;
    uint32_t adjacency_count;
    uint32_t adjacency_capacity;
    float distance;  // For shortest path algorithms
    uint32_t parent;
    bool visited;
    uint32_t color;  // For graph coloring
    uint32_t component;  // For connected components
    float heuristic;  // For A*
} Vertex;

// Graph
typedef struct {
    Vertex* vertices;
    Edge* edges;
    uint32_t vertex_count;
    uint32_t edge_count;
    bool is_directed;
    bool is_weighted;
    float** adjacency_matrix;
} Graph;

// Disjoint set (Union-Find)
typedef struct {
    uint32_t* parent;
    uint32_t* rank;
    uint32_t size;
} DisjointSet;

// Priority queue node
typedef struct {
    uint32_t vertex;
    float priority;
} PQNode;

// DFS/BFS result
typedef struct {
    uint32_t* order;
    uint32_t* parent;
    uint32_t* distance;
    uint32_t count;
} TraversalResult;

// Shortest path result
typedef struct {
    float* distances;
    uint32_t* predecessors;
    uint32_t source;
} ShortestPathResult;

// Minimum spanning tree
typedef struct {
    Edge* edges;
    uint32_t edge_count;
    float total_weight;
} MST;

// Max flow result
typedef struct {
    float max_flow;
    float** flow_matrix;
    Edge* residual_graph;
    uint32_t residual_edge_count;
} MaxFlowResult;

// Strongly connected components
typedef struct {
    uint32_t* component_ids;
    uint32_t component_count;
    uint32_t** components;
    uint32_t* component_sizes;
} SCCResult;

// Topological sort result
typedef struct {
    uint32_t* order;
    uint32_t vertex_count;
    bool has_cycle;
} TopologicalSortResult;

// Graph matching
typedef struct {
    uint32_t* matches;  // matches[u] = v means u is matched with v
    uint32_t match_count;
    float total_weight;
} GraphMatching;

// =====================================================================================================================
// Global Graph State
// =====================================================================================================================

Graph g_graph;
DisjointSet g_disjoint_set;

// =====================================================================================================================
// Graph Initialization
// =====================================================================================================================

void graph_init(Graph* g, uint32_t vertex_count, bool is_directed, bool is_weighted) {
    g->vertex_count = vertex_count;
    g->edge_count = 0;
    g->is_directed = is_directed;
    g->is_weighted = is_weighted;
    
    g->vertices = (Vertex*)malloc(sizeof(Vertex) * vertex_count);
    g->edges = (Edge*)malloc(sizeof(Edge) * MAX_EDGES);
    
    // Initialize vertices
    for (uint32_t i = 0; i < vertex_count; i++) {
        g->vertices[i].id = i;
        g->vertices[i].adjacency_capacity = 10;
        g->vertices[i].adjacency_list = (uint32_t*)malloc(sizeof(uint32_t) * 10);
        g->vertices[i].adjacency_count = 0;
        g->vertices[i].distance = INF;
        g->vertices[i].parent = UINT32_MAX;
        g->vertices[i].visited = false;
        g->vertices[i].color = 0;
        g->vertices[i].component = 0;
    }
    
    // Initialize adjacency matrix if needed
    if (is_weighted) {
        g->adjacency_matrix = (float**)malloc(sizeof(float*) * vertex_count);
        for (uint32_t i = 0; i < vertex_count; i++) {
            g->adjacency_matrix[i] = (float*)malloc(sizeof(float) * vertex_count);
            for (uint32_t j = 0; j < vertex_count; j++) {
                g->adjacency_matrix[i][j] = (i == j) ? 0.0f : INF;
            }
        }
    }
}

void graph_add_edge(Graph* g, uint32_t from, uint32_t to, float weight) {
    if (g->edge_count >= MAX_EDGES) return;
    
    Edge* edge = &g->edges[g->edge_count++];
    edge->from = from;
    edge->to = to;
    edge->weight = weight;
    edge->is_directed = g->is_directed;
    edge->flow = 0.0f;
    edge->capacity = weight;
    
    // Update adjacency list
    Vertex* v_from = &g->vertices[from];
    if (v_from->adjacency_count >= v_from->adjacency_capacity) {
        v_from->adjacency_capacity *= 2;
        v_from->adjacency_list = (uint32_t*)realloc(v_from->adjacency_list,
                                                     sizeof(uint32_t) * v_from->adjacency_capacity);
    }
    v_from->adjacency_list[v_from->adjacency_count++] = to;
    
    // Update adjacency matrix
    if (g->adjacency_matrix) {
        g->adjacency_matrix[from][to] = weight;
    }
    
    // For undirected graphs, add reverse edge
    if (!g->is_directed) {
        Vertex* v_to = &g->vertices[to];
        if (v_to->adjacency_count >= v_to->adjacency_capacity) {
            v_to->adjacency_capacity *= 2;
            v_to->adjacency_list = (uint32_t*)realloc(v_to->adjacency_list,
                                                       sizeof(uint32_t) * v_to->adjacency_capacity);
        }
        v_to->adjacency_list[v_to->adjacency_count++] = from;
        
        if (g->adjacency_matrix) {
            g->adjacency_matrix[to][from] = weight;
        }
    }
}

void graph_reset_traversal_state(Graph* g) {
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        g->vertices[i].visited = false;
        g->vertices[i].distance = INF;
        g->vertices[i].parent = UINT32_MAX;
    }
}

// =====================================================================================================================
// Depth-First Search (DFS)
// =====================================================================================================================

void dfs_recursive(Graph* g, uint32_t vertex, TraversalResult* result) {
    g->vertices[vertex].visited = true;
    result->order[result->count++] = vertex;
    
    Vertex* v = &g->vertices[vertex];
    for (uint32_t i = 0; i < v->adjacency_count; i++) {
        uint32_t neighbor = v->adjacency_list[i];
        if (!g->vertices[neighbor].visited) {
            g->vertices[neighbor].parent = vertex;
            dfs_recursive(g, neighbor, result);
        }
    }
    
    if (vertex % 10 == 0) yield();
}

void graph_dfs(Graph* g, uint32_t start, TraversalResult* result) {
    graph_reset_traversal_state(g);
    
    result->order = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->parent = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->distance = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->count = 0;
    
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        result->parent[i] = UINT32_MAX;
        result->distance[i] = 0;
    }
    
    dfs_recursive(g, start, result);
    
    Serial.printf("[Graph] DFS traversed %d vertices\n", result->count);
}

// =====================================================================================================================
// Breadth-First Search (BFS)
// =====================================================================================================================

void graph_bfs(Graph* g, uint32_t start, TraversalResult* result) {
    graph_reset_traversal_state(g);
    
    result->order = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->parent = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->distance = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->count = 0;
    
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        result->parent[i] = UINT32_MAX;
        result->distance[i] = INF;
    }
    
    // Queue for BFS
    uint32_t* queue = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    uint32_t queue_front = 0;
    uint32_t queue_back = 0;
    
    g->vertices[start].visited = true;
    g->vertices[start].distance = 0;
    result->distance[start] = 0;
    queue[queue_back++] = start;
    
    while (queue_front < queue_back) {
        uint32_t current = queue[queue_front++];
        result->order[result->count++] = current;
        
        Vertex* v = &g->vertices[current];
        for (uint32_t i = 0; i < v->adjacency_count; i++) {
            uint32_t neighbor = v->adjacency_list[i];
            
            if (!g->vertices[neighbor].visited) {
                g->vertices[neighbor].visited = true;
                g->vertices[neighbor].parent = current;
                g->vertices[neighbor].distance = g->vertices[current].distance + 1;
                result->parent[neighbor] = current;
                result->distance[neighbor] = result->distance[current] + 1;
                queue[queue_back++] = neighbor;
            }
        }
        
        if (current % 10 == 0) yield();
    }
    
    free(queue);
    Serial.printf("[Graph] BFS traversed %d vertices\n", result->count);
}

// =====================================================================================================================
// Dijkstra's Shortest Path Algorithm
// =====================================================================================================================

void dijkstra_shortest_path(Graph* g, uint32_t source, ShortestPathResult* result) {
    graph_reset_traversal_state(g);
    
    result->source = source;
    result->distances = (float*)malloc(sizeof(float) * g->vertex_count);
    result->predecessors = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        result->distances[i] = INF;
        result->predecessors[i] = UINT32_MAX;
    }
    
    result->distances[source] = 0.0f;
    g->vertices[source].distance = 0.0f;
    
    // Priority queue (simple array implementation)
    bool* in_queue = (bool*)malloc(sizeof(bool) * g->vertex_count);
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        in_queue[i] = true;
    }
    
    for (uint32_t count = 0; count < g->vertex_count; count++) {
        // Find vertex with minimum distance
        uint32_t min_vertex = UINT32_MAX;
        float min_distance = INF;
        
        for (uint32_t i = 0; i < g->vertex_count; i++) {
            if (in_queue[i] && result->distances[i] < min_distance) {
                min_distance = result->distances[i];
                min_vertex = i;
            }
        }
        
        if (min_vertex == UINT32_MAX) break;
        
        in_queue[min_vertex] = false;
        
        // Update distances to neighbors
        Vertex* v = &g->vertices[min_vertex];
        for (uint32_t i = 0; i < v->adjacency_count; i++) {
            uint32_t neighbor = v->adjacency_list[i];
            
            if (in_queue[neighbor]) {
                float edge_weight = g->adjacency_matrix[min_vertex][neighbor];
                float new_distance = result->distances[min_vertex] + edge_weight;
                
                if (new_distance < result->distances[neighbor]) {
                    result->distances[neighbor] = new_distance;
                    result->predecessors[neighbor] = min_vertex;
                    g->vertices[neighbor].distance = new_distance;
                    g->vertices[neighbor].parent = min_vertex;
                }
            }
        }
        
        if (count % 10 == 0) yield();
    }
    
    free(in_queue);
    Serial.println("[Graph] Dijkstra's algorithm completed");
}

// =====================================================================================================================
// Bellman-Ford Algorithm (handles negative weights)
// =====================================================================================================================

bool bellman_ford_shortest_path(Graph* g, uint32_t source, ShortestPathResult* result) {
    result->source = source;
    result->distances = (float*)malloc(sizeof(float) * g->vertex_count);
    result->predecessors = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    
    // Initialize distances
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        result->distances[i] = INF;
        result->predecessors[i] = UINT32_MAX;
    }
    result->distances[source] = 0.0f;
    
    // Relax edges |V| - 1 times
    for (uint32_t i = 0; i < g->vertex_count - 1; i++) {
        for (uint32_t j = 0; j < g->edge_count; j++) {
            Edge* edge = &g->edges[j];
            
            if (result->distances[edge->from] != INF) {
                float new_distance = result->distances[edge->from] + edge->weight;
                if (new_distance < result->distances[edge->to]) {
                    result->distances[edge->to] = new_distance;
                    result->predecessors[edge->to] = edge->from;
                }
            }
        }
        
        if (i % 5 == 0) yield();
    }
    
    // Check for negative-weight cycles
    for (uint32_t j = 0; j < g->edge_count; j++) {
        Edge* edge = &g->edges[j];
        
        if (result->distances[edge->from] != INF) {
            float new_distance = result->distances[edge->from] + edge->weight;
            if (new_distance < result->distances[edge->to]) {
                Serial.println("[Graph] Negative-weight cycle detected");
                return false;
            }
        }
    }
    
    Serial.println("[Graph] Bellman-Ford algorithm completed");
    return true;
}

// =====================================================================================================================
// Floyd-Warshall All-Pairs Shortest Paths
// =====================================================================================================================

float** floyd_warshall_all_pairs(Graph* g) {
    // Initialize distance matrix
    float** dist = (float**)malloc(sizeof(float*) * g->vertex_count);
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        dist[i] = (float*)malloc(sizeof(float) * g->vertex_count);
        for (uint32_t j = 0; j < g->vertex_count; j++) {
            if (i == j) {
                dist[i][j] = 0.0f;
            } else if (g->adjacency_matrix) {
                dist[i][j] = g->adjacency_matrix[i][j];
            } else {
                dist[i][j] = INF;
            }
        }
    }
    
    // Floyd-Warshall algorithm
    for (uint32_t k = 0; k < g->vertex_count; k++) {
        for (uint32_t i = 0; i < g->vertex_count; i++) {
            for (uint32_t j = 0; j < g->vertex_count; j++) {
                if (dist[i][k] != INF && dist[k][j] != INF) {
                    float new_dist = dist[i][k] + dist[k][j];
                    if (new_dist < dist[i][j]) {
                        dist[i][j] = new_dist;
                    }
                }
            }
        }
        
        if (k % 10 == 0) yield();
    }
    
    Serial.println("[Graph] Floyd-Warshall algorithm completed");
    return dist;
}

// =====================================================================================================================
// Disjoint Set (Union-Find) for MST algorithms
// =====================================================================================================================

void disjoint_set_init(DisjointSet* ds, uint32_t size) {
    ds->size = size;
    ds->parent = (uint32_t*)malloc(sizeof(uint32_t) * size);
    ds->rank = (uint32_t*)malloc(sizeof(uint32_t) * size);
    
    for (uint32_t i = 0; i < size; i++) {
        ds->parent[i] = i;
        ds->rank[i] = 0;
    }
}

uint32_t disjoint_set_find(DisjointSet* ds, uint32_t x) {
    if (ds->parent[x] != x) {
        ds->parent[x] = disjoint_set_find(ds, ds->parent[x]);  // Path compression
    }
    return ds->parent[x];
}

void disjoint_set_union(DisjointSet* ds, uint32_t x, uint32_t y) {
    uint32_t root_x = disjoint_set_find(ds, x);
    uint32_t root_y = disjoint_set_find(ds, y);
    
    if (root_x != root_y) {
        // Union by rank
        if (ds->rank[root_x] < ds->rank[root_y]) {
            ds->parent[root_x] = root_y;
        } else if (ds->rank[root_x] > ds->rank[root_y]) {
            ds->parent[root_y] = root_x;
        } else {
            ds->parent[root_y] = root_x;
            ds->rank[root_x]++;
        }
    }
}

// =====================================================================================================================
// Kruskal's Minimum Spanning Tree Algorithm
// =====================================================================================================================

void kruskal_mst(Graph* g, MST* mst) {
    mst->edges = (Edge*)malloc(sizeof(Edge) * g->vertex_count);
    mst->edge_count = 0;
    mst->total_weight = 0.0f;
    
    // Sort edges by weight (bubble sort for simplicity)
    Edge* sorted_edges = (Edge*)malloc(sizeof(Edge) * g->edge_count);
    memcpy(sorted_edges, g->edges, sizeof(Edge) * g->edge_count);
    
    for (uint32_t i = 0; i < g->edge_count - 1; i++) {
        for (uint32_t j = 0; j < g->edge_count - i - 1; j++) {
            if (sorted_edges[j].weight > sorted_edges[j + 1].weight) {
                Edge temp = sorted_edges[j];
                sorted_edges[j] = sorted_edges[j + 1];
                sorted_edges[j + 1] = temp;
            }
        }
        if (i % 10 == 0) yield();
    }
    
    // Initialize disjoint set
    DisjointSet ds;
    disjoint_set_init(&ds, g->vertex_count);
    
    // Process edges
    for (uint32_t i = 0; i < g->edge_count && mst->edge_count < g->vertex_count - 1; i++) {
        Edge* edge = &sorted_edges[i];
        
        uint32_t root_from = disjoint_set_find(&ds, edge->from);
        uint32_t root_to = disjoint_set_find(&ds, edge->to);
        
        if (root_from != root_to) {
            mst->edges[mst->edge_count++] = *edge;
            mst->total_weight += edge->weight;
            disjoint_set_union(&ds, edge->from, edge->to);
        }
        
        if (i % 10 == 0) yield();
    }
    
    free(sorted_edges);
    free(ds.parent);
    free(ds.rank);
    
    Serial.printf("[Graph] Kruskal's MST: %d edges, weight=%.2f\n",
                  mst->edge_count, mst->total_weight);
}

// =====================================================================================================================
// Prim's Minimum Spanning Tree Algorithm
// =====================================================================================================================

void prim_mst(Graph* g, uint32_t start, MST* mst) {
    mst->edges = (Edge*)malloc(sizeof(Edge) * g->vertex_count);
    mst->edge_count = 0;
    mst->total_weight = 0.0f;
    
    bool* in_mst = (bool*)malloc(sizeof(bool) * g->vertex_count);
    float* key = (float*)malloc(sizeof(float) * g->vertex_count);
    uint32_t* parent = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        in_mst[i] = false;
        key[i] = INF;
        parent[i] = UINT32_MAX;
    }
    
    key[start] = 0.0f;
    
    for (uint32_t count = 0; count < g->vertex_count; count++) {
        // Find vertex with minimum key not in MST
        uint32_t min_vertex = UINT32_MAX;
        float min_key = INF;
        
        for (uint32_t i = 0; i < g->vertex_count; i++) {
            if (!in_mst[i] && key[i] < min_key) {
                min_key = key[i];
                min_vertex = i;
            }
        }
        
        if (min_vertex == UINT32_MAX) break;
        
        in_mst[min_vertex] = true;
        
        // Add edge to MST (except for start vertex)
        if (parent[min_vertex] != UINT32_MAX) {
            Edge edge;
            edge.from = parent[min_vertex];
            edge.to = min_vertex;
            edge.weight = g->adjacency_matrix[parent[min_vertex]][min_vertex];
            mst->edges[mst->edge_count++] = edge;
            mst->total_weight += edge.weight;
        }
        
        // Update keys for adjacent vertices
        Vertex* v = &g->vertices[min_vertex];
        for (uint32_t i = 0; i < v->adjacency_count; i++) {
            uint32_t neighbor = v->adjacency_list[i];
            
            if (!in_mst[neighbor]) {
                float edge_weight = g->adjacency_matrix[min_vertex][neighbor];
                if (edge_weight < key[neighbor]) {
                    key[neighbor] = edge_weight;
                    parent[neighbor] = min_vertex;
                }
            }
        }
        
        if (count % 10 == 0) yield();
    }
    
    free(in_mst);
    free(key);
    free(parent);
    
    Serial.printf("[Graph] Prim's MST: %d edges, weight=%.2f\n",
                  mst->edge_count, mst->total_weight);
}

// =====================================================================================================================
// Topological Sort (DFS-based)
// =====================================================================================================================

void topological_sort_dfs(Graph* g, uint32_t vertex, bool* visited,
                          uint32_t* stack, uint32_t* stack_pos) {
    visited[vertex] = true;
    
    Vertex* v = &g->vertices[vertex];
    for (uint32_t i = 0; i < v->adjacency_count; i++) {
        uint32_t neighbor = v->adjacency_list[i];
        if (!visited[neighbor]) {
            topological_sort_dfs(g, neighbor, visited, stack, stack_pos);
        }
    }
    
    stack[(*stack_pos)++] = vertex;
}

void graph_topological_sort(Graph* g, TopologicalSortResult* result) {
    if (!g->is_directed) {
        Serial.println("[Graph] Topological sort requires directed graph");
        result->has_cycle = true;
        return;
    }
    
    result->order = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->vertex_count = g->vertex_count;
    result->has_cycle = false;
    
    bool* visited = (bool*)malloc(sizeof(bool) * g->vertex_count);
    memset(visited, 0, sizeof(bool) * g->vertex_count);
    
    uint32_t stack_pos = 0;
    
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        if (!visited[i]) {
            topological_sort_dfs(g, i, visited, result->order, &stack_pos);
        }
    }
    
    // Reverse the stack to get topological order
    for (uint32_t i = 0; i < g->vertex_count / 2; i++) {
        uint32_t temp = result->order[i];
        result->order[i] = result->order[g->vertex_count - 1 - i];
        result->order[g->vertex_count - 1 - i] = temp;
    }
    
    free(visited);
    Serial.println("[Graph] Topological sort completed");
}

// =====================================================================================================================
// Strongly Connected Components (Kosaraju's Algorithm)
// =====================================================================================================================

void kosaraju_scc(Graph* g, SCCResult* result) {
    if (!g->is_directed) {
        Serial.println("[Graph] SCC requires directed graph");
        return;
    }
    
    // First DFS to get finishing times
    bool* visited = (bool*)malloc(sizeof(bool) * g->vertex_count);
    memset(visited, 0, sizeof(bool) * g->vertex_count);
    
    uint32_t* finish_stack = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    uint32_t stack_pos = 0;
    
    for (uint32_t i = 0; i < g->vertex_count; i++) {
        if (!visited[i]) {
            topological_sort_dfs(g, i, visited, finish_stack, &stack_pos);
        }
    }
    
    // Create transpose graph
    Graph transpose;
    graph_init(&transpose, g->vertex_count, true, g->is_weighted);
    
    for (uint32_t i = 0; i < g->edge_count; i++) {
        graph_add_edge(&transpose, g->edges[i].to, g->edges[i].from, g->edges[i].weight);
    }
    
    // Second DFS on transpose graph
    memset(visited, 0, sizeof(bool) * g->vertex_count);
    result->component_ids = (uint32_t*)malloc(sizeof(uint32_t) * g->vertex_count);
    result->component_count = 0;
    
    for (int32_t i = g->vertex_count - 1; i >= 0; i--) {
        uint32_t vertex = finish_stack[i];
        if (!visited[vertex]) {
            TraversalResult trav;
            graph_dfs(&transpose, vertex, &trav);
            
            for (uint32_t j = 0; j < trav.count; j++) {
                result->component_ids[trav.order[j]] = result->component_count;
            }
            
            result->component_count++;
            free(trav.order);
            free(trav.parent);
            free(trav.distance);
        }
    }
    
    free(visited);
    free(finish_stack);
    
    Serial.printf("[Graph] Found %d strongly connected components\n",
                  result->component_count);
}

// =====================================================================================================================
// Graph Algorithms Initialization
// =====================================================================================================================

void graph_algorithms_init() {
    Serial.println("[Graph] Initializing graph algorithms...");
    
    // Initialize global graph
    graph_init(&g_graph, 100, false, true);
    
    Serial.println("[Graph] Graph algorithms initialized");
}

// =====================================================================================================================
// End of graph_algorithms.cpp
// Lines: ~1000
// =====================================================================================================================

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { RefreshCw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import cytoscape from 'cytoscape';

// Dynamically import CytoscapeComponent to avoid SSR issues
// @ts-expect-error - react-cytoscapejs doesn't have TypeScript declarations
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CytoscapeComponent: any = dynamic(() => import('react-cytoscapejs'), { ssr: false });

// Global flag to track if cola is registered
let colaRegistered = false;

interface Entity {
  id: string;
  title: string;
  type: string;
  summary?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  signal?: Array<{
    importance: number;
    recency: number;
    novelty: number;
  }>;
}

interface Edge {
  id: string;
  from_id: string;
  to_id: string;
  kind: string;
  confidence?: number;
  importance?: number;
  description?: string;
  metadata?: Record<string, unknown>;
}

interface CytoscapeElement {
  data: {
    id: string;
    label: string;
    type?: string;
    summary?: string;
    size?: number;
    color?: string;
    source?: string;
    target?: string;
    edgeLabel?: string;
  };
  classes?: string;
}

// Color palette for different entity types
const TYPE_COLORS: Record<string, string> = {
  person: '#3b82f6', // blue
  organization: '#8b5cf6', // purple
  project: '#10b981', // green
  product: '#06b6d4', // cyan
  goal: '#f59e0b', // amber
  core_identity: '#ec4899', // pink
  concept: '#6366f1', // indigo
  decision: '#14b8a6', // teal
  task: '#84cc16', // lime
  skill: '#f97316', // orange
  event: '#ef4444', // red
  location: '#78716c', // stone
  default: '#6b7280', // gray
};

interface NodeData {
  id: string;
  label: string;
  type?: string;
  summary?: string;
  size?: number;
  color?: string;
}

export default function EntitiesPage(): React.JSX.Element {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [cytoscapeElements, setCytoscapeElements] = useState<CytoscapeElement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [isCyReady, setIsCyReady] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setIsCyReady(false); // Reset cy ready state when reloading data

    try {
      const response = await fetch('/api/entities?limit=200&includeEdges=true');
      const data = await response.json();

      if (data.error) {
        setError(data.error);
        return;
      }

      setEntities(data.entities || []);
      setEdges(data.edges || []);

      // Find ALL Ryan York entity IDs
      const allRyanYorkEntities = (data.entities || []).filter((e: Entity) =>
        e.title.toLowerCase().includes('ryan york')
      );
      const ryanYorkIds = new Set(allRyanYorkEntities.map((e: Entity) => e.id));

      console.log('=== RYAN YORK FILTERING DEBUG ===');
      console.log('All Ryan York entities found:', allRyanYorkEntities.length);
      allRyanYorkEntities.forEach((e: Entity, i: number) => {
        console.log(`  ${i + 1}. ID: ${e.id}, Title: ${e.title}`);
      });
      console.log('Ryan York IDs to filter:', Array.from(ryanYorkIds));
      console.log('Total entities:', data.entities?.length);
      console.log('Total edges before filter:', data.edges?.length);

      console.log('Edges connected to any Ryan York:', data.edges?.filter((e: Edge) =>
        ryanYorkIds.has(e.from_id) || ryanYorkIds.has(e.to_id)
      ).length);

      // Calculate connection count for each entity (excluding Ryan York connections)
      const connectionCounts = new Map<string, number>();
      (data.edges || []).forEach((edge: Edge) => {
        // Skip edges connected to any Ryan York entity
        if (ryanYorkIds.has(edge.from_id) || ryanYorkIds.has(edge.to_id)) {
          return;
        }

        connectionCounts.set(edge.from_id, (connectionCounts.get(edge.from_id) || 0) + 1);
        connectionCounts.set(edge.to_id, (connectionCounts.get(edge.to_id) || 0) + 1);
      });

      // Transform data for Cytoscape, excluding all Ryan York entities
      const nodeElements: CytoscapeElement[] = (data.entities || [])
        .filter((entity: Entity) => !ryanYorkIds.has(entity.id))
        .map((entity: Entity) => {
          const connections = connectionCounts.get(entity.id) || 0;

          // Get importance from signal data (default to 0.5 if not present)
          const importance = entity.signal?.[0]?.importance ?? 0.5;

          // Calculate node size based on both connection count and importance
          // Base size: 10
          // Connection factor: connections * 20 (so 10 connections = +200)
          // Importance factor: importance * 120 (so 1.0 importance = +120)
          // Max size: 300
          // Small nodes (0 connections, 0.5 importance): 70px
          const nodeSize = Math.min(
            10 + (connections * 20) + (importance * 120),
            300
          );

          return {
            data: {
              id: entity.id,
              label: entity.title,
              type: entity.type,
              summary: entity.summary,
              size: nodeSize,
              color: TYPE_COLORS[entity.type] || TYPE_COLORS.default,
            },
            classes: entity.type,
          };
        });

      // Filter out edges connected to any Ryan York entity
      const edgeElements: CytoscapeElement[] = (data.edges || [])
        .filter((edge: Edge) => {
          // Exclude any edge connected to any Ryan York entity
          return !ryanYorkIds.has(edge.from_id) && !ryanYorkIds.has(edge.to_id);
        })
        .map((edge: Edge) => ({
          data: {
            id: `${edge.from_id}-${edge.to_id}`,
            source: edge.from_id,
            target: edge.to_id,
            edgeLabel: edge.kind,
          },
        }));

      const elements = [...nodeElements, ...edgeElements];
      console.log('Setting Cytoscape data with', nodeElements.length, 'nodes and', edgeElements.length, 'edges');

      setCytoscapeElements(elements);
      setSelectedNode(null); // Clear selection when reloading data
    } catch (err) {
      console.error('Failed to load entities:', err);
      setError('Failed to load entities');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);


  // Register cola layout extension once globally
  useEffect(() => {
    if (!colaRegistered) {
      // @ts-expect-error - cytoscape-cola doesn't have TypeScript declarations
      import('cytoscape-cola').then((colaModule) => {
        const cola = colaModule.default;
        if (typeof cola === 'function') {
          try {
            cytoscape.use(cola);
            colaRegistered = true;
            console.log('Cola layout registered globally');
          } catch (err) {
            console.error('Failed to register cola layout:', err);
          }
        }
      }).catch(err => {
        console.error('Failed to load cola module:', err);
      });
    }
  }, []);

  // Cytoscape setup after mount
  useEffect(() => {
    if (!isCyReady || !cyRef.current || cytoscapeElements.length === 0) {
      console.log('Waiting for cy to be ready...', { isCyReady, hasCy: !!cyRef.current, elemCount: cytoscapeElements.length });
      return;
    }

    const cy = cyRef.current;
    console.log('Starting layout with', cytoscapeElements.length, 'elements');

    // Give a small delay to ensure cola is registered
    setTimeout(() => {
      // Run cola layout for force-directed positioning with clustering
      console.log('Running cola layout...');
      try {
        const colaLayout = cy.layout({
          name: 'cola',
          animate: true,
          refresh: 1,
          maxSimulationTime: 8000,
          ungrabifyWhileSimulating: false,
          fit: true,
          padding: 100,
          nodeDimensionsIncludeLabels: true,
          edgeLength: 450, // Increased to space nodes out more
          nodeSpacing: 250, // Increased for more breathing room
          avoidOverlap: true,
          handleDisconnected: true,
          convergenceThreshold: 0.01,
          randomize: true, // Start with random positions
        } as cytoscape.LayoutOptions);

        colaLayout.run();
        colaLayout.one('layoutstop', () => {
          console.log('Cola layout complete');
        });
      } catch (err) {
        console.error('Cola layout failed, falling back to cose:', err);
        // Fallback to cose layout if cola fails
        cy.layout({
          name: 'cose',
          animate: true,
          nodeDimensionsIncludeLabels: true,
          nodeRepulsion: 400000,
          idealEdgeLength: 400,
          nodeOverlap: 200,
          fit: true,
          padding: 80,
        } as cytoscape.LayoutOptions).run();
      }
    }, 100);

    // Handle node tap (only register once)
    cy.removeListener('tap');
    cy.on('tap', 'node', (evt: cytoscape.EventObject) => {
      const node = evt.target;
      setSelectedNode(node.data());

      // Hide all nodes except the selected node and its neighbors
      const connectedNodes = node.neighborhood('node').add(node);
      const connectedEdges = node.connectedEdges();

      // Hide all nodes and edges first
      cy.nodes().addClass('dimmed');
      cy.edges().addClass('dimmed');

      // Show only connected elements
      connectedNodes.removeClass('dimmed');
      connectedEdges.removeClass('dimmed');
    });

    // Handle background tap to reset view
    cy.on('tap', (evt: cytoscape.EventObject) => {
      if (evt.target === cy) {
        // Clicked on background, not a node
        setSelectedNode(null);

        // Show all nodes and edges
        cy.nodes().removeClass('dimmed');
        cy.edges().removeClass('dimmed');
      }
    });
  }, [cytoscapeElements, isCyReady]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      const cy = cyRef.current;
      cy.zoom(cy.zoom() * 1.2);
      cy.center();
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      const cy = cyRef.current;
      cy.zoom(cy.zoom() / 1.2);
      cy.center();
    }
  };

  const handleFitView = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 50);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Entity Graph</h1>
            <p className="text-sm text-gray-600 mt-1">
              Visualizing {entities.length} entities and {edges.length} connections
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleZoomIn} variant="outline" size="sm">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button onClick={handleZoomOut} variant="outline" size="sm">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button onClick={handleFitView} variant="outline" size="sm">
              <Maximize2 className="h-4 w-4" />
            </Button>
            <Button onClick={loadData} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Graph Canvas */}
        <div className="flex-1 relative min-w-0 z-0" style={{ width: 'calc(100% - 320px)' }}>
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading entities...</p>
              </div>
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <Button onClick={loadData}>Try Again</Button>
              </div>
            </div>
          ) : (
            <CytoscapeComponent
              elements={cytoscapeElements}
              cy={(cy: cytoscape.Core) => {
                console.log('Cytoscape instance ready');
                cyRef.current = cy;
                setIsCyReady(true);
              }}
              style={{ width: '100%', height: '100%' }}
              stylesheet={[
                {
                  selector: 'node',
                  style: {
                    'background-color': 'data(color)',
                    'width': 'data(size)',
                    'height': 'data(size)',
                    'label': 'data(label)',
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'text-margin-y': 8,
                    'font-size': '16px',
                    'font-weight': '600',
                    'color': '#1f2937',
                    'text-background-color': '#ffffff',
                    'text-background-opacity': 0.95,
                    'text-background-padding': '6px',
                    'text-background-shape': 'roundrectangle',
                    'text-wrap': 'wrap',
                    'text-max-width': '200px',
                    'border-width': 3,
                    'border-color': '#ffffff',
                  },
                },
                {
                  selector: 'node.dimmed',
                  style: {
                    'opacity': 0.1,
                    'text-opacity': 0,
                  },
                },
                {
                  selector: 'node:selected',
                  style: {
                    'border-color': '#1e40af',
                    'border-width': 3,
                    'font-weight': 'bold',
                    'color': '#1e40af',
                  },
                },
                {
                  selector: 'edge',
                  style: {
                    'width': 3,
                    'line-color': '#cbd5e1',
                    'target-arrow-color': '#cbd5e1',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.5,
                  },
                },
                {
                  selector: 'edge.dimmed',
                  style: {
                    'opacity': 0.05,
                  },
                },
              ]}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="w-80 flex-shrink-0 bg-white border-l border-gray-200 p-4 overflow-y-auto relative z-10">
          {selectedNode ? (
            <div>
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-lg font-semibold text-gray-900">Selected Entity</h2>
                <Button
                  onClick={() => {
                    setSelectedNode(null);
                    if (cyRef.current) {
                      cyRef.current.nodes().removeClass('dimmed');
                      cyRef.current.edges().removeClass('dimmed');
                    }
                  }}
                  variant="outline"
                  size="sm"
                >
                  Clear
                </Button>
              </div>
              <div className="space-y-3">
                <div>
                  <span className="text-xs font-medium text-gray-500 uppercase">Title</span>
                  <p className="text-sm text-gray-900 mt-1">{selectedNode.label}</p>
                </div>
                <div>
                  <span className="text-xs font-medium text-gray-500 uppercase">Type</span>
                  <div className="mt-1">
                    <span
                      className="inline-flex items-center px-2 py-1 rounded text-xs font-medium"
                      style={{ backgroundColor: selectedNode.color + '20', color: selectedNode.color }}
                    >
                      {selectedNode.type}
                    </span>
                  </div>
                </div>
                {selectedNode.summary && (
                  <div>
                    <span className="text-xs font-medium text-gray-500 uppercase">Summary</span>
                    <p className="text-sm text-gray-700 mt-1">{selectedNode.summary}</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Legend</h2>
              <div className="space-y-2">
                {Object.entries(TYPE_COLORS)
                  .filter(([type]) => type !== 'default')
                  .map(([type, color]) => (
                    <div key={type} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-sm text-gray-700 capitalize">
                        {type.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
              </div>

              <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-800 mb-2">
                  <strong>Tips:</strong>
                </p>
                <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
                  <li>Hover over nodes to see details</li>
                  <li>Click to select and view full information</li>
                  <li>Scroll to zoom, drag canvas to pan</li>
                  <li>Use &ldquo;Fit View&rdquo; button to reset</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

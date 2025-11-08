'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { RefreshCw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

// Dynamically import ForceGraph2D to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface Entity {
  id: string;
  title: string;
  type: string;
  summary?: string;
  metadata?: any;
  created_at: string;
}

interface Edge {
  id: string;
  from_id: string;
  to_id: string;
  kind: string;
  confidence?: number;
  importance?: number;
  description?: string;
  metadata?: any;
}

interface GraphNode {
  id: string;
  name: string;
  type: string;
  summary?: string;
  val: number;
  color: string;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
  confidence: number;
  importance: number;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
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

export default function EntitiesPage(): React.JSX.Element {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const graphRef = useRef<any>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/entities?limit=200&includeEdges=true');
      const data = await response.json();

      if (data.error) {
        setError(data.error);
        return;
      }

      setEntities(data.entities || []);
      setEdges(data.edges || []);

      // Find Ryan York's entity ID
      const ryanYorkEntity = (data.entities || []).find((e: Entity) =>
        e.title.toLowerCase().includes('ryan york')
      );
      const ryanYorkId = ryanYorkEntity?.id;

      // Calculate connection count for each entity (excluding Ryan York connections)
      const connectionCounts = new Map<string, number>();
      (data.edges || []).forEach((edge: Edge) => {
        // Skip edges connected to Ryan York
        if (edge.from_id === ryanYorkId || edge.to_id === ryanYorkId) {
          return;
        }

        connectionCounts.set(edge.from_id, (connectionCounts.get(edge.from_id) || 0) + 1);
        connectionCounts.set(edge.to_id, (connectionCounts.get(edge.to_id) || 0) + 1);
      });

      // Transform data for force graph
      const nodes: GraphNode[] = (data.entities || []).map((entity: Entity) => {
        const connections = connectionCounts.get(entity.id) || 0;
        // Scale node size: base 3, add 1 per connection, max 15
        const nodeSize = Math.min(3 + connections * 0.8, 15);

        return {
          id: entity.id,
          name: entity.title,
          type: entity.type,
          summary: entity.summary,
          val: nodeSize,
          color: TYPE_COLORS[entity.type] || TYPE_COLORS.default,
        };
      });

      const links: GraphLink[] = (data.edges || []).map((edge: Edge) => ({
        source: edge.from_id,
        target: edge.to_id,
        label: edge.kind,
        confidence: edge.confidence || 1,
        importance: edge.importance || 1,
      }));

      setGraphData({ nodes, links });
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

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node);
  }, []);

  const handleZoomIn = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() * 1.2);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() / 1.2);
    }
  };

  const handleFitView = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400);
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
        <div className="flex-1 relative">
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
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              nodeLabel="name"
              nodeAutoColorBy="type"
              // Force simulation parameters for much better spacing
              d3AlphaDecay={0.01}
              d3VelocityDecay={0.2}
              cooldownTicks={300}
              linkDistance={200}
              chargeStrength={-400}
              nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                // Draw node circle
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
                ctx.fillStyle = node.color;
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 1.5 / globalScale;
                ctx.stroke();

                // Only show labels when zoomed in enough or for selected node
                const isSelected = selectedNode?.id === node.id;
                const shouldShowLabel = globalScale > 0.8 || isSelected;

                if (shouldShowLabel) {
                  const label = node.name;
                  const fontSize = Math.max(12 / globalScale, 10);
                  ctx.font = `${isSelected ? 'bold ' : ''}${fontSize}px Sans-Serif`;
                  const textWidth = ctx.measureText(label).width;
                  const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4);

                  // Draw label background
                  ctx.fillStyle = isSelected ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.8)';
                  ctx.fillRect(
                    node.x - bckgDimensions[0] / 2,
                    node.y + node.val + 2,
                    bckgDimensions[0],
                    bckgDimensions[1]
                  );

                  // Draw label text
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';
                  ctx.fillStyle = isSelected ? '#1e40af' : '#1f2937';
                  ctx.fillText(label, node.x, node.y + node.val + 2 + bckgDimensions[1] / 2);
                }
              }}
              linkLabel="label"
              linkColor={() => '#cbd5e1'}
              linkWidth={(link: any) => (link.importance || 1) * 1.5}
              linkDirectionalParticles={2}
              linkDirectionalParticleWidth={2}
              onNodeClick={handleNodeClick}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white border-l border-gray-200 p-4 overflow-y-auto">
          {selectedNode ? (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Selected Entity</h2>
              <div className="space-y-3">
                <div>
                  <span className="text-xs font-medium text-gray-500 uppercase">Title</span>
                  <p className="text-sm text-gray-900 mt-1">{selectedNode.name}</p>
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
                  <li>Click a node to see details</li>
                  <li>Drag nodes to rearrange</li>
                  <li>Scroll to zoom in/out</li>
                  <li><strong>Zoom in to reveal labels</strong></li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

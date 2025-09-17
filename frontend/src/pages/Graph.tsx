import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Network, ZoomIn, ZoomOut, RotateCcw, Download, Settings } from 'lucide-react'
import LoadingSpinner from '../components/LoadingSpinner'
import { DataSet, Network as VisNetwork } from 'vis-network/standalone/esm/vis-network'

interface GraphNode {
  id: string
  label: string
  type: 'contact' | 'phone' | 'message' | 'call'
  value?: number
  color?: string
  title?: string
  metadata?: any
}

interface GraphEdge {
  id: string
  from: string
  to: string
  label?: string
  type: 'message' | 'call' | 'contact_relation'
  weight?: number
  color?: string
  title?: string
  arrows?: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  summary: {
    total_nodes: number
    total_edges: number
    contact_count: number
    message_count: number
    call_count: number
  }
}

/**
 * Graph visualization page component
 */
function Graph() {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [networkInstance, setNetworkInstance] = useState<VisNetwork | null>(null)
  const [layoutType, setLayoutType] = useState<'hierarchical' | 'physics' | 'static'>('physics')
  const networkRef = useRef<HTMLDivElement>(null)

  // Fetch graph data
  const { data: graphData, isLoading, error } = useQuery<GraphData>({
    queryKey: ['graph'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/graph')
      if (!response.ok) {
        throw new Error('Failed to fetch graph data')
      }
      return response.json()
    }
  })

  useEffect(() => {
    if (graphData && networkRef.current && !networkInstance) {
      // Prepare nodes
      const nodes = new DataSet(graphData.nodes.map(node => ({
        id: node.id,
        label: node.label,
        title: node.title || `${node.type}: ${node.label}`,
        value: node.value || 1,
        color: getNodeColor(node.type),
        shape: getNodeShape(node.type),
        font: { color: '#333333', size: 12 },
        borderWidth: 2
      })))

      // Prepare edges
      const edges = new DataSet(graphData.edges.map(edge => ({
        id: edge.id,
        from: edge.from,
        to: edge.to,
        label: edge.label,
        title: edge.title || `${edge.type}: ${edge.label || ''}`,
        width: Math.max(1, (edge.weight || 1) * 2),
        color: getEdgeColor(edge.type),
        arrows: edge.arrows || 'to',
        smooth: { type: 'continuous' }
      })))

      const options = {
        layout: getLayoutOptions(layoutType),
        physics: {
          enabled: layoutType === 'physics',
          stabilization: { iterations: 100 }
        },
        interaction: {
          hover: true,
          selectConnectedEdges: false
        },
        nodes: {
          scaling: {
            min: 10,
            max: 30
          }
        },
        edges: {
          scaling: {
            min: 1,
            max: 5
          },
          smooth: {
            type: 'continuous'
          }
        }
      }

      const network = new VisNetwork(networkRef.current, { nodes, edges }, options)
      
      // Handle node selection
      network.on('selectNode', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          const node = graphData.nodes.find(n => n.id === nodeId)
          setSelectedNode(node || null)
        }
      })

      network.on('deselectNode', () => {
        setSelectedNode(null)
      })

      setNetworkInstance(network)
    }
  }, [graphData, networkInstance, layoutType])

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'contact':
        return { background: '#3B82F6', border: '#1D4ED8' }
      case 'phone':
        return { background: '#10B981', border: '#047857' }
      case 'message':
        return { background: '#F59E0B', border: '#D97706' }
      case 'call':
        return { background: '#EF4444', border: '#DC2626' }
      default:
        return { background: '#6B7280', border: '#374151' }
    }
  }

  const getNodeShape = (type: string) => {
    switch (type) {
      case 'contact':
        return 'circle'
      case 'phone':
        return 'square'
      case 'message':
        return 'triangle'
      case 'call':
        return 'diamond'
      default:
        return 'dot'
    }
  }

  const getEdgeColor = (type: string) => {
    switch (type) {
      case 'message':
        return { color: '#3B82F6', opacity: 0.7 }
      case 'call':
        return { color: '#EF4444', opacity: 0.7 }
      case 'contact_relation':
        return { color: '#6B7280', opacity: 0.5 }
      default:
        return { color: '#9CA3AF', opacity: 0.5 }
    }
  }

  const getLayoutOptions = (layout: string) => {
    switch (layout) {
      case 'hierarchical':
        return {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed'
          }
        }
      case 'static':
        return {
          randomSeed: 42
        }
      default:
        return {}
    }
  }

  const handleZoomIn = () => {
    if (networkInstance) {
      const scale = networkInstance.getScale()
      networkInstance.moveTo({ scale: scale * 1.2 })
    }
  }

  const handleZoomOut = () => {
    if (networkInstance) {
      const scale = networkInstance.getScale()
      networkInstance.moveTo({ scale: scale * 0.8 })
    }
  }

  const handleReset = () => {
    if (networkInstance) {
      networkInstance.fit()
    }
  }

  const handleExportPNG = () => {
    if (networkRef.current) {
      const canvas = networkRef.current.querySelector('canvas')
      if (canvas) {
        const link = document.createElement('a')
        link.download = 'forensiq-graph.png'
        link.href = canvas.toDataURL()
        link.click()
      }
    }
  }

  const handleLayoutChange = (newLayout: 'hierarchical' | 'physics' | 'static') => {
    setLayoutType(newLayout)
    if (networkInstance) {
      networkInstance.destroy()
      setNetworkInstance(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <Network className="mx-auto h-12 w-12 text-red-400 mb-4" />
          <h2 className="text-lg font-semibold text-red-800 mb-2">Graph Load Error</h2>
          <p className="text-red-600">
            Failed to load graph data. Please check your connection and try again.
          </p>
        </div>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="text-center py-12">
        <Network className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900">No Graph Data</h3>
        <p className="text-gray-600">
          No evidence data available for visualization. Parse some UFDR files first.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evidence Graph</h1>
          <p className="text-sm text-gray-600">
            Network visualization of contacts, communications, and relationships
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1">
            <button
              onClick={handleZoomIn}
              className="p-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded"
              title="Zoom In"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded"
              title="Zoom Out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <button
              onClick={handleReset}
              className="p-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded"
              title="Reset View"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
            <button
              onClick={handleExportPNG}
              className="p-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded"
              title="Export as PNG"
            >
              <Download className="h-4 w-4" />
            </button>
          </div>

          <select
            value={layoutType}
            onChange={(e) => handleLayoutChange(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="physics">Physics Layout</option>
            <option value="hierarchical">Hierarchical Layout</option>
            <option value="static">Static Layout</option>
          </select>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-blue-600">{graphData.summary.total_nodes}</div>
          <div className="text-xs text-gray-600">Total Nodes</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-green-600">{graphData.summary.total_edges}</div>
          <div className="text-xs text-gray-600">Connections</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-purple-600">{graphData.summary.contact_count}</div>
          <div className="text-xs text-gray-600">Contacts</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-orange-600">{graphData.summary.message_count}</div>
          <div className="text-xs text-gray-600">Messages</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-red-600">{graphData.summary.call_count}</div>
          <div className="text-xs text-gray-600">Calls</div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Graph Visualization */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg shadow h-96 lg:h-[600px] relative">
            <div 
              ref={networkRef}
              className="w-full h-full rounded-lg"
              style={{ minHeight: '400px' }}
            />
            
            {/* Legend */}
            <div className="absolute top-4 left-4 bg-white bg-opacity-90 rounded-lg p-3 shadow">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Legend</h4>
              <div className="space-y-1 text-xs">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                  <span>Contacts</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500"></div>
                  <span>Phone Numbers</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-orange-500 transform rotate-45"></div>
                  <span>Messages</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-red-500 transform rotate-45"></div>
                  <span>Calls</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Node Details Panel */}
        <div className="space-y-4">
          {selectedNode ? (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Node Details</h3>
              
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-700">Type</label>
                  <p className="text-sm text-gray-900 capitalize">{selectedNode.type}</p>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-700">Label</label>
                  <p className="text-sm text-gray-900">{selectedNode.label}</p>
                </div>
                
                {selectedNode.value && (
                  <div>
                    <label className="text-sm font-medium text-gray-700">Connections</label>
                    <p className="text-sm text-gray-900">{selectedNode.value}</p>
                  </div>
                )}
                
                {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                  <div>
                    <label className="text-sm font-medium text-gray-700">Metadata</label>
                    <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded mt-1">
                      <pre>{JSON.stringify(selectedNode.metadata, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6 text-center">
              <Settings className="mx-auto h-8 w-8 text-gray-400 mb-2" />
              <h3 className="text-sm font-medium text-gray-900">Node Selection</h3>
              <p className="text-xs text-gray-600 mt-1">
                Click on a node in the graph to view its details here.
              </p>
            </div>
          )}

          {/* Instructions */}
          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Graph Controls</h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• Click and drag to pan</li>
              <li>• Scroll to zoom in/out</li>
              <li>• Click nodes for details</li>
              <li>• Drag nodes to reposition</li>
              <li>• Use layout options to reorganize</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Graph
import React from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Calendar, User, Phone, MessageCircle, Clock, ExternalLink, Download } from 'lucide-react'
import LoadingSpinner from '../components/LoadingSpinner'
import EntityHighlighter from '../components/EntityHighlighter'
import ExportButton from '../components/ExportButton'

interface EvidenceDetail {
  id: string
  type: 'message' | 'call' | 'contact'
  content: string
  timestamp?: string
  contact?: string
  phone?: string
  direction?: 'inbound' | 'outbound' | 'sent' | 'received'
  duration?: number
  entities?: { [key: string]: string[] }
  metadata?: { [key: string]: any }
  attachments?: Array<{
    id: string
    name: string
    type: string
    size: number
    path: string
  }>
  conversation?: Array<{
    id: string
    content: string
    timestamp: string
    direction: 'sent' | 'received'
    contact?: string
  }>
  source: string
  raw_data?: any
}

/**
 * Evidence detail page component
 */
function Detail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: evidence, isLoading, error } = useQuery<EvidenceDetail>({
    queryKey: ['evidence', id],
    queryFn: async () => {
      if (!id) throw new Error('No evidence ID provided')
      
      const response = await fetch(`http://localhost:8000/api/evidence/${id}`)
      if (!response.ok) {
        throw new Error('Failed to fetch evidence details')
      }
      return response.json()
    },
    enabled: !!id
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !evidence) {
    return (
      <div className="text-center py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Evidence Not Found</h2>
          <p className="text-red-600 mb-4">
            The requested evidence could not be found or loaded.
          </p>
          <Link 
            to="/" 
            className="inline-flex items-center text-blue-600 hover:text-blue-800"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Search
          </Link>
        </div>
      </div>
    )
  }

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'Unknown'
    return new Date(timestamp).toLocaleString()
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'message':
        return 'bg-blue-100 text-blue-800'
      case 'call':
        return 'bg-green-100 text-green-800'
      case 'contact':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getDirectionColor = (direction?: string) => {
    switch (direction) {
      case 'sent':
      case 'outbound':
        return 'text-blue-600'
      case 'received':
      case 'inbound':
        return 'text-green-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Back
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Evidence Detail</h1>
            <p className="text-sm text-gray-600">ID: {evidence.id}</p>
          </div>
        </div>
        
        <ExportButton 
          data={[evidence]}
          filename={`evidence-${evidence.id}`}
          type="detail"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Primary Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Evidence Overview */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Overview</h2>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTypeColor(evidence.type)}`}>
                {evidence.type}
              </span>
            </div>

            <div className="space-y-4">
              {/* Content */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Content</h3>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <EntityHighlighter 
                    text={evidence.content}
                    entities={evidence.entities}
                  />
                </div>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {evidence.contact && (
                  <div className="flex items-center space-x-2">
                    <User className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Contact:</span>
                    <span className="text-sm font-medium text-gray-900">{evidence.contact}</span>
                  </div>
                )}

                {evidence.phone && (
                  <div className="flex items-center space-x-2">
                    <Phone className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Phone:</span>
                    <span className="text-sm font-medium text-gray-900">{evidence.phone}</span>
                  </div>
                )}

                {evidence.timestamp && (
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Timestamp:</span>
                    <span className="text-sm font-medium text-gray-900">{formatTimestamp(evidence.timestamp)}</span>
                  </div>
                )}

                {evidence.direction && (
                  <div className="flex items-center space-x-2">
                    <MessageCircle className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Direction:</span>
                    <span className={`text-sm font-medium ${getDirectionColor(evidence.direction)}`}>
                      {evidence.direction}
                    </span>
                  </div>
                )}

                {evidence.duration && (
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-600">Duration:</span>
                    <span className="text-sm font-medium text-gray-900">{formatDuration(evidence.duration)}</span>
                  </div>
                )}

                <div className="flex items-center space-x-2">
                  <ExternalLink className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-600">Source:</span>
                  <span className="text-sm font-medium text-gray-900">{evidence.source}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Conversation Thread */}
          {evidence.conversation && evidence.conversation.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Conversation Thread
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({evidence.conversation.length} messages)
                </span>
              </h2>
              
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {evidence.conversation.map((message, index) => (
                  <div 
                    key={`${message.id}-${index}`}
                    className={`flex ${message.direction === 'sent' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div 
                      className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                        message.direction === 'sent' 
                          ? 'bg-blue-500 text-white' 
                          : 'bg-gray-200 text-gray-900'
                      }`}
                    >
                      <p className="text-sm">{message.content}</p>
                      <p className={`text-xs mt-1 ${
                        message.direction === 'sent' ? 'text-blue-100' : 'text-gray-500'
                      }`}>
                        {formatTimestamp(message.timestamp)}
                        {message.contact && ` • ${message.contact}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Attachments */}
          {evidence.attachments && evidence.attachments.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Attachments
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({evidence.attachments.length} files)
                </span>
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {evidence.attachments.map((attachment) => (
                  <div 
                    key={attachment.id}
                    className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <Download className="h-8 w-8 text-gray-400 mr-3" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {attachment.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {attachment.type} • {(attachment.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <button 
                      className="ml-2 text-blue-600 hover:text-blue-800"
                      onClick={() => {
                        // Handle download - would connect to backend endpoint
                        console.log('Download attachment:', attachment.path)
                      }}
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Entities */}
          {evidence.entities && Object.keys(evidence.entities).length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Extracted Entities</h3>
              <div className="space-y-3">
                {Object.entries(evidence.entities).map(([entityType, entities]) => (
                  <div key={entityType}>
                    <h4 className="text-sm font-medium text-gray-700 mb-2 capitalize">
                      {entityType.replace(/_/g, ' ')}
                    </h4>
                    <div className="flex flex-wrap gap-1">
                      {entities.map((entity, index) => (
                        <span 
                          key={`${entity}-${index}`}
                          className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full"
                        >
                          {entity}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          {evidence.metadata && Object.keys(evidence.metadata).length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Metadata</h3>
              <dl className="space-y-2">
                {Object.entries(evidence.metadata).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {key.replace(/_/g, ' ')}
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {/* Raw Data */}
          {evidence.raw_data && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Raw Data</h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded-md overflow-x-auto">
                <pre className="text-xs whitespace-pre-wrap">
                  {JSON.stringify(evidence.raw_data, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Detail
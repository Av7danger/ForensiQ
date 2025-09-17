import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import LoadingSpinner from '../components/LoadingSpinner'
import Pagination from '../components/Pagination'
import EntityHighlighter from '../components/EntityHighlighter'
import ExportButton from '../components/ExportButton'
import { Search, MessageCircle, Phone, Users, Calendar, Clock } from 'lucide-react'

interface SearchResult {
  id: string
  type: 'message' | 'call' | 'contact'
  score: number
  content: string
  timestamp?: string
  contact?: string
  phone?: string
  entities?: { [key: string]: string[] }
  source: string
}

interface SearchResponse {
  results: SearchResult[]
  total: number
  page: number
  per_page: number
  query: string
  search_time: number
}

/**
 * Main dashboard page with search functionality
 */
function Dashboard() {
  const [query, setQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [searchType, setSearchType] = useState<'all' | 'messages' | 'calls' | 'contacts'>('all')
  const [hasSearched, setHasSearched] = useState(false)
  const navigate = useNavigate()

  // Search query
  const { data: searchResults, isLoading, error } = useQuery<SearchResponse>({
    queryKey: ['search', query, currentPage, searchType],
    queryFn: async () => {
      if (!query.trim()) return null
      
      const params = new URLSearchParams({
        q: query,
        page: currentPage.toString(),
        per_page: '20',
        type: searchType === 'all' ? '' : searchType
      })

      const response = await fetch(`http://localhost:8000/api/search?${params}`)
      if (!response.ok) {
        throw new Error('Search failed')
      }
      return response.json()
    },
    enabled: !!query.trim() && hasSearched,
    keepPreviousData: true
  })

  const handleSearch = (searchQuery: string) => {
    setQuery(searchQuery)
    setCurrentPage(1)
    setHasSearched(true)
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'Unknown'
    return new Date(timestamp).toLocaleString()
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'message':
        return <MessageCircle className="h-4 w-4 text-blue-600" />
      case 'call':
        return <Phone className="h-4 w-4 text-green-600" />
      case 'contact':
        return <Users className="h-4 w-4 text-purple-600" />
      default:
        return <Search className="h-4 w-4 text-gray-600" />
    }
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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Search Evidence</h1>
        <p className="mt-1 text-sm text-gray-600">
          Search through parsed UFDR data including messages, calls, and contacts
        </p>
      </div>

      {/* Search Interface */}
      <div className="bg-white rounded-lg shadow p-6">
        <SearchBar 
          onSearch={handleSearch} 
          placeholder="Search messages, contacts, phone numbers..."
          className="mb-4"
        />
        
        {/* Search Type Filter */}
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-700">Filter by:</span>
          {[
            { key: 'all', label: 'All Results', icon: Search },
            { key: 'messages', label: 'Messages', icon: MessageCircle },
            { key: 'calls', label: 'Calls', icon: Phone },
            { key: 'contacts', label: 'Contacts', icon: Users }
          ].map((filter) => {
            const Icon = filter.icon
            return (
              <button
                key={filter.key}
                onClick={() => setSearchType(filter.key as any)}
                className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  searchType === filter.key
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Icon className="h-4 w-4 mr-2" />
                {filter.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Search Error</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>Failed to search evidence. Please check your connection and try again.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {searchResults && !isLoading && (
        <div className="space-y-4">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Search Results
              </h2>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                {searchResults.total.toLocaleString()} results
              </span>
              <span className="text-sm text-gray-500">
                <Clock className="inline h-3 w-3 mr-1" />
                {searchResults.search_time.toFixed(2)}s
              </span>
            </div>
            
            {searchResults.results.length > 0 && (
              <ExportButton 
                data={searchResults.results}
                filename={`forensiq-search-${query.replace(/\s+/g, '-')}`}
                type="search-results"
              />
            )}
          </div>

          {/* Results List */}
          {searchResults.results.length === 0 ? (
            <div className="text-center py-12">
              <Search className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
              <p className="mt-1 text-sm text-gray-500">
                Try different keywords or check your spelling.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <ul className="divide-y divide-gray-200">
                {searchResults.results.map((result, index) => (
                  <li key={`${result.id}-${index}`} className="hover:bg-gray-50">
                    <div 
                      className="px-6 py-4 cursor-pointer"
                      onClick={() => navigate(`/detail/${result.id}`)}
                    >
                      <div className="flex items-start space-x-4">
                        {/* Type Icon */}
                        <div className="flex-shrink-0 mt-1">
                          {getTypeIcon(result.type)}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTypeColor(result.type)}`}>
                              {result.type}
                            </span>
                            {result.contact && (
                              <span className="text-sm font-medium text-gray-900">
                                {result.contact}
                              </span>
                            )}
                            {result.phone && (
                              <span className="text-sm text-gray-600">
                                {result.phone}
                              </span>
                            )}
                            <span className="text-xs text-gray-500">
                              Score: {(result.score * 100).toFixed(1)}%
                            </span>
                          </div>

                          <div className="mb-2">
                            <EntityHighlighter 
                              text={result.content}
                              entities={result.entities}
                              searchQuery={query}
                            />
                          </div>

                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span className="flex items-center">
                              <Calendar className="h-3 w-3 mr-1" />
                              {formatTimestamp(result.timestamp)}
                            </span>
                            <span>Source: {result.source}</span>
                          </div>
                        </div>

                        {/* Score Bar */}
                        <div className="flex-shrink-0 w-16">
                          <div className="text-xs text-gray-600 mb-1 text-center">
                            {(result.score * 100).toFixed(0)}%
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all"
                              style={{ width: `${result.score * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Pagination */}
          {searchResults.total > searchResults.per_page && (
            <Pagination
              currentPage={searchResults.page}
              totalPages={Math.ceil(searchResults.total / searchResults.per_page)}
              onPageChange={handlePageChange}
            />
          )}
        </div>
      )}

      {/* Welcome State */}
      {!hasSearched && (
        <div className="text-center py-12">
          <Search className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-lg font-medium text-gray-900">Welcome to ForensiQ</h3>
          <p className="mt-1 text-sm text-gray-500 max-w-md mx-auto">
            Enter a search query above to find messages, calls, contacts, and other digital evidence 
            from your parsed UFDR files.
          </p>
          <div className="mt-6 text-xs text-gray-400">
            <p>Supported search: Keywords, phone numbers, dates, and entity names</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
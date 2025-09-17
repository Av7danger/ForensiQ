import React, { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import type { SearchBarProps, SearchFilters } from '../types';
import LoadingSpinner from './LoadingSpinner';

/**
 * Search bar component with natural language input and quick filters
 * Supports crypto-only, phone-only, email-only, and URL-only filters
 */
const SearchBar: React.FC<SearchBarProps> = ({ 
  onSearch, 
  isLoading = false, 
  placeholder = "Ask: e.g. 'show chats with bitcoin addresses'" 
}) => {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    cryptoOnly: false,
    phoneOnly: false,
    emailOnly: false,
    urlOnly: false,
  });

  /**
   * Handle search form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      return;
    }

    onSearch(query.trim(), filters);
  };

  /**
   * Handle filter toggle
   */
  const handleFilterToggle = (filterKey: keyof SearchFilters) => {
    setFilters(prev => ({
      ...prev,
      [filterKey]: !prev[filterKey]
    }));
  };

  /**
   * Clear all filters
   */
  const clearFilters = () => {
    setFilters({
      cryptoOnly: false,
      phoneOnly: false,
      emailOnly: false,
      urlOnly: false,
    });
  };

  /**
   * Get active filter count
   */
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Search Input */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
          </div>
          
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            disabled={isLoading}
            className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-md 
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500 
                     disabled:bg-gray-50 disabled:text-gray-500
                     text-base placeholder-gray-400"
            aria-label="Search query"
          />
          
          {/* Filter Toggle Button */}
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`p-1.5 rounded-md transition-colors ${
                showFilters || activeFilterCount > 0
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
              aria-label={`${showFilters ? 'Hide' : 'Show'} filters`}
            >
              <Filter className="h-4 w-4" />
              {activeFilterCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-blue-600 text-white 
                               text-xs rounded-full h-4 w-4 flex items-center 
                               justify-center font-medium">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Quick Filters */}
        {showFilters && (
          <div className="bg-gray-50 rounded-md p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-700">Quick Filters</h3>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="text-sm text-blue-600 hover:text-blue-800 
                           flex items-center space-x-1"
                >
                  <X className="h-3 w-3" />
                  <span>Clear all</span>
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {/* Crypto Only Filter */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.cryptoOnly}
                  onChange={() => handleFilterToggle('cryptoOnly')}
                  className="rounded border-gray-300 text-blue-600 
                           focus:ring-blue-500 focus:ring-offset-0"
                />
                <span className="text-sm text-gray-700">
                  <span className="inline-block w-3 h-3 bg-yellow-400 rounded mr-1"></span>
                  Crypto only
                </span>
              </label>

              {/* Phone Only Filter */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.phoneOnly}
                  onChange={() => handleFilterToggle('phoneOnly')}
                  className="rounded border-gray-300 text-blue-600 
                           focus:ring-blue-500 focus:ring-offset-0"
                />
                <span className="text-sm text-gray-700">
                  <span className="inline-block w-3 h-3 bg-blue-400 rounded mr-1"></span>
                  Phone only
                </span>
              </label>

              {/* Email Only Filter */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.emailOnly}
                  onChange={() => handleFilterToggle('emailOnly')}
                  className="rounded border-gray-300 text-blue-600 
                           focus:ring-blue-500 focus:ring-offset-0"
                />
                <span className="text-sm text-gray-700">
                  <span className="inline-block w-3 h-3 bg-green-400 rounded mr-1"></span>
                  Email only
                </span>
              </label>

              {/* URL Only Filter */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.urlOnly}
                  onChange={() => handleFilterToggle('urlOnly')}
                  className="rounded border-gray-300 text-blue-600 
                           focus:ring-blue-500 focus:ring-offset-0"
                />
                <span className="text-sm text-gray-700">
                  <span className="inline-block w-3 h-3 bg-purple-400 rounded mr-1"></span>
                  URL only
                </span>
              </label>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="inline-flex items-center px-6 py-3 border border-transparent 
                     text-base font-medium rounded-md text-white bg-blue-600 
                     hover:bg-blue-700 focus:outline-none focus:ring-2 
                     focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 
                     disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Search
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SearchBar;
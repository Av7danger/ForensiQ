import React from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { Search, Network, FileText, Upload, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Detail from './pages/Detail'
import Graph from './pages/Graph'

/**
 * Main application component with layout and routing
 */
function App() {
  const location = useLocation()

  const navigation = [
    { name: 'Search', href: '/', icon: Search, current: location.pathname === '/' },
    { name: 'Graph', href: '/graph', icon: Network, current: location.pathname === '/graph' },
    { name: 'Upload', href: '/upload', icon: Upload, current: location.pathname === '/upload' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center space-x-4">
              <FileText className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">ForensiQ</h1>
                <p className="text-xs text-gray-500">UFDR Investigator Dashboard</p>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      item.current
                        ? 'text-blue-700 bg-blue-50'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </Link>
                )
              })}
            </nav>

            {/* Settings */}
            <button
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md"
              aria-label="Settings"
            >
              <Settings className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/detail/:id" element={<Detail />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/upload" element={<div className="text-center py-12">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">Upload UFDR File</h3>
            <p className="mt-1 text-sm text-gray-500">
              Feature coming soon. Use the CLI parser for now.
            </p>
          </div>} />
          <Route path="*" element={<div className="text-center py-12">
            <h2 className="text-2xl font-bold text-gray-900">Page Not Found</h2>
            <p className="mt-2 text-gray-600">The page you're looking for doesn't exist.</p>
            <Link to="/" className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-800">
              <Search className="h-4 w-4 mr-1" />
              Back to Search
            </Link>
          </div>} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center text-sm text-gray-500">
            <p>&copy; 2025 ForensiQ. Digital forensic investigation platform.</p>
            <div className="flex space-x-4">
              <span>Version 1.0.0</span>
              <a 
                href="https://github.com/Av7danger/ForensiQ" 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-gray-700"
              >
                GitHub
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
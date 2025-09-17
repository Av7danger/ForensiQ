# ForensiQ Frontend

A modern React + TypeScript web application for digital forensic investigation, specifically designed for analyzing UFDR (Universal Forensic Data Report) files.

## Features

### 🔍 **Search & Discovery**
- **Natural Language Search**: Search through messages, calls, and contacts using keywords
- **Entity Highlighting**: Automatically highlights people, organizations, locations, phones, emails, and dates
- **Advanced Filtering**: Filter results by type (messages, calls, contacts)
- **Hybrid Search**: Combines keyword matching with semantic similarity
- **Real-time Results**: Fast search with pagination and sorting

### 📊 **Data Visualization**
- **Interactive Network Graph**: Visualize relationships between contacts and communications
- **Multiple Layout Options**: Physics-based, hierarchical, and static layouts
- **Node Details**: Click on any node to see detailed information
- **Zoom & Pan Controls**: Full navigation of complex networks
- **Export Capabilities**: Save graphs as PNG images

### 📋 **Evidence Management**
- **Detailed Evidence View**: Complete metadata and content for each piece of evidence
- **Conversation Threading**: View complete message conversations with participants
- **Attachment Preview**: Access and download file attachments
- **Entity Extraction**: View extracted entities (people, places, organizations)
- **Raw Data Access**: Inspect original UFDR data for technical analysis

### 📤 **Export & Reporting**
- **Multiple Formats**: Export as PDF, HTML, or JSON
- **Custom Reports**: Generate investigator-friendly reports
- **Print Optimization**: Clean layouts for physical documentation
- **Batch Export**: Export multiple pieces of evidence at once

### 🎨 **User Experience**
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Accessibility**: Full keyboard navigation and screen reader support
- **Loading States**: Clear feedback during data processing
- **Error Handling**: Graceful degradation when services are unavailable
- **Offline Indicators**: Shows connection status

## Technology Stack

### Core Framework
- **React 18** with TypeScript for type safety
- **Vite** for fast development and building
- **Tailwind CSS** for responsive design

### State Management & Data
- **TanStack Query** (React Query) for server state management
- **React Router** for client-side routing
- **Axios** for API communication

### Visualization
- **vis-network** for interactive graph visualization
- **Lucide React** for consistent iconography

### Export & Utilities
- **html2pdf.js** for PDF generation
- **React Helmet** for document head management

## Prerequisites

Before running the frontend, ensure you have:

1. **Node.js 16+** installed
2. **npm or yarn** package manager
3. **Backend API** running (see backend README)
4. **Environment variables** configured

## Installation

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment** (create `.env.local`):
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   VITE_APP_TITLE=ForensiQ Investigator Dashboard
   VITE_APP_VERSION=1.0.0
   ```

4. **Start development server**:
   ```bash
   npm run dev
   ```

5. **Open in browser**:
   ```
   http://localhost:5173
   ```

## Available Scripts

### Development
- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally

### Code Quality
- `npm run lint` - Run ESLint for code quality
- `npm run lint:fix` - Auto-fix linting issues
- `npm run type-check` - Run TypeScript type checking

### Testing (if implemented)
- `npm run test` - Run unit tests
- `npm run test:coverage` - Run tests with coverage report

## Configuration

### Environment Variables

Create a `.env.local` file in the frontend directory:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=10000

# Application Info
VITE_APP_TITLE=ForensiQ Investigator Dashboard
VITE_APP_VERSION=1.0.0
VITE_APP_DESCRIPTION=Digital forensic investigation platform

# Feature Flags
VITE_ENABLE_GRAPH=true
VITE_ENABLE_EXPORT=true
VITE_ENABLE_DEBUG=false

# Graph Configuration
VITE_GRAPH_MAX_NODES=1000
VITE_GRAPH_PHYSICS_ENABLED=true

# Export Configuration
VITE_EXPORT_MAX_SIZE=50000
VITE_PDF_QUALITY=0.98
```

### API Endpoints

The frontend expects the following API endpoints:

```
GET  /api/search?q={query}&page={page}&per_page={limit}&type={type}
GET  /api/evidence/{id}
GET  /api/graph
GET  /api/attachments/{id}/download
POST /api/parse (for future upload feature)
```

## Project Structure

```
frontend/
├── public/
│   ├── vite.svg              # App icon
│   └── favicon.ico           # Browser favicon
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── EntityHighlighter.tsx
│   │   ├── ExportButton.tsx
│   │   ├── LoadingSpinner.tsx
│   │   ├── Pagination.tsx
│   │   └── SearchBar.tsx
│   ├── pages/               # Main application pages
│   │   ├── Dashboard.tsx    # Search and results
│   │   ├── Detail.tsx       # Evidence details
│   │   └── Graph.tsx        # Network visualization
│   ├── types/               # TypeScript type definitions
│   │   └── api.ts
│   ├── utils/               # Utility functions
│   │   ├── api.ts           # API client setup
│   │   ├── export.ts        # Export utilities
│   │   └── formatting.ts    # Data formatting helpers
│   ├── App.tsx              # Main application component
│   ├── index.tsx            # Application entry point
│   ├── index.css            # Global styles and Tailwind
│   └── vite-env.d.ts        # Vite type definitions
├── index.html               # HTML template
├── package.json             # Dependencies and scripts
├── tailwind.config.js       # Tailwind CSS configuration
├── tsconfig.json            # TypeScript configuration
├── tsconfig.node.json       # Node.js TypeScript config
├── vite.config.ts           # Vite build configuration
└── README.md                # This file
```

## API Integration

### Search API
```typescript
interface SearchResponse {
  results: SearchResult[]
  total: number
  page: number
  per_page: number
  query: string
  search_time: number
}
```

### Evidence API
```typescript
interface EvidenceDetail {
  id: string
  type: 'message' | 'call' | 'contact'
  content: string
  timestamp?: string
  contact?: string
  phone?: string
  direction?: 'inbound' | 'outbound' | 'sent' | 'received'
  entities?: { [key: string]: string[] }
  conversation?: Array<{
    id: string
    content: string
    timestamp: string
    direction: 'sent' | 'received'
  }>
  attachments?: Array<{
    id: string
    name: string
    type: string
    size: number
    path: string
  }>
  source: string
}
```

### Graph API
```typescript
interface GraphData {
  nodes: Array<{
    id: string
    label: string
    type: 'contact' | 'phone' | 'message_thread'
    value?: number
  }>
  edges: Array<{
    id: string
    from: string
    to: string
    label?: string
    value?: number
  }>
  stats: {
    total_contacts: number
    total_connections: number
    most_connected: string
    message_threads: number
  }
}
```

## Customization

### Theming
Modify `tailwind.config.js` to customize colors, fonts, and spacing:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        forensiq: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a'
        }
      }
    }
  }
}
```

### Entity Types
Add new entity types in `EntityHighlighter.tsx`:

```typescript
const entityColors = {
  person: 'bg-blue-100 text-blue-800',
  organization: 'bg-green-100 text-green-800',
  location: 'bg-purple-100 text-purple-800',
  // Add your custom types here
  custom_type: 'bg-red-100 text-red-800'
}
```

## Performance Optimization

### Bundle Size
- Tree shaking is enabled by default
- Use dynamic imports for large components
- Optimize images and assets

### Search Performance
- Debounced search input (300ms delay)
- Pagination to limit results
- Virtualized lists for large datasets

### Graph Performance
- Node limit configuration
- Physics engine optimization
- Efficient edge rendering

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Verify backend is running on port 8000
   - Check CORS configuration
   - Confirm environment variables

2. **Graph Not Rendering**
   - Ensure vis-network is properly installed
   - Check browser console for WebGL errors
   - Verify graph data format

3. **Export Not Working**
   - Check browser popup blocker
   - Verify html2pdf.js is loaded
   - Test with smaller datasets

4. **TypeScript Errors**
   - Run `npm run type-check`
   - Update type definitions
   - Check import statements

### Debug Mode

Enable debug mode in `.env.local`:
```env
VITE_ENABLE_DEBUG=true
```

This will:
- Show API request/response logs
- Display component re-render information
- Enable React Query DevTools

## Deployment

### Production Build

1. **Build the application**:
   ```bash
   npm run build
   ```

2. **Test production build**:
   ```bash
   npm run preview
   ```

3. **Deploy `dist/` folder** to your web server

### Environment-Specific Builds

Create environment-specific `.env` files:
- `.env.development` - Development settings
- `.env.staging` - Staging environment
- `.env.production` - Production settings

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]
```

## Contributing

1. Follow TypeScript best practices
2. Use Tailwind CSS for styling
3. Write meaningful commit messages
4. Test on multiple screen sizes
5. Ensure accessibility compliance

## Browser Support

- **Chrome 90+**
- **Firefox 88+**
- **Safari 14+**
- **Edge 90+**

## License

This project is part of the ForensiQ digital forensic investigation platform.

---

For backend setup and API documentation, see the main project README.
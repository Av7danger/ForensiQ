// TypeScript interfaces for ForensiQ API responses and data structures

// Core API Types
export interface QueryRequest {
  q: string;
  limit?: number;
  summarize?: boolean;
}

export interface QueryResponse {
  query: string;
  summary?: string;
  hits: Hit[];
  total_hits: number;
  sources_used: string[];
}

export interface Hit {
  message_id: string;
  case_id: string;
  snippet: string;
  sender?: string;
  recipient?: string;
  timestamp?: string;
  score: number;
  sources: string[];
  opensearch_score: number;
  faiss_score: number;
  entities?: Entities;
  attachments?: Attachment[];
}

export interface Entities {
  phones: string[];
  emails: string[];
  crypto_addresses: string[];
  urls: string[];
}

export interface Attachment {
  filename: string;
  file_type: string;
  size_bytes: number;
  sha256: string;
  thumbnail_url?: string;
  download_url?: string;
}

export interface MessageDetail {
  id: string;
  case_id: string;
  content: string;
  sender?: string;
  recipient?: string;
  timestamp?: string;
  entities?: Entities;
  attachments?: Attachment[];
  raw_source?: string;
  provenance: {
    case_id: string;
    source_file: string;
    sha256: string;
    extracted_at: string;
  };
}

// Case Management
export interface Case {
  id: string;
  case_id: string;
  investigator: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'closed' | 'pending';
  description?: string;
  metadata?: Record<string, any>;
  files_count?: number;
  messages_count?: number;
}

export interface UFDRFile {
  id: string;
  case_id: string;
  filename: string;
  file_hash: string;
  file_size: number;
  upload_path: string;
  processed_at?: string;
  processing_status: 'pending' | 'running' | 'completed' | 'failed';
  metadata?: Record<string, any>;
  created_at: string;
}

export interface ProcessingJob {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  metadata?: Record<string, any>;
}

// Network Visualization
export interface GraphNode {
  id: string;
  label: string;
  type: 'contact' | 'phone' | 'email' | 'file' | 'crypto' | 'person' | 'device';
  group: string;
  size?: number;
  color?: string;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  from: string;
  to: string;
  label?: string;
  type: 'message' | 'call' | 'file_transfer' | 'crypto_transaction';
  weight?: number;
  count?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics?: {
    total_nodes: number;
    total_edges: number;
    connected_components: number;
    density: number;
  };
}

// Upload and Processing
export interface UploadResponse {
  success: boolean;
  message: string;
  case_id?: string;
  files_processed?: number;
  job_id?: string;
  file_id?: string;
}

export interface ApiError {
  detail: string;
  status?: number;
}

// Enhanced Search and Filters
export interface SearchFilters {
  cryptoOnly: boolean;
  phoneOnly: boolean;
  emailOnly: boolean;
  urlOnly: boolean;
  dateRange?: {
    start: string;
    end: string;
  };
  messageTypes?: string[];
  senders?: string[];
  searchType?: 'keyword' | 'semantic' | 'hybrid';
}

export interface SearchRequest {
  query: string;
  case_id?: string;
  filters?: SearchFilters;
  limit?: number;
  offset?: number;
}

// Timeline and Analysis
export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: 'message' | 'call' | 'contact_add' | 'file_access';
  title: string;
  description: string;
  entities: string[];
  metadata?: Record<string, any>;
}

export interface AnalysisSummary {
  case_id: string;
  total_messages: number;
  total_calls: number;
  total_contacts: number;
  date_range: {
    start: string;
    end: string;
  };
  top_entities: Array<{
    type: string;
    value: string;
    frequency: number;
  }>;
  activity_patterns: Array<{
    hour: number;
    message_count: number;
    call_count: number;
  }>;
}

// Pagination
export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

// Dashboard State
export interface DashboardState {
  selectedCase: Case | null;
  activeTab: 'search' | 'timeline' | 'network' | 'analysis' | 'upload';
  filters: SearchFilters;
  searchQuery: string;
  searchResults: Hit[];
  isLoading: boolean;
  error: string | null;
}

// Component Props
export interface EntityHighlighterProps {
  text: string;
  entities?: Entities;
  className?: string;
}

export interface ResultsTableProps {
  hits: Hit[];
  pagination: PaginationState;
  onPaginationChange: (page: number) => void;
  onRowClick?: (hit: Hit) => void;
  isLoading?: boolean;
}

export interface SearchBarProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  isLoading?: boolean;
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
}

export interface ExportButtonProps {
  data: Hit[] | MessageDetail;
  filename?: string;
  title?: string;
  format?: 'pdf' | 'json' | 'csv';
}

export interface NetworkGraphProps {
  data: GraphData;
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
}

export interface TimelineProps {
  events: TimelineEvent[];
  onEventClick?: (event: TimelineEvent) => void;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface UploadFormProps {
  onUpload: (file: File, caseId: string, investigator: string) => Promise<void>;
  isUploading?: boolean;
  onProgress?: (progress: number) => void;
}

export interface CaseSelectProps {
  cases: Case[];
  selectedCase: Case | null;
  onCaseSelect: (case_: Case) => void;
  onNewCase: () => void;
}

export interface StatsCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<any>;
  change?: {
    value: number;
    type: 'increase' | 'decrease';
  };
  loading?: boolean;
}
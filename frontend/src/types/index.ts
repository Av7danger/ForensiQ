// TypeScript interfaces for ForensiQ API responses and data structures

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

export interface GraphNode {
  id: string;
  label: string;
  type: 'contact' | 'phone' | 'email' | 'file' | 'crypto';
  group: string;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  from: string;
  to: string;
  label?: string;
  type: 'message' | 'call' | 'file_transfer' | 'crypto_transaction';
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface UploadResponse {
  success: boolean;
  message: string;
  case_id?: string;
  files_processed?: number;
}

export interface ApiError {
  detail: string;
  status?: number;
}

// Filter types for search
export interface SearchFilters {
  cryptoOnly: boolean;
  phoneOnly: boolean;
  emailOnly: boolean;
  urlOnly: boolean;
  dateRange?: {
    start: string;
    end: string;
  };
}

// Pagination
export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

// Component props interfaces
export interface EntityHighlighterProps {
  text: string;
  entities?: Entities;
  className?: string;
}

export interface ResultsTableProps {
  hits: Hit[];
  pagination: PaginationState;
  onPaginationChange: (page: number) => void;
  isLoading?: boolean;
}

export interface SearchBarProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export interface ExportButtonProps {
  data: Hit[] | MessageDetail;
  filename?: string;
  title?: string;
}
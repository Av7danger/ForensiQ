import React from 'react';
import SearchBar from '../components/SearchBar';
import StatsCards from '../components/StatsCards';
import CaseSelector from '../components/CaseSelector';
import EntityNetwork from '../components/EntityNetwork';
import TimelineView from '../components/TimelineView';
import type { SearchFilters, Case, TimelineEvent, GraphData } from '../types';

const ComponentTest: React.FC = () => {
  // Mock data for testing
  const mockCases: Case[] = [
    {
      id: '1',
      case_id: 'CASE-2024-001',
      investigator: 'Detective Smith',
      created_at: '2024-01-15T10:30:00Z',
      updated_at: '2024-01-15T15:45:00Z',
      status: 'active',
      description: 'Cryptocurrency fraud investigation',
      files_count: 25,
      messages_count: 1240,
    },
    {
      id: '2',
      case_id: 'CASE-2024-002',
      investigator: 'Agent Johnson',
      created_at: '2024-01-10T09:15:00Z',
      updated_at: '2024-01-14T16:20:00Z',
      status: 'pending',
      description: 'Digital evidence analysis',
      files_count: 8,
      messages_count: 356,
    },
  ];

  const mockTimelineEvents: TimelineEvent[] = [
    {
      id: '1',
      timestamp: '2024-01-15T14:30:00Z',
      type: 'message',
      description: 'Suspicious message sent',
      details: 'Message containing crypto wallet address',
      source: 'WhatsApp',
    },
    {
      id: '2',
      timestamp: '2024-01-15T12:15:00Z',
      type: 'crypto_transaction',
      description: 'Bitcoin transaction detected',
      details: '0.5 BTC transferred to unknown wallet',
      source: 'Blockchain analysis',
    },
  ];

  const mockGraphData: GraphData = {
    nodes: [
      {
        id: '1',
        label: 'John Doe',
        type: 'person',
        group: 'suspects',
      },
      {
        id: '2',
        label: '+1234567890',
        type: 'phone',
        group: 'communications',
      },
    ],
    edges: [
      {
        from: '1',
        to: '2',
        type: 'message',
        label: 'sent message',
        weight: 5,
      },
    ],
    statistics: {
      total_nodes: 2,
      total_edges: 1,
      connected_components: 1,
      density: 0.5,
    },
  };

  const mockStats = {
    total_files: 33,
    total_size: 2147483648, // 2GB
    files_by_type: { 'pdf': 10, 'docx': 15, 'jpg': 8 },
    processing_progress: 85,
    entities_extracted: 142,
    timeline_events: 67,
    network_connections: 23,
  };

  const handleSearch = (query: string, filters: SearchFilters) => {
    console.log('Search:', query, filters);
  };

  const handleCaseSelect = (caseId: string) => {
    console.log('Selected case:', caseId);
  };

  const handleEventClick = (event: TimelineEvent) => {
    console.log('Event clicked:', event);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          ForensiQ Component Test
        </h1>

        {/* SearchBar Test */}
        <section className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Search Bar Component</h2>
          <SearchBar onSearch={handleSearch} />
        </section>

        {/* Stats Cards Test */}
        <section className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Statistics Cards</h2>
          <StatsCards stats={mockStats} />
        </section>

        {/* Case Selector Test */}
        <section className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Case Selector</h2>
          <CaseSelector
            cases={mockCases}
            selectedCase="CASE-2024-001"
            onCaseSelect={handleCaseSelect}
          />
        </section>

        {/* Entity Network Test */}
        <section className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Entity Network</h2>
          <EntityNetwork data={mockGraphData} height={400} />
        </section>

        {/* Timeline View Test */}
        <section className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Timeline View</h2>
          <TimelineView events={mockTimelineEvents} onEventClick={handleEventClick} />
        </section>
      </div>
    </div>
  );
};

export default ComponentTest;
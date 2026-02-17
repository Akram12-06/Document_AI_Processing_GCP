import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { FilterBar } from './components/FilterBar';
import { DocumentTable } from './components/DocumentTable';
import { UploadModal } from './components/UploadModal';
import { DocumentDetailModal } from './components/DocumentDetailModal';
import { api } from './utils/api';
import './styles/globals.css';
import './styles/components.css';
import './styles/utilities.css';
import './styles/layout.css';

function App() {
  // State management
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    file_name: '',
  });
  const [pagination, setPagination] = useState({
    limit: 50,
    offset: 0,
    total: 0,
  });

  // Modal states
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  // Load data when filters or pagination change
  useEffect(() => {
    loadDocuments();
  }, [filters, pagination.offset, pagination.limit]);

  const loadData = async () => {
    try {
      setLoading(true);
      console.log('Loading stats...'); // Debug log
      const [statsData] = await Promise.all([
        api.getStats(),
      ]);
      console.log('Stats loaded:', statsData); // Debug log
      setStats(statsData);
      await loadDocuments();
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      // Use the regular documents endpoint since table endpoint may not be deployed
      const documentsData = await api.getDocuments({
        ...filters,
        limit: pagination.limit,
        offset: pagination.offset,
      });
      console.log('Documents loaded:', documentsData); // Debug log
      setDocuments(documentsData);
      // Note: API doesn't return total count, so we'll estimate based on results
      setPagination(prev => ({
        ...prev,
        total: documentsData.length === prev.limit ? prev.offset + prev.limit + 1 : prev.offset + documentsData.length
      }));
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocuments([]);
    }
  };

  const handleFiltersChange = (newFilters) => {
    setFilters(newFilters);
    setPagination(prev => ({ ...prev, offset: 0 }));
  };

  const handlePageChange = (newOffset) => {
    setPagination(prev => ({ ...prev, offset: newOffset }));
  };

  const handleUpload = async (files) => {
    try {
      const result = await api.uploadFiles(files);
      // Refresh stats and documents after upload
      if (result.success || (result.uploaded_files && result.uploaded_files.length > 0)) {
        await loadData();
      }
      return result;
    } catch (error) {
      throw error;
    }
  };

  const handleTriggerProcessing = async () => {
    try {
      await api.triggerProcessing();
      // Show success message or refresh data
      console.log('Processing triggered successfully');
    } catch (error) {
      console.error('Failed to trigger processing:', error);
      throw error;
    }
  };

  const handleViewDetails = (document) => {
    setSelectedDocument(document);
    setDetailModalOpen(true);
  };

  const handleViewPDF = (document) => {
    window.open(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/documents/${document.id}/pdf`, '_blank');
  };

  const handleViewRaw = async (document) => {
    try {
      const rawData = await api.getDocumentRaw(document.id);
      const blob = new Blob([JSON.stringify(rawData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${document.file_name}_raw_data.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download raw data:', error);
    }
  };

  return (
    <div className="app min-h-screen bg-primary">
      {/* Header */}
      <Header
        onUpload={() => setUploadModalOpen(true)}
        onTriggerProcessing={handleTriggerProcessing}
      />

      {/* Main Content */}
      <main className="main-content">
        <div className="container py-lg">
          {/* Dashboard Stats */}
          <Dashboard stats={stats} loading={loading} />

          {/* Filters */}
          <FilterBar
            filters={filters}
            onFiltersChange={handleFiltersChange}
            onClear={() => handleFiltersChange({
              file_name: '',
            })}
          />

          {/* Documents Table */}
          <DocumentTable
            documents={documents}
            loading={loading}
            onViewDetails={handleViewDetails}
            onViewPDF={handleViewPDF}
            onViewRaw={handleViewRaw}
            pagination={pagination}
            onPageChange={handlePageChange}
          />
        </div>
      </main>

      {/* Modals */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUpload={handleUpload}
      />

      <DocumentDetailModal
        isOpen={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        document={selectedDocument}
        onViewRaw={handleViewRaw}
      />
    </div>
  );
}

export default App;

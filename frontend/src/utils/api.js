// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// API Client Class
class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = { ...options };
    // Set headers conditionally: do not set Content-Type for FormData
    const isFormData = options?.body instanceof FormData;
    const defaultHeaders = isFormData ? {} : { 'Content-Type': 'application/json' };
    config.headers = { ...defaultHeaders, ...(options.headers || {}) };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Handle different response types
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        return await response.json();
      } else if (contentType?.includes('application/pdf')) {
        return await response.blob();
      } else {
        return await response.text();
      }
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    return this.request('/api/health');
  }

  // Get processing statistics
  async getStats() {
    return this.request('/api/documents/stats');
  }

  // Get documents with optional filters
  async getDocuments(filters = {}) {
    const queryParams = new URLSearchParams();
    
    if (filters.file_name) queryParams.append('file_name', filters.file_name);
    if (filters.po_number) queryParams.append('po_number', filters.po_number);
    if (filters.supplier_name) queryParams.append('supplier_name', filters.supplier_name);
    if (filters.document_status) queryParams.append('document_status', filters.document_status);
    if (filters.status) queryParams.append('document_status', filters.status); // Support both for compatibility
    if (filters.limit) queryParams.append('limit', filters.limit);
    if (filters.offset) queryParams.append('offset', filters.offset);

    const endpoint = `/api/documents${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return this.request(endpoint);
  }

  // Get document details
  async getDocument(id) {
    return this.request(`/api/documents/${id}`);
  }

  // Get document PDF
  async getDocumentPDF(id) {
    return this.request(`/api/documents/${id}/pdf`);
  }

  // Get document raw output
  async getDocumentRaw(id) {
    return this.request(`/api/documents/${id}/raw`);
  }

  // Upload files
  async uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const resp = await this.request('/api/upload', {
      method: 'POST',
      headers: {}, // Let browser set boundary for FormData
      body: formData,
    });

    // Normalize response to a consistent shape for the UI
    // Support both legacy {success, message, uploaded_files: [names], failed_files: [errs]}
    // and newer {uploaded_files: [{file_name,...}], ...}
    const uploaded = Array.isArray(resp?.uploaded_files)
      ? resp.uploaded_files.map(f => (typeof f === 'string' ? f : (f.file_name || f)))
      : [];
    const failed = Array.isArray(resp?.failed_files)
      ? resp.failed_files.map(f => (typeof f === 'string' ? f : (f.file_name || f)))
      : [];

    const normalized = {
      success: resp?.success !== undefined ? !!resp.success : uploaded.length > 0 && failed.length === 0,
      message: resp?.message || `Uploaded ${uploaded.length} file(s), ${failed.length} failed`,
      uploaded_files: uploaded,
      failed_files: failed,
      raw: resp,
    };

    return normalized;
  }

  // Trigger processing
  async triggerProcessing() {
    return this.request('/api/trigger-processing', {
      method: 'POST',
    });
  }

  // Get processing status
  async getProcessingStatus() {
    return this.request('/api/processing/status');
  }
}

// Create and export API instance
export const api = new ApiClient();

// Export individual methods for convenience
export const {
  healthCheck,
  getStats,
  getDocuments,
  getDocumentsTable,
  getDocument,
  getDocumentPDF,
  getDocumentRaw,
  uploadFiles,
  triggerProcessing,
  getProcessingStatus,
} = api;
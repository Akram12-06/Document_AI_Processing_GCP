
//src/components/DocumentDetailModal.jsx

import { useState, useEffect } from 'react';
import { Modal, Button, StatusBadge, LoadingSpinner } from './UI';
import {
  AlertTriangle,
  XCircle,
  ClipboardList,
  BarChart3,
  Search,
  ChevronDown,
  ChevronRight,
  DownloadIcon
} from 'lucide-react'

export function DocumentDetailModal({ 
  isOpen, 
  onClose, 
  document,
  onViewRaw 
}) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    keyInfo: true,
    processingInfo: false,
    allEntities: false
  });

  useEffect(() => {
    if (isOpen && document) {
      fetchDocumentDetails();
    }
  }, [isOpen, document]);

  const fetchDocumentDetails = async () => {
    if (!document?.id) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/documents/${document.id}`);
      const data = await response.json();
      setDetails(data);
    } catch (error) {
      console.error('Failed to fetch document details:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getEntityValue = (entities, entityName) => {
    const entity = entities?.find(e => e.entity_name === entityName);
    return entity?.entity_value || '-';
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const groupedEntities = details?.entities?.reduce((acc, entity) => {
    if (!acc[entity.entity_name]) {
      acc[entity.entity_name] = [];
    }
    acc[entity.entity_name].push(entity);
    return acc;
  }, {}) || {};

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Document: ${document?.file_name || 'Unknown'}`}
      size="xl"
    >
      {loading ? (
        <div className="flex items-center justify-center p-xl">
          <LoadingSpinner size="lg" />
          <span className="text-muted ml-md">Loading document...</span>
        </div>
      ) : details ? (
        <div className="document-detail-layout" style={{ display: 'flex', height: '80vh', gap: 'var(--space-md)' }}>
          {/* PDF Viewer - Left Side */}
          <div className="pdf-container" style={{ flex: '1', minWidth: '50%' }}>
            <div className="pdf-viewer bg-surface rounded-lg p-md" style={{ height: '100%' }}>
              <iframe
                src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/documents/${details.id}/pdf`}
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  borderRadius: 'var(--radius-md)'
                }}
                title={`PDF: ${details.file_name}`}
              />
            </div>
          </div>

          {/* Information Panel - Right Side */}
          <div className="info-container" style={{ flex: '0 0 450px', display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Document Header */}
            <div className="detail-header bg-surface rounded-lg p-md mb-md">
              <div className="flex items-center justify-between mb-sm">
                <StatusBadge status={details.document_status || details.processing_status} />
                <span className="text-xs text-muted">ID: #{details.id}</span>
              </div>
              {details.document_status && details.document_status !== details.processing_status && (
                <div className="mb-sm">
                  <span className="text-xs text-muted">Processing: </span>
                  <StatusBadge status={details.processing_status} size="sm" />
                </div>
              )}
              <p className="text-xs text-muted mb-sm">
                Processed: {formatDateTime(details.created_at)}
              </p>
              {details.error_message && (
                <div className="p-sm bg-warning/10 border border-warning/20 rounded text-xs text-warning">
                  <AlertTriangle size={14}/>{details.error_message}
                </div>
              )}
              {details.document_status === 'FAILED' && details.exception_reason_description && (
                <div className="p-sm bg-error/10 border border-error/20 rounded text-xs text-error mt-sm">
                   <XCircle size={14}/>{details.exception_reason_code}: {details.exception_reason_description}
                </div>
              )}
            </div>

            {/* Collapsible Sections */}
            <div className="info-sections" style={{ flex: '1', overflowY: 'auto', paddingRight: 'var(--space-sm)' }}>
              {/* Key Information */}
              <div className="section bg-surface rounded-lg mb-md">
                <button
                  className="section-header w-full flex items-center justify-between p-md text-left hover:bg-hover transition"
                  onClick={() => toggleSection('keyInfo')}
                >
                  <h4 className="font-medium text-primary flex items-center gap-sm">
                    <ClipboardList size={16}/>
                    Key Information
                  </h4>
                  <span className="text-muted">
                    {expandedSections.keyInfo ? <ChevronDown size={16}/> : <ChevronRight size={16}/>}
                  </span>
                </button>
                
                {expandedSections.keyInfo && (
                  <div className="section-content p-md border-t border-primary">
                    <div className="space-y-sm text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted">PO Number:</span>
                        <span className="text-primary font-mono">
                          {getEntityValue(details.entities, 'po_number')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Supplier:</span>
                        <span className="text-primary">
                          {getEntityValue(details.entities, 'vendor_name')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Invoice Number:</span>
                        <span className="text-primary font-mono">
                          {getEntityValue(details.entities, 'invoice_number')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Invoice Date:</span>
                        <span className="text-primary">
                          {getEntityValue(details.entities, 'invoice_date')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Total Amount:</span>
                        <span className="text-primary font-mono font-bold">
                          {getEntityValue(details.entities, 'invoice_total_amount')}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Processing Information */}
              <div className="section bg-surface rounded-lg mb-md">
                <button
                  className="section-header w-full flex items-center justify-between p-md text-left hover:bg-hover transition"
                  onClick={() => toggleSection('processingInfo')}
                >
                  <h4 className="font-medium text-primary flex items-center gap-sm">
                    <BarChart3 size={16}/>
                    Processing Info
                  </h4>
                  <span className="text-muted">
                    {expandedSections.processingInfo ? <ChevronDown size={16}/> : <ChevronRight size={16}/>}
                  </span>
                </button>
                
                {expandedSections.processingInfo && (
                  <div className="section-content p-md border-t border-primary">
                    <div className="space-y-sm text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted">Document Status:</span>
                        <StatusBadge status={details.document_status || details.processing_status} size="sm" />
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Processing Status:</span>
                        <StatusBadge status={details.processing_status} size="sm" />
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Min Confidence:</span>
                        <span className="text-primary font-bold">{details.min_confidence ? `${Math.round(details.min_confidence * 100)}%` : 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Total Entities:</span>
                        <span className="text-primary font-bold">{details.total_entities}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">Has Raw Data:</span>
                        <span className={details.has_raw_output ? 'text-success' : 'text-error'}>
                          {details.has_raw_output ? 'Yes' : ' No'}
                        </span>
                      </div>
                      {details.exception_reason_code && (
                        <div className="flex justify-between">
                          <span className="text-muted">Exception Code:</span>
                          <span className="text-error font-mono text-xs">{details.exception_reason_code}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-muted">GCS Path:</span>
                        <span className="text-muted text-xs break-all">
                          {details.gcs_path.split('/').pop()}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* All Entities */}
              <div className="section bg-surface rounded-lg">
                <button
                  className="section-header w-full flex items-center justify-between p-md text-left hover:bg-hover transition"
                  onClick={() => toggleSection('allEntities')}
                >
                  <h4 className="font-medium text-primary flex items-center gap-sm">
                    <Search size={16}/>
                    All Entities ({Object.keys(groupedEntities).length})
                  </h4>
                  <span className="text-muted">
                    {expandedSections.allEntities ? <ChevronDown size={16}/> : <ChevronRight size={16}/>}
                  </span>
                </button>
                
                {expandedSections.allEntities && (
                  <div className="section-content p-md border-t border-primary" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    <div className="space-y-md text-xs">
                      {Object.entries(groupedEntities).map(([entityName, entities]) => (
                        <div key={entityName} className="entity-group border border-primary rounded p-sm">
                          <div className="entity-name font-medium text-primary mb-sm capitalize">
                            {entityName.replace(/_/g, ' ')}
                          </div>
                          {entities.map((entity, index) => (
                            <div key={index} className="entity-value mb-xs">
                              <div className="text-secondary">{entity.entity_value}</div>
                              <div className="text-muted">
                                Conf: {entity.confidence ? `${Math.round(parseFloat(entity.confidence) * 100)}%` : 'N/A'}
                                {entity.page_number !== null && entity.page_number !== undefined && ` • Page ${entity.page_number}`}
                              </div>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center p-xl text-muted">
          No document details available
        </div>
      )}

      {/* Footer */}
      <div className="modal-footer">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        {details?.has_raw_output && (
          <Button
            variant="secondary"
            icon={<DownloadIcon size={16}/>}
            onClick={() => onViewRaw(details)}
          >
            Download Raw Data
          </Button>
        )}
      </div>
    </Modal>
  );
}
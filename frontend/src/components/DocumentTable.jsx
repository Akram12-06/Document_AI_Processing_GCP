//src/components/DocumentTable.jsx

import { useState } from 'react';
import { StatusBadge, Button, EmptyState, LoadingSpinner } from './UI';
import {
  FileText,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  HelpCircle,
  Eye,
  ExternalLink
} from 'lucide-react';

export function DocumentTable({ 
  documents, 
  loading = false,
  onViewDetails,
  onViewPDF,
  onViewRaw,
  pagination,
  onPageChange
}) {
  const [sortField, setSortField] = useState('id');
  const [sortDirection, setSortDirection] = useState('desc');

  const handleSort = (field) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSortIcon = (field) => {
    if (field !== sortField) return <ArrowUpDown size={14}/> ;
    return sortDirection === 'asc' ? <ArrowUp size={14}/> : <ArrowDown size={14}/>;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatConfidence = (confidence) => {
    if (confidence == null) return '-';
    return `${(confidence * 100).toFixed(1)}%`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS': return 'text-green-400';
      case 'FAILED': return 'text-red-400';
      case 'PENDING': return 'text-blue-400';
      case 'PENDING_REVIEW': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS': return {icon: CheckCircle2, className: 'status-success'};
      case 'FAILED': return {icon: XCircle, className: 'status-failed'};
      case 'PENDING': return {icon: Clock, className: 'status-pending'};
      case 'PENDING_REVIEW': return {icon: AlertTriangle, className: 'status-warning'};
      default: return {icon: HelpCircle, className: 'status-unknown'};
    }
  };

  if (loading) {
    return (
      <div className="table-container">
        <div className="flex items-center justify-center p-xl">
          <LoadingSpinner size="lg" />
          <span className="text-muted ml-md">Loading documents...</span>
        </div>
      </div>
    );
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="table-container">
        <EmptyState
          icon={<FileText size={48}/>}
          title="No documents found"
          description="No documents match your current filters. Try adjusting your search criteria or upload new documents."
        />
      </div>
    );
  }

  return (
    <div className="table-container">
      <div className="table-wrapper" style={{ overflowX: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th 
                className="cursor-pointer hover:bg-hover"
                onClick={() => handleSort('id')}
              >
                Unique ID {getSortIcon('id')}
              </th>
              <th 
                className="cursor-pointer hover:bg-hover"
                onClick={() => handleSort('file_name')}
              >
                File Name {getSortIcon('file_name')}
              </th>
              <th>Invoice Type</th>
              <th 
                className="cursor-pointer hover:bg-hover"
                onClick={() => handleSort('date_received')}
              >
                Date Received {getSortIcon('date_received')}
              </th>
              <th 
                className="cursor-pointer hover:bg-hover"
                onClick={() => handleSort('document_status')}
              >
                Status {getSortIcon('document_status')}
              </th>
              <th 
                className="cursor-pointer hover:bg-hover"
                onClick={() => handleSort('min_confidence')}
              >
                Min Confidence {getSortIcon('min_confidence')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id} className="hover:bg-hover/50 transition-colors">
                <td className="font-mono text-accent">
                  #{document.id}
                </td>
                <td className="font-medium">
                  <div className="flex items-center gap-sm">
                    <FileText size={16} className='text-muted'/>
                    <span className="text-primary">{document.file_name}</span>
                  </div>
                  {document.error_message && (
                    <div className="text-xs text-red-400 mt-xs">
                      <AlertTriangle size={12}/>{document.error_message}
                    </div>
                  )}
                </td>
                <td>
                  <span className="text-gray-300">
                    {document.invoice_type || 'N/A'}
                  </span>
                </td>
                <td className="text-muted">
                  {formatDateTime(document.date_received)}
                </td>
                <td>
                 {(()=>{
                  const {icon: StatusIcon, className} =
                  getStatusIcon(document.document_status);
                  return(
                    <span className= {`status-chip ${className}`}>
                      <StatusIcon size={16} strokeWidth={1.5}/>
                      <span>
                        {document.document_status}
                      </span>
                    </span>
                  );
                 })()}
                </td>
                <td>
                  <span className={`font-medium ${
                    document.min_confidence >= 0.8 ? 'text-green-400' : 
                    document.min_confidence >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {formatConfidence(document.min_confidence)}
                  </span>
                </td>
                <td>
                  <div className="flex gap-xs">
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={<Eye size={14}/>}
                      onClick={() => onViewDetails(document)}
                      title="View Details"
                      className="hover:bg-accent/20"
                    >
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={<ExternalLink size={14}/>}
                      onClick={() => onViewPDF(document)}
                      title="View PDF"
                      className="hover:bg-blue-500/20"

                    >
                    </Button>
                    {/* <Button
                      variant="secondary"
                      size="sm"
                      icon="📊"
                      onClick={() => onViewRaw(document)}
                      title="Raw Data"
                      className="hover:bg-green-500/20"
                    >
                    </Button> */}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {pagination && (
        <div className="pagination-container p-md border-t border-primary">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted">
              Showing {pagination.offset + 1} to {Math.min(pagination.offset + pagination.limit, pagination.total)} of {pagination.total} documents
            </div>
            <div className="flex gap-sm">
              <Button
                variant="secondary"
                size="sm"
                disabled={pagination.offset === 0}
                onClick={() => onPageChange(Math.max(0, pagination.offset - pagination.limit))}
              >
                Previous
              </Button>
              <span className="px-md py-sm text-sm">
                Page {Math.floor(pagination.offset / pagination.limit) + 1} of {Math.ceil(pagination.total / pagination.limit)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={pagination.offset + pagination.limit >= pagination.total}
                onClick={() => onPageChange(pagination.offset + pagination.limit)}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
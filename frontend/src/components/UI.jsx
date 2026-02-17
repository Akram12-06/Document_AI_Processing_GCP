import { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertTriangle,
  FileText
} from 'lucide-react';

// StatusBadge Component
export function StatusBadge({ status, children, size = 'md' }) {
  const getStatusClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'success':
        return 'success';
      case 'failed':
      case 'failure':
        return 'error';
      case 'processing':
        return 'processing';
      case 'pending_review':
        return 'warning';
      case 'warning':
        return 'warning';
      default:
        return 'processing';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'success':
        return <CheckCircle2 size={14}/>;
      case 'failed':
      case 'failure':
        return <XCircle size={14}/>;
      case 'processing':
        return <RefreshCw size={14}/>;
      case 'pending_review':
        return <AlertTriangle size={14}/>;
      case 'warning':
        return <AlertTriangle size={14}/>;
      default:
        return <FileText size={14}/>;
    }
  };

  return (
    <span className={`status-badge ${getStatusClass(status)} ${size !== 'md' ? `status-badge-${size}` : ''}`}>
      <span>{getStatusIcon(status)}</span>
      {children || status}
    </span>
  );
}

// Button Component
export function Button({ 
  children, 
  onClick, 
  variant = 'primary', 
  size = 'md', 
  disabled = false, 
  loading = false,
  icon,
  ...props 
}) {
  return (
    <button
      className={`btn btn-${variant} btn-${size}`}
      onClick={onClick}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="spinner" />
      ) : icon ? (
        <span>{icon}</span>
      ) : null}
      {children}
    </button>
  );
}

// Input Component
export function Input({ 
  label, 
  error, 
  className = '', 
  ...props 
}) {
  return (
    <div className={`input-group ${className}`}>
      {label && (
        <label className="input-label text-secondary">
          {label}
        </label>
      )}
      <input className="input" {...props} />
      {error && (
        <span className="input-error text-error">
          {error}
        </span>
      )}
    </div>
  );
}

// Select Component
export function Select({ 
  label, 
  options = [], 
  value, 
  onChange, 
  placeholder = "Select...",
  className = '',
  ...props 
}) {
  return (
    <div className={`select-group ${className}`}>
      {label && (
        <label className="select-label text-secondary">
          {label}
        </label>
      )}
      <select 
        className="select" 
        value={value} 
        onChange={(e) => onChange?.(e.target.value)}
        {...props}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option 
            key={option.value} 
            value={option.value}
          >
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Card Component
export function Card({ 
  title, 
  description, 
  children, 
  className = '',
  onClick,
  ...props 
}) {
  return (
    <div 
      className={`card ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
      {...props}
    >
      {(title || description) && (
        <div className="card-header">
          {title && <h3 className="card-title">{title}</h3>}
          {description && <p className="card-description">{description}</p>}
        </div>
      )}
      {children}
    </div>
  );
}

// StatsCard Component
export function StatsCard({ 
  icon, 
  value, 
  label, 
  color = 'accent',
  className = '',
  ...props 
}) {
  return (
    <div className={`stats-card ${className}`} {...props}>
      {icon && (
        <div className={`stats-icon text-${color}`}>
          {icon}
        </div>
      )}
      <div className="stats-value">
        {value?.toLocaleString() || 0}
      </div>
      <div className="stats-label">
        {label}
      </div>
    </div>
  );
}

// Modal Component
export function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  size = 'md',
  ...props 
}) {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
    xl: 'max-w-6xl',
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className={`modal-content ${sizeClasses[size]}`}
        onClick={(e) => e.stopPropagation()}
        {...props}
      >
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button 
            className="modal-close"
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  );
}

// Loading Spinner Component
export function LoadingSpinner({ size = 'md', className = '' }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    
  };

  return (
    <div className={`spinner ${sizeClasses[size]} ${className}`} />
  );
}

// Empty State Component
export function EmptyState({ 
  icon = <FileText size={48}/>, 
  title = 'No data found', 
  description,
  action,
  className = '' 
}) {
  return (
    <div className={`empty-state text-center p-lg ${className}`}>
      <div className="empty-icon text-6xl mb-lg">{icon}</div>
      <h3 className="empty-title text-primary text-xl mb-sm">{title}</h3>
      {description && (
        <p className="empty-description text-muted mb-lg">{description}</p>
      )}
      {action}
    </div>
  );
}

// Error Boundary Component
export function ErrorBoundary({ children, fallback }) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const handleError = () => {
      setHasError(true);
    };

    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);

  if (hasError) {
    return fallback || (
      <div className="error-boundary p-lg text-center">
        <h2 className="text-error text-xl mb-md">Something went wrong</h2>
        <p className="text-muted mb-lg">Please refresh the page and try again.</p>
        <Button onClick={() => window.location.reload()}>
          Refresh Page
        </Button>
      </div>
    );
  }

  return children;
}
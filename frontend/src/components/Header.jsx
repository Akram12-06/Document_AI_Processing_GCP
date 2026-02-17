//src/components/Header.jsx
import { useState, useEffect} from 'react';
import { Button } from './UI';
import {
  BrainIcon,
  LayoutDashboard,
  UploadIcon,
  PlayCircle

} from 'lucide-react';

export function Header({ onUpload, onTriggerProcessing, currentView = 'dashboard', onNavigate = () => {} }) {
  const [isProcessing, setIsProcessing] = useState(false);
   const [showTooltip, setShowTooltip] = useState(false);

  const handleTriggerProcessing = async () => {
    setIsProcessing(true);
    setShowTooltip(true);
    try {
      await onTriggerProcessing([]);
    } catch (error) {
      console.error('Processing trigger failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const isUploadView = currentView === 'upload';
  const isDashboardView = currentView === 'dashboard';
  const isDocumentView = currentView === 'document-view';
  useEffect(() => {
  if (isProcessing) {
    const timer = setTimeout(() => {setShowTooltip(false);}, 15000);
    return () => clearTimeout(timer);
  }
}, [showTooltip]);

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo">
          <span className="text-2xl cursor-pointer" onClick={() => onNavigate('dashboard')}><BrainIcon size={20}/></span>
          <span 
            className="cursor-pointer hover:text-accent transition-colors"
            onClick={() => onNavigate('dashboard')}
          >
          Document AI Processor
          </span>
        </div>

        <nav className="header-nav">
          <button
            onClick={() => onNavigate('dashboard')}
            className={`nav-link ${isDashboardView ? 'nav-link-active' : ''}`}
            disabled={!onNavigate}
          >
            <LayoutDashboard size={16}/>Dashboard
          </button>
          {/* <button
            onClick={() => onUpload()}
            className={`nav-link ${isUploadView ? 'nav-link-active' : ''}`}
          >
            <Upload size={14}/>Upload
          </button> */}
        </nav>
        
        <div className="header-actions">
          {isDashboardView && (
            <Button
              variant="secondary"
              onClick={onUpload}
            >
              <UploadIcon size={14}/>
              Upload Files
            </Button>
          )}
          {/* {!isDocumentView && (
            
            <Button
              variant="primary"
              loading={isProcessing}
              onClick={handleTriggerProcessing}
              title={isProcessing ? 'Processing in progress...' : 'Start document processing'}
            >
              <PlayCircle size={14}/>
              {isProcessing ? 'Processing...' : 'Trigger Job'}
            </Button>

            
          )} */}
          {!isDocumentView && (
  <div className="processing-wrapper">
    <Button
      variant="primary"
      loading={isProcessing}
      onClick={handleTriggerProcessing}
    >
      <PlayCircle size={14}/>
      {isProcessing ? 'Processing...' : 'Trigger Job'}
    </Button>

    {showTooltip && (
      <div className="processing-tooltip">
        Processing can take ~5 minutes.  
        Please don’t refresh the page.
      </div>
    )}
  </div>
)}
        </div>
      </div>
    </header>
  );
}
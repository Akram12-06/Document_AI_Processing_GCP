import { useState } from 'react';
import { Button } from './UI';

export function Header({ onUpload, onTriggerProcessing }) {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleTriggerProcessing = async () => {
    setIsProcessing(true);
    try {
      await onTriggerProcessing();
    } catch (error) {
      console.error('Processing trigger failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo">
          <span className="text-2xl">�</span>
          <span>DocumentAI Processing Dashboard</span>
        </div>
        
        <div className="header-actions">
          <Button
            variant="secondary"
            icon="�"
            onClick={onUpload}
          >
            Upload Files
          </Button>
          <Button
            variant="primary"
            icon="⚡"
            loading={isProcessing}
            onClick={handleTriggerProcessing}
          >
            {isProcessing ? 'Processing...' : 'Trigger Processing'}
          </Button>
        </div>
      </div>
    </header>
  );
}
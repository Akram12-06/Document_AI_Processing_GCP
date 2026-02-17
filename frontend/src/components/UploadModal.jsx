import { useState, useCallback, useRef } from 'react';
import { Modal, Button, LoadingSpinner } from './UI';
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  XCircle,
  Check,
  X
} from 'lucide-react'

export function UploadModal({ 
  isOpen, 
  onClose, 
  onUpload 
}) {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    );
    setFiles(droppedFiles);
  }, []);

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files).filter(
      file => file.type === 'application/pdf'
    );
    setFiles(selectedFiles);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setUploadResult(null);

    try {
      const result = await onUpload(files);
      setUploadResult(result);
      
      if (result.success) {
        // Clear files on successful upload
        setTimeout(() => {
          setFiles([]);
          setUploadResult(null);
          onClose();
        }, 2000);
      }
    } catch (error) {
      setUploadResult({
        success: false,
        message: 'Upload failed: ' + error.message,
        uploaded_files: [],
        failed_files: files.map(f => f.name)
      });
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFiles([]);
      setUploadResult(null);
      onClose();
    }
  };

  const formatFileSize = (bytes) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Documents"
      size='xl'
    >
      <div className="upload-modal">
        {!uploadResult ? (
          <>
            {/* Drop Zone */}
            <div
              className={`upload-dropzone border-2 border-dashed rounded-lg p-xl mb-lg text-center transition ${
                isDragging 
                  ? 'border-accent bg-accent/10' 
                  : 'border-primary hover:border-secondary'
              } flex flex-col items-center justify-center`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="upload-icon mb-md flex justify-center text-accent"><Upload size={56}/></div>
              <h3 className="text-lg font-medium text-primary mb-sm">
                Drag & drop PDF files here
              </h3>
              <p className="text-muted mb-lg">
                or click to browse
              </p>
              <div className="upload-info text-sm text-muted">
                <p>Supported: PDF files only</p>
                <p>Max size: 10MB per file</p>
              </div>
              <input
                type="file"
                multiple
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
                ref={fileInputRef}
              />
              <Button
                variant="secondary"
                className="mt-lg"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Browse Files
              </Button>
            </div>

            {/* Selected Files */}
            {files.length > 0 && (
              <div className="selected-files">
                <h4 className="text-md font-medium text-primary mb-md">
                  Selected Files ({files.length})
                </h4>
                <div className="files-list space-y-sm max-h-48 overflow-y-auto">
                  {files.map((file, index) => (
                    <div
                      key={index}
                      className="file-item flex items-center justify-between bg-surface rounded-lg p-md"
                    >
                      <div className="file-info flex items-center gap-md">
                        <span className="file-icon text-secondary"><FileText size={18}/></span>
                        <div>
                          <div className="file-name text-primary font-medium">
                            {file.name}
                          </div>
                          <div className="file-size text-xs text-muted">
                            {formatFileSize(file.size)}
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={<Trash2 size={14}/>}
                        onClick={() => removeFile(index)}
                        className="text-error hover:bg-error/20"
                      >
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          /* Upload Result */
          <div className="upload-result">
            <div className={`result-icon text-6xl mb-lg text-center ${
              uploadResult.success ? 'text-success' : 'text-error'
            }`}>
              {uploadResult.success ? <CheckCircle2 size={56}/> : <XCircle size={56}/>}
            </div>
            
            <h3 className={`text-lg font-medium mb-md text-center ${
              uploadResult.success ? 'text-success' : 'text-error'
            }`}>
              {uploadResult.success ? 'Upload Successful!' : 'Upload Failed'}
            </h3>
            
            <p className="text-center text-muted mb-lg">
              {uploadResult.message}
            </p>

            {uploadResult.uploaded_files?.length > 0 && (
              <div className="uploaded-files mb-lg">
                <h4 className="text-success font-medium mb-sm">
                  Successfully uploaded ({uploadResult.uploaded_files.length}):
                </h4>
                <ul className="space-y-xs">
                  {uploadResult.uploaded_files.map((fileName, index) => (
                    <li key={index} className="text-sm text-muted flex items-center gap-sm">
                      <span className="text-success">
                        <Check size={14}/>
                      </span>
                      {fileName}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {uploadResult.failed_files?.length > 0 && (
              <div className="failed-files mb-lg">
                <h4 className="text-error font-medium mb-sm">
                  Failed uploads ({uploadResult.failed_files.length}):
                </h4>
                <ul className="space-y-xs">
                  {uploadResult.failed_files.map((fileName, index) => (
                    <li key={index} className="text-sm text-muted flex items-center gap-sm">
                      <span className="text-error">
                        <X size={14}/>
                      </span>
                      {fileName}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="modal-footer">
          <Button
            variant="secondary"
            onClick={handleClose}
            disabled={uploading}
          >
            {uploadResult ? 'Close' : 'Cancel'}
          </Button>
          {!uploadResult && (
            <Button
              variant="primary"
              onClick={handleUpload}
              disabled={files.length === 0 || uploading}
              loading={uploading}
            >
              {uploading ? 'Uploading...' : `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
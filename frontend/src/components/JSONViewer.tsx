import React, { useState } from 'react';
import type { ScrapeResult } from '../types';

interface JSONViewerProps {
  rawData: ScrapeResult;
  djangoData: Record<string, any> | null;
  market?: string | null;
  schema?: string | null;
  initialTab?: 'raw' | 'django';
  onClose: () => void;
  onDownloadRaw: () => void;
  onDownloadDjango: () => void;
}

export const JSONViewer: React.FC<JSONViewerProps> = ({
  rawData,
  djangoData,
  market,
  schema,
  initialTab = 'django',
  onClose,
  onDownloadRaw,
  onDownloadDjango,
}) => {
  const [activeTab, setActiveTab] = useState<'raw' | 'django'>(djangoData ? initialTab : 'raw');
  const [copied, setCopied] = useState(false);

  const rawJsonString = JSON.stringify(rawData, null, 2);
  const djangoJsonString = djangoData
    ? JSON.stringify(djangoData, null, 2)
    : 'Django JSON not yet generated.';
  const currentJsonString = activeTab === 'django' ? djangoJsonString : rawJsonString;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentJsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownloadActive = () => {
    if (activeTab === 'django') {
      onDownloadDjango();
    } else {
      onDownloadRaw();
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container json-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <h2 className="modal-title">JSON Payload Preview</h2>
            <div className="json-tabs-nav">
              <button
                className={`json-tab-btn ${activeTab === 'django' ? 'active' : ''}`}
                onClick={() => setActiveTab('django')}
              >
                ✨ Django-Compatible JSON
                {market && <span className="tab-market-badge">{market.toUpperCase()}</span>}
              </button>
              <button
                className={`json-tab-btn ${activeTab === 'raw' ? 'active' : ''}`}
                onClick={() => setActiveTab('raw')}
              >
                📄 Raw GT Holidays JSON
              </button>
            </div>
          </div>

          <div className="json-header-actions">
            <button className="copy-btn" onClick={handleCopy}>
              {copied ? '✓ Copied!' : '📋 Copy JSON'}
            </button>
            <button className="download-btn-header" onClick={handleDownloadActive}>
              ⬇ Download {activeTab === 'django' ? 'Django' : 'Raw'}
            </button>
            <button className="modal-close-btn" onClick={onClose}>✕</button>
          </div>
        </div>

        {activeTab === 'django' && schema && (
          <div className="json-meta-banner">
            <span className="meta-pill-market">{market ? market.toUpperCase() : 'DOMESTIC'} BULK IMPORT</span>
            <span className="meta-endpoint-label">Target Django Schema: <code>{schema}</code></span>
            <span className="meta-pill-contract">Validated with Pydantic</span>
          </div>
        )}

        <div className="json-modal-body">
          <pre className="json-pre">
            <code>{currentJsonString}</code>
          </pre>
        </div>

        <div className="modal-footer">
          <span className="json-size-info">
            {activeTab === 'django'
              ? `Django-Compatible JSON • ${(djangoJsonString.length / 1024).toFixed(1)} KB`
              : `${rawData.packages.length} Packages • ${(rawJsonString.length / 1024).toFixed(1)} KB`}
          </span>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

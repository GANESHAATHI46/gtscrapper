import React, { useState } from 'react';

interface URLInputProps {
  onSubmit: (url: string, downloadImages?: boolean) => void;
  isLoading: boolean;
}

// UI-only quick paste sample shortcuts for testing convenience
const UI_SHORTCUTS = [
  { label: 'Delhi', url: 'https://www.gtholidays.in/packages/india/north-india/delhi-tour-packages/' },
  { label: 'Kerala', url: 'https://www.gtholidays.in/packages/india/south-india/kerala-tour-packages/' },
  { label: 'Goa', url: 'https://www.gtholidays.in/packages/india/west-india/goa-tour-packages/' },
  { label: 'Kashmir', url: 'https://www.gtholidays.in/packages/india/north-india/jammu-and-kashmir-tour-packages/' },
  { label: 'Thailand', url: 'https://www.gtholidays.in/packages/international/asia/thailand-tour-packages/' },
  { label: 'Dubai', url: 'https://www.gtholidays.in/packages/international/asia/dubai-tour-packages/' },
  { label: 'Singapore', url: 'https://www.gtholidays.in/packages/international/asia/singapore-tour-packages/' },
];

export const URLInput: React.FC<URLInputProps> = ({ onSubmit, isLoading }) => {
  const [url, setUrl] = useState('');
  const [downloadImages, setDownloadImages] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim(), downloadImages);
    }
  };

  return (
    <div className="input-card">
      <form onSubmit={handleSubmit} className="url-form">
        <div className="input-header">
          <label htmlFor="listing-url" className="input-label">
            Paste Any GT Holidays Listing URL
          </label>
          <span className="input-hint">Domestic (India) or International Category</span>
        </div>

        <div className="input-group">
          <div className="input-wrapper">
            <svg className="input-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <input
              id="listing-url"
              type="url"
              className="url-field"
              placeholder="https://www.gtholidays.in/packages/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isLoading}
              required
            />
            {url && !isLoading && (
              <button
                type="button"
                className="clear-btn"
                onClick={() => setUrl('')}
                title="Clear input"
              >
                ✕
              </button>
            )}
          </div>

          <button
            type="submit"
            className="scrape-btn"
            disabled={isLoading || !url.trim()}
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                <span>PROCESSING...</span>
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <span>SCRAPE PACKAGES</span>
              </>
            )}
          </button>
        </div>

        <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <input
              type="checkbox"
              checked={downloadImages}
              onChange={(e) => setDownloadImages(e.target.checked)}
              disabled={isLoading}
              style={{ accentColor: 'var(--accent-cyan)', cursor: 'pointer', width: '15px', height: '15px' }}
            />
            <span>Download banner & gallery images to local storage</span>
          </label>
        </div>
      </form>

      <div className="shortcuts-container">
        <span className="shortcuts-label">Sample Category Shortcuts:</span>
        <div className="shortcuts-list">
          {UI_SHORTCUTS.map((s) => (
            <button
              key={s.label}
              type="button"
              className="shortcut-chip"
              disabled={isLoading}
              onClick={() => setUrl(s.url)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect, useRef } from 'react';
import { URLInput } from './components/URLInput';
import { ProgressTracker } from './components/ProgressTracker';
import { PackageTable } from './components/PackageTable';
import { PackageDetailModal } from './components/PackageDetailModal';
import { JSONViewer } from './components/JSONViewer';
import type { JobStatus, ScrapeResult, PackageDetail } from './types';
import './App.css';

export const App: React.FC = () => {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<ScrapeResult | null>(null);
  const [djangoPayload, setDjangoPayload] = useState<Record<string, any> | null>(null);
  const [selectedPackage, setSelectedPackage] = useState<PackageDetail | null>(null);
  const [showJsonModal, setShowJsonModal] = useState<boolean>(false);
  const [initialJsonTab, setInitialJsonTab] = useState<'raw' | 'django'>('django');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  const pollingRef = useRef<number | null>(null);

  // Check backend health on mount
  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then(() => setBackendHealthy(true))
      .catch(() => setBackendHealthy(false));
  }, []);

  // Polling loop for job status
  useEffect(() => {
    if (!jobId) return;

    const checkStatus = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) {
          throw new Error('Failed to fetch job status');
        }
        const data: JobStatus = await res.json();
        setStatus(data);

        // Fetch data once completed
        if (['completed', 'completed_with_errors'].includes(data.status)) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          fetchResult(jobId);
          fetchDjangoPayload(jobId);
        } else if (data.status === 'failed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setErrorMessage(data.error_message || 'Scrape job failed.');
        }
      } catch (err: any) {
        console.error('Polling error:', err);
      }
    };

    checkStatus();
    pollingRef.current = window.setInterval(checkStatus, 1200);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [jobId]);

  const fetchResult = async (id: string) => {
    try {
      const res = await fetch(`/api/jobs/${id}/json`);
      if (res.ok) {
        const json: ScrapeResult = await res.json();
        setResult(json);
      }
    } catch (err) {
      console.error('Failed to fetch raw result JSON:', err);
    }
  };

  const fetchDjangoPayload = async (id: string) => {
    try {
      const res = await fetch(`/api/jobs/${id}/django-json`);
      if (res.ok) {
        const json = await res.json();
        setDjangoPayload(json);
      }
    } catch (err) {
      console.error('Failed to fetch Django payload:', err);
    }
  };

  const handleStartScrape = async (targetUrl: string, downloadImages: boolean = true) => {
    setErrorMessage(null);
    setResult(null);
    setDjangoPayload(null);
    setStatus(null);
    setJobId(null);

    try {
      const res = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: targetUrl, download_images: downloadImages }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to start scraping');
      }

      const data = await res.json();
      setJobId(data.job_id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error initiating scrape job');
    }
  };

  const handleDownloadRaw = () => {
    if (!jobId) return;
    window.location.href = `/api/jobs/${jobId}/download`;
  };

  const handleDownloadDjango = () => {
    if (!jobId) return;
    window.location.href = `/api/jobs/${jobId}/download-django`;
  };

  const openJsonPreview = (tab: 'raw' | 'django') => {
    setInitialJsonTab(tab);
    setShowJsonModal(true);
  };

  const isLoading =
    !!status &&
    ['queued', 'analyzing', 'discovering', 'scraping', 'exporting', 'transforming'].includes(
      status.status
    );

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="app-header">
        <div className="header-left">
          <div className="brand-logo">
            <span className="brand-badge">GT</span>
            <span className="brand-title">GT Holidays Package Scraper</span>
          </div>
          <span className="version-pill">Django Export Edition v2.0</span>
        </div>

        <div className="header-right">
          <div className="system-health">
            <span
              className={`health-dot ${
                backendHealthy === true ? 'online' : backendHealthy === false ? 'offline' : 'checking'
              }`}
            ></span>
            <span className="health-text">
              {backendHealthy === true ? 'Backend Online' : backendHealthy === false ? 'Backend Offline' : 'Connecting...'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="app-main">
        {/* URL Input Form */}
        <section className="section-input">
          <URLInput onSubmit={handleStartScrape} isLoading={isLoading} />
        </section>

        {/* Global Error Banner */}
        {errorMessage && (
          <div className="error-banner">
            <span className="error-icon">⚠️</span>
            <span className="error-text">{errorMessage}</span>
            <button className="error-dismiss" onClick={() => setErrorMessage(null)}>✕</button>
          </div>
        )}

        {/* Live Progress Tracker */}
        {status && <ProgressTracker status={status} />}

        {/* Results Screen */}
        {result && (
          <section className="section-results">
            {/* Scraping Summary Bar */}
            <div className="results-summary-card">
              <div className="summary-left">
                <div className="summary-item">
                  <span className="summary-label">Destination</span>
                  <span className="summary-val highlight">{result.destination || 'Detected Category'}</span>
                </div>
                {result.country && (
                  <div className="summary-item">
                    <span className="summary-label">Country</span>
                    <span className="summary-val">{result.country}</span>
                  </div>
                )}
                {result.region && (
                  <div className="summary-item">
                    <span className="summary-label">Region</span>
                    <span className="summary-val">{result.region}</span>
                  </div>
                )}
                <div className="summary-item">
                  <span className="summary-label">Packages Found</span>
                  <span className="summary-val">{result.total_packages}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Successful</span>
                  <span className="summary-val success">{result.success_count}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Failed</span>
                  <span className="summary-val error">{result.failed_count}</span>
                </div>
              </div>

              <div className="summary-market-tag">
                <span className="summary-label">Detected Market</span>
                <span className={`market-pill ${status?.market || 'india'}`}>
                  {status?.market === 'international' ? '🌍 INTERNATIONAL' : '🇮🇳 INDIA'}
                </span>
              </div>
            </div>

            {/* Django-Compatible Output Card */}
            <div className="django-output-card">
              <div className="django-card-header">
                <div className="django-header-left">
                  <span className="django-card-icon">📦</span>
                  <div className="django-title-group">
                    <h3 className="django-card-title">Generated Output Files</h3>
                    <p className="django-card-subtitle">
                      Both Raw GT Holidays JSON and validated Django Bulk-Import JSON are saved in <code>backend/output/</code>
                    </p>
                  </div>
                </div>

                <div className="django-schema-badge">
                  <span className="schema-label">Target Django Schema:</span>
                  <code className="schema-code">{status?.django_schema || '/bulk-import/india/'}</code>
                </div>
              </div>

              <div className="django-actions-grid">
                <div className="output-action-group raw">
                  <div className="action-group-info">
                    <span className="file-badge raw">RAW JSON</span>
                    <span className="file-name">Original GT Holidays Complete Data</span>
                  </div>
                  <div className="action-buttons">
                    <button className="btn-action preview" onClick={() => openJsonPreview('raw')}>
                      👁️ Preview Raw JSON
                    </button>
                    <button className="btn-action download" onClick={handleDownloadRaw}>
                      ⬇️ Download Raw JSON
                    </button>
                  </div>
                </div>

                <div className="output-action-group django">
                  <div className="action-group-info">
                    <span className="file-badge django">DJANGO JSON</span>
                    <span className="file-name">
                      Focus Tourism Compatible ({status?.market?.toUpperCase() || 'INDIA'})
                    </span>
                  </div>
                  <div className="action-buttons">
                    <button className="btn-action preview django-btn" onClick={() => openJsonPreview('django')}>
                      👁️ Preview Django JSON
                    </button>
                    <button className="btn-action download django-download" onClick={handleDownloadDjango}>
                      ⬇️ Download Django JSON
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Scraped Package Data Table */}
            <PackageTable
              packages={result.packages}
              onSelectPackage={(pkg) => setSelectedPackage(pkg)}
            />
          </section>
        )}
      </main>

      {/* Package Detail Inspector Modal */}
      <PackageDetailModal
        pkg={selectedPackage}
        onClose={() => setSelectedPackage(null)}
      />

      {/* Tabbed JSON Viewer Modal */}
      {showJsonModal && result && (
        <JSONViewer
          rawData={result}
          djangoData={djangoPayload}
          market={status?.market}
          schema={status?.django_schema}
          initialTab={initialJsonTab}
          onClose={() => setShowJsonModal(false)}
          onDownloadRaw={handleDownloadRaw}
          onDownloadDjango={handleDownloadDjango}
        />
      )}
    </div>
  );
};

export default App;

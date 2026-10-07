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

  const [imageActionMsg, setImageActionMsg] = useState<string | null>(null);

  const startPolling = (id: string) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    const checkStatus = async () => {
      try {
        const res = await fetch(`/api/jobs/${id}`);
        if (!res.ok) {
          throw new Error('Failed to fetch job status');
        }
        const data: JobStatus = await res.json();
        setStatus(data);

        // Fetch data once completed
        if (['completed', 'completed_with_errors'].includes(data.status)) {
          if (data.image_download_status === 'in_progress') {
            // Keep polling while images are actively downloading in background
            return;
          }
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          fetchResult(id);
          fetchDjangoPayload(id);
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
  };

  // Polling loop for job status
  useEffect(() => {
    if (!jobId) return;
    startPolling(jobId);

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

  const handleStartScrape = async (targetUrl: string, downloadImages: boolean = false) => {
    setErrorMessage(null);
    setImageActionMsg(null);
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

  const handleTriggerDownloadImages = async () => {
    if (!jobId || isDownloadingImages) return;
    setImageActionMsg(null);
    try {
      const res = await fetch(`/api/jobs/${jobId}/download-images`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to trigger image download');
      }
      setImageActionMsg('Image download initiated. Fetching banners & galleries in background...');
      setStatus((prev) => (prev ? { ...prev, image_download_status: 'in_progress' } : null));
      startPolling(jobId);
    } catch (err: any) {
      setImageActionMsg(`Error: ${err.message || 'Failed to initiate image download'}`);
    }
  };

  const handleDownloadImagesZip = () => {
    if (!jobId) return;
    window.location.href = `/api/jobs/${jobId}/download-images-zip`;
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

  const isDownloadingImages = status?.image_download_status === 'in_progress';
  const totalImageUrls = (result?.packages || []).reduce((acc, pkg) => {
    const bannerCount = pkg.banner_image ? 1 : 0;
    const galleryCount = pkg.images ? pkg.images.length : 0;
    return acc + bannerCount + galleryCount;
  }, 0);

  const totalDownloadedImages = (result?.packages || []).reduce((acc, pkg) => {
    const bannerCount = pkg.banner_image_local ? 1 : 0;
    const galleryCount = pkg.images_local ? pkg.images_local.filter(Boolean).length : 0;
    return acc + bannerCount + galleryCount;
  }, 0);

  const hasDownloadedImages = totalDownloadedImages > 0 || status?.image_download_status === 'completed';

  const isLoading =
    !!status &&
    ['queued', 'analyzing', 'discovering', 'scraping', 'downloading_images', 'exporting', 'transforming'].includes(
      status.status
    );

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="app-header">
        <div className="header-left">
          <div className="brand-logo">
            <span className="brand-badge">TP</span>
            <span className="brand-title">Tour Package Scraper</span>
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

            {/* Dedicated Downloads & Export Hub Section */}
            <div className="download-hub-card">
              <div className="download-hub-header">
                <div className="hub-header-left">
                  <span className="hub-card-icon">📥</span>
                  <div className="hub-title-group">
                    <h3 className="hub-card-title">Downloads & Export Hub</h3>
                    <p className="hub-card-subtitle">
                      Download scraped tour packages, Django bulk-import JSON, and package images on demand.
                    </p>
                  </div>
                </div>

                <div className="hub-header-right">
                  <div className="django-schema-badge">
                    <span className="schema-label">Target Django Schema:</span>
                    <code className="schema-code">{status?.django_schema || '/bulk-import/india/'}</code>
                  </div>
                </div>
              </div>

              {imageActionMsg && (
                <div className={`hub-action-alert ${imageActionMsg.startsWith('Error') ? 'error' : 'info'}`}>
                  <span>{imageActionMsg}</span>
                  <button className="alert-close" onClick={() => setImageActionMsg(null)}>✕</button>
                </div>
              )}

              <div className="download-tiles-grid">
                {/* Tile 1: Tour Packages JSON */}
                <div className="download-tile raw-tile">
                  <div className="tile-top">
                    <div className="tile-badge-row">
                      <span className="file-badge raw">TOUR JSON</span>
                      <span className="tile-count-badge">{result.packages.length} Packages</span>
                    </div>
                    <h4 className="tile-title">Tour Packages Dataset</h4>
                    <p className="tile-desc">
                      Standard JSON format with complete itineraries, pricing, hotel options, inclusions, exclusions, and media links.
                    </p>
                  </div>
                  <div className="tile-bottom">
                    <div className="tile-meta">
                      <span>Format: <code>.json</code></span>
                      <span>Directory: <code>output/</code></span>
                    </div>
                    <div className="tile-actions">
                      <button className="btn-action preview" onClick={() => openJsonPreview('raw')}>
                        👁️ Preview
                      </button>
                      <button className="btn-action download" onClick={handleDownloadRaw}>
                        ⬇️ Download JSON
                      </button>
                    </div>
                  </div>
                </div>

                {/* Tile 2: Django Bulk-Import JSON */}
                <div className="download-tile django-tile">
                  <div className="tile-top">
                    <div className="tile-badge-row">
                      <span className="file-badge django">DJANGO JSON</span>
                      <span className="tile-market-badge">{status?.market?.toUpperCase() || 'INDIA'}</span>
                    </div>
                    <h4 className="tile-title">Django Bulk-Import Ready</h4>
                    <p className="tile-desc">
                      Pre-formatted and validated JSON ready for direct ingestion via <code>{status?.django_schema || '/bulk-import/india/'}</code>.
                    </p>
                  </div>
                  <div className="tile-bottom">
                    <div className="tile-meta">
                      <span>Schema: <code>{status?.django_schema || '/bulk-import/india/'}</code></span>
                      <span>Directory: <code>output/</code></span>
                    </div>
                    <div className="tile-actions">
                      <button className="btn-action preview django-btn" onClick={() => openJsonPreview('django')}>
                        👁️ Preview
                      </button>
                      <button className="btn-action download django-download" onClick={handleDownloadDjango}>
                        ⬇️ Download Django JSON
                      </button>
                    </div>
                  </div>
                </div>

                {/* Tile 3: Package Images Media */}
                <div className="download-tile images-tile">
                  <div className="tile-top">
                    <div className="tile-badge-row">
                      <span className="file-badge images">IMAGES MEDIA</span>
                      <span className={`tile-status-badge ${isDownloadingImages ? 'in-progress' : hasDownloadedImages ? 'completed' : 'ondemand'}`}>
                        {isDownloadingImages ? '⏳ Downloading...' : hasDownloadedImages ? '✓ Ready' : '⚡ On Demand'}
                      </span>
                    </div>
                    <h4 className="tile-title">Package Images & Banners</h4>
                    <p className="tile-desc">
                      {isDownloadingImages ? (
                        <>Downloading banners & gallery photos in background... {status?.current_package || ''}</>
                      ) : hasDownloadedImages ? (
                        <>{totalDownloadedImages} images saved locally in <code>storage/tour_packages/</code>. Download the complete ZIP archive below.</>
                      ) : (
                        <>{totalImageUrls} image URLs discovered across {result.packages.length} packages. Not automatically downloaded to save disk and bandwidth.</>
                      )}
                    </p>
                  </div>
                  <div className="tile-bottom">
                    <div className="tile-meta">
                      <span>Discovered: <strong>{totalImageUrls}</strong> URLs</span>
                      {hasDownloadedImages && <span>Downloaded: <strong>{totalDownloadedImages}</strong> files</span>}
                    </div>
                    <div className="tile-actions images-actions">
                      {!hasDownloadedImages && !isDownloadingImages && (
                        <button
                          className="btn-action image-fetch-btn"
                          onClick={handleTriggerDownloadImages}
                          disabled={isDownloadingImages}
                        >
                          📥 Fetch & Download Images
                        </button>
                      )}

                      {isDownloadingImages && (
                        <button className="btn-action image-loading-btn" disabled>
                          <span className="spinner"></span>
                          <span>Downloading Images...</span>
                        </button>
                      )}

                      {hasDownloadedImages && !isDownloadingImages && (
                        <>
                          <button
                            className="btn-action image-zip-btn"
                            onClick={handleDownloadImagesZip}
                            title="Download all downloaded package images as a ZIP file"
                          >
                            📦 Download Images (.zip)
                          </button>
                          <button
                            className="btn-action image-resync-btn"
                            onClick={handleTriggerDownloadImages}
                            title="Re-download any missing or updated images"
                          >
                            🔄 Re-sync
                          </button>
                        </>
                      )}
                    </div>
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

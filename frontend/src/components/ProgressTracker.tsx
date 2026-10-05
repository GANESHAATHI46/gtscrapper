import React from 'react';
import type { JobStatus } from '../types';

interface ProgressTrackerProps {
  status: JobStatus;
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ status }) => {
  const getStageDisplay = () => {
    if (status.status === 'analyzing') {
      return 'Analyzing listing page structure...';
    }
    if (status.status === 'discovering') {
      return 'Discovering tour packages & hidden listings...';
    }
    if (status.status === 'scraping') {
      if (status.current_package) {
        return `Scraping package ${status.completed + 1} of ${status.total}: ${status.current_package}`;
      }
      return `Scraping packages (${status.completed} / ${status.total})...`;
    }
    if (status.status === 'downloading_images') {
      const imgSum = status.image_download_summary;
      if (imgSum && imgSum.total > 0) {
        return `Downloading package images: ${imgSum.downloaded + imgSum.skipped} of ${imgSum.total} processed...`;
      }
      return status.current_package
        ? `Downloading package images: ${status.current_package}...`
        : 'Downloading package banner and gallery images to local storage...';
    }
    if (status.status === 'exporting') {
      return 'Exporting raw GT Holidays JSON...';
    }
    if (status.status === 'transforming') {
      return `Detecting market & transforming to Django-compatible JSON (${status.market?.toUpperCase() || 'Auto'})...`;
    }
    if (status.status === 'completed') {
      return 'Scrape & Django data transformation completed successfully!';
    }
    if (status.status === 'completed_with_errors') {
      return status.stage || `Completed with ${status.failed} failed packages.`;
    }
    if (status.status === 'failed') {
      return status.error_message || 'Scraping process encountered an error.';
    }
    return status.stage || 'Processing...';
  };

  const isFailed = status.status === 'failed';
  const isCompleted = status.status === 'completed' || status.status === 'completed_with_errors';

  return (
    <div className={`progress-card ${isFailed ? 'failed' : ''} ${isCompleted ? 'completed' : ''}`}>
      <div className="progress-header">
        <div className="status-badge-container">
          <span className={`status-indicator-dot ${status.status}`}></span>
          <span className="status-title">
            {status.status.toUpperCase().replace(/_/g, ' ')}
          </span>
          {status.market && (
            <span className={`market-tag-pill ${status.market}`}>
              {status.market.toUpperCase()}
            </span>
          )}
        </div>
        <div className="progress-percent-label">{status.progress_percent}%</div>
      </div>

      <div className="progress-bar-track">
        <div
          className={`progress-bar-fill ${status.status}`}
          style={{ width: `${Math.max(5, status.progress_percent)}%` }}
        ></div>
      </div>

      <div className="progress-stage-text">
        {!isCompleted && !isFailed && <span className="mini-pulse-spinner"></span>}
        <span>{getStageDisplay()}</span>
      </div>

      <div className="progress-stats-grid">
        <div className="stat-box">
          <span className="stat-label">Total Discovered</span>
          <span className="stat-value">{status.total}</span>
        </div>
        <div className="stat-box">
          <span className="stat-label">Scraped</span>
          <span className="stat-value">{status.completed}</span>
        </div>
        <div className="stat-box success">
          <span className="stat-label">Success</span>
          <span className="stat-value">{status.success}</span>
        </div>
        <div className="stat-box error">
          <span className="stat-label">Failed</span>
          <span className="stat-value">{status.failed}</span>
        </div>
      </div>

      {status.image_download_summary && status.image_download_summary.total > 0 && (
        <div className="progress-stats-grid" style={{ marginTop: '12px' }}>
          <div className="stat-box">
            <span className="stat-label">Total Images</span>
            <span className="stat-value">{status.image_download_summary.total}</span>
          </div>
          <div className="stat-box success">
            <span className="stat-label">Images Saved</span>
            <span className="stat-value">{status.image_download_summary.downloaded}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Images Cached</span>
            <span className="stat-value">{status.image_download_summary.skipped}</span>
          </div>
          <div className={`stat-box ${status.image_download_summary.failed > 0 ? 'error' : ''}`}>
            <span className="stat-label">Images Failed</span>
            <span className="stat-value">{status.image_download_summary.failed}</span>
          </div>
        </div>
      )}
    </div>
  );
};


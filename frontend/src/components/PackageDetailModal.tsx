import React, { useState } from 'react';
import type { PackageDetail } from '../types';

interface PackageDetailModalProps {
  pkg: PackageDetail | null;
  onClose: () => void;
}

export const PackageDetailModal: React.FC<PackageDetailModalProps> = ({ pkg, onClose }) => {
  const [activeTab, setActiveTab] = useState<'itinerary' | 'overview' | 'inclusions' | 'images'>('itinerary');
  const [expandedDays, setExpandedDays] = useState<Record<number, boolean>>({ 1: true });

  if (!pkg) return null;

  const toggleDay = (day: number) => {
    setExpandedDays((prev) => ({ ...prev, [day]: !prev[day] }));
  };

  const expandAll = () => {
    const all: Record<number, boolean> = {};
    pkg.itinerary.forEach((it) => (all[it.day] = true));
    setExpandedDays(all);
  };

  const collapseAll = () => {
    setExpandedDays({});
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-category-badge">{pkg.destination || 'Tour Package'}</span>
            <h2 className="modal-title">{pkg.name}</h2>
            <div className="modal-meta-row">
              {pkg.duration && <span className="meta-tag">⏱ {pkg.duration}</span>}
              {pkg.tour_type && <span className="meta-tag">🏷 {pkg.tour_type}</span>}
              {pkg.group_size && <span className="meta-tag">👥 Group: {pkg.group_size}</span>}
              {pkg.languages?.length > 0 && <span className="meta-tag">🗣 {pkg.languages.join(', ')}</span>}
              {pkg.price ? (
                <span className="meta-tag price-tag">
                  {pkg.currency || 'INR'} {new Intl.NumberFormat().format(pkg.price)}
                </span>
              ) : (
                <span className="meta-tag price-req-tag">Price on Request</span>
              )}
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Tab Navigation */}
        <div className="modal-tabs">
          <button
            className={`tab-btn ${activeTab === 'itinerary' ? 'active' : ''}`}
            onClick={() => setActiveTab('itinerary')}
          >
            Itinerary ({pkg.itinerary.length} Days)
          </button>
          <button
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview & Location
          </button>
          <button
            className={`tab-btn ${activeTab === 'inclusions' ? 'active' : ''}`}
            onClick={() => setActiveTab('inclusions')}
          >
            Inclusions / Exclusions
          </button>
          <button
            className={`tab-btn ${activeTab === 'images' ? 'active' : ''}`}
            onClick={() => setActiveTab('images')}
          >
            Gallery ({pkg.images.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="modal-body">
          {activeTab === 'itinerary' && (
            <div className="itinerary-tab-content">
              <div className="itinerary-actions">
                <span className="itinerary-counter">{pkg.itinerary.length} Days Itinerary Plan</span>
                <div className="expand-buttons">
                  <button className="text-action-btn" onClick={expandAll}>Expand All</button>
                  <span className="sep">•</span>
                  <button className="text-action-btn" onClick={collapseAll}>Collapse All</button>
                </div>
              </div>

              {pkg.itinerary.length === 0 ? (
                <div className="empty-tab-msg">No day-by-day itinerary schedule found for this tour.</div>
              ) : (
                <div className="itinerary-accordion">
                  {pkg.itinerary.map((item) => {
                    const isExpanded = !!expandedDays[item.day];
                    return (
                      <div key={item.day} className={`accordion-day-card ${isExpanded ? 'open' : ''}`}>
                        <div className="accordion-day-header" onClick={() => toggleDay(item.day)}>
                          <div className="day-badge">Day {item.day}</div>
                          <div className="day-title">{item.title || `Day ${item.day} Sightseeing`}</div>
                          <span className="accordion-chevron">{isExpanded ? '▲' : '▼'}</span>
                        </div>
                        {isExpanded && (
                          <div className="accordion-day-body">
                            <p>{item.description || 'Detailed itinerary activities are scheduled for this day.'}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'overview' && (
            <div className="overview-tab-content">
              <div className="overview-section">
                <h4>Package Overview</h4>
                <p className="overview-text">
                  {pkg.overview || 'No textual overview description available for this package.'}
                </p>
              </div>

              <div className="location-section">
                <h4>Destinations & Route</h4>
                <p><strong>Primary Destination:</strong> {pkg.destination || 'Not Specified'}</p>
                {pkg.destinations?.length > 0 && (
                  <div className="destinations-pills">
                    {pkg.destinations.map((d, i) => (
                      <span key={i} className="dest-pill">📍 {d}</span>
                    ))}
                  </div>
                )}
                {pkg.location && (
                  <p className="location-detail"><strong>Location String:</strong> {pkg.location}</p>
                )}
              </div>

              <div className="source-section">
                <h4>Original Source</h4>
                <a href={pkg.source_url} target="_blank" rel="noreferrer" className="source-link">
                  Open Original Page on GT Holidays ↗
                </a>
              </div>
            </div>
          )}

          {activeTab === 'inclusions' && (
            <div className="inclusions-tab-content">
              <div className="inc-exc-grid">
                <div className="inc-box">
                  <h4 className="inc-title">Included</h4>
                  {pkg.included.length > 0 ? (
                    <ul className="inc-list">
                      {pkg.included.map((inc, i) => (
                        <li key={i}>✓ {inc}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="empty-inc-text">Standard tour inclusions apply or not itemized on source page.</p>
                  )}
                </div>

                <div className="exc-box">
                  <h4 className="exc-title">Excluded</h4>
                  {pkg.excluded.length > 0 ? (
                    <ul className="exc-list">
                      {pkg.excluded.map((exc, i) => (
                        <li key={i}>✗ {exc}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="empty-inc-text">Standard exclusions apply or not itemized on source page.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'images' && (
            <div className="images-tab-content">
              {pkg.image_download_status && (
                <div style={{ marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Download Status:</span>
                  <span style={{ textTransform: 'capitalize', color: pkg.image_download_status === 'completed' ? 'var(--accent-emerald)' : 'var(--accent-cyan)' }}>
                    {pkg.image_download_status}
                  </span>
                  {pkg.banner_image_local && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                      (Storage: <code>storage/gt_holidays/{pkg.banner_image_local}</code>)
                    </span>
                  )}
                </div>
              )}
              {pkg.images.length === 0 ? (
                <div className="empty-tab-msg">No images found for this package.</div>
              ) : (
                <div className="gallery-grid">
                  {pkg.images.map((img, i) => {
                    const localPath = pkg.images_local && pkg.images_local[i];
                    return (
                      <div key={i} className="gallery-item" style={{ position: 'relative' }}>
                        <img
                          src={localPath ? `/storage/${localPath}` : img}
                          alt={`${pkg.name} preview ${i + 1}`}
                          loading="lazy"
                          onError={(e) => {
                            if (localPath && e.currentTarget.src !== img) {
                              e.currentTarget.src = img;
                            }
                          }}
                        />
                        {localPath && (
                          <div style={{ position: 'absolute', bottom: '6px', left: '6px', background: 'rgba(0,0,0,0.7)', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', color: '#10b981' }}>
                            ✓ Local
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <span className="slug-info">Slug: <code>{pkg.slug}</code></span>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

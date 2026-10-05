import React, { useState } from 'react';
import type { PackageDetail } from '../types';

interface PackageTableProps {
  packages: PackageDetail[];
  onSelectPackage: (pkg: PackageDetail) => void;
}

export const PackageTable: React.FC<PackageTableProps> = ({ packages, onSelectPackage }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredPackages = packages.filter((pkg) => {
    const term = searchTerm.toLowerCase();
    const nameMatch = pkg.name.toLowerCase().includes(term);
    const destMatch = (pkg.destination || '').toLowerCase().includes(term);
    const locMatch = (pkg.location || '').toLowerCase().includes(term);
    return nameMatch || destMatch || locMatch;
  });

  const formatPrice = (pkg: PackageDetail) => {
    if (pkg.price != null && pkg.price > 0) {
      const cur = pkg.currency || 'INR';
      const formatted = new Intl.NumberFormat('en-IN').format(pkg.price);
      return cur === 'INR' ? `₹ ${formatted}` : `${cur} ${formatted}`;
    }
    return <span className="price-on-req">Price on Request</span>;
  };

  return (
    <div className="table-card">
      <div className="table-header">
        <div className="table-title-group">
          <h3 className="table-heading">Scraped Packages</h3>
          <span className="table-count-badge">
            {filteredPackages.length} of {packages.length}
          </span>
        </div>

        <div className="search-box">
          <svg className="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="search-field"
            placeholder="Search by name, destination..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button className="clear-search-btn" onClick={() => setSearchTerm('')}>✕</button>
          )}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="package-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>Destination</th>
              <th>Duration</th>
              <th>Price</th>
              <th>Itinerary</th>
              <th>Images</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredPackages.map((pkg, idx) => (
              <tr key={pkg.slug + idx} onClick={() => onSelectPackage(pkg)} className="table-row-clickable">
                <td className="row-num">{idx + 1}</td>
                <td className="cell-name">
                  <div className="name-wrapper">
                    {pkg.banner_image && (
                      <img src={pkg.banner_image} alt="" className="table-thumb" loading="lazy" />
                    )}
                    <span className="package-title-text" title={pkg.name}>
                      {pkg.name}
                    </span>
                  </div>
                </td>
                <td className="cell-dest">
                  <span className="dest-tag">{pkg.destination || 'N/A'}</span>
                </td>
                <td className="cell-duration">
                  <span className="duration-pill">{pkg.duration || 'N/A'}</span>
                </td>
                <td className="cell-price">
                  {formatPrice(pkg)}
                </td>
                <td className="cell-itinerary">
                  <span className="itinerary-badge">
                    {pkg.itinerary.length > 0 ? `${pkg.itinerary.length} Days` : '0 Days'}
                  </span>
                </td>
                <td className="cell-images">
                  <span className="images-count">
                    📸 {pkg.images.length}
                  </span>
                </td>
                <td className="cell-status">
                  <span className="status-pill-success">Ready</span>
                </td>
                <td className="cell-action">
                  <button
                    className="view-details-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectPackage(pkg);
                    }}
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
            {filteredPackages.length === 0 && (
              <tr>
                <td colSpan={9} className="no-results-cell">
                  No packages matched your search filter "{searchTerm}".
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

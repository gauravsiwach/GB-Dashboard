import React, { useState } from 'react';

const ImportFlagModal = ({ isOpen, onClose, onImport, selectedMarketId }) => {
  const [growthbookFeatureId, setGrowthbookFeatureId] = useState('');
  const [flagKey, setFlagKey] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleImport = async (e) => {
    e.preventDefault();
    setError('');
    setIsImporting(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/flags/import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          growthbook_feature_id: growthbookFeatureId,
          market_id: selectedMarketId,
          key: flagKey || undefined,
        }),
      });

      const data = await response.json();

      if (data.success) {
        onImport(data.flag);
        setGrowthbookFeatureId('');
        setFlagKey('');
        onClose();
      } else {
        setError(data.message || 'Failed to import flag');
      }
    } catch (err) {
      setError(err.message || 'Failed to import flag');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2>Import Flag from GrowthBook</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {error && <div className="error">{error}</div>}
          <form onSubmit={handleImport}>
            <div className="form-group">
              <label htmlFor="gb-feature-id">GrowthBook Feature ID:</label>
              <input
                type="text"
                id="gb-feature-id"
                value={growthbookFeatureId}
                onChange={(e) => setGrowthbookFeatureId(e.target.value)}
                required
                placeholder="e.g., test-feature"
              />
            </div>
            <div className="form-group">
              <label htmlFor="flag-key">Flag Key (optional):</label>
              <input
                type="text"
                id="flag-key"
                value={flagKey}
                onChange={(e) => setFlagKey(e.target.value)}
                placeholder="Leave blank to use GrowthBook key"
              />
            </div>
            <div className="modal-actions">
              <button type="button" onClick={onClose} disabled={isImporting}>
                Cancel
              </button>
              <button type="submit" disabled={isImporting}>
                {isImporting ? 'Importing...' : 'Import'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ImportFlagModal;

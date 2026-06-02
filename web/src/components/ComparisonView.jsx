import React, { useState, useEffect } from 'react';
import PromotionDialog from './PromotionDialog';

const ComparisonView = ({ selectedMarket }) => {
  const [sourceEnv, setSourceEnv] = useState('dev');
  const [targetEnv, setTargetEnv] = useState('production');
  const [comparisons, setComparisons] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  const [isPromoting, setIsPromoting] = useState(false);
  const [showPromotionDialog, setShowPromotionDialog] = useState(false);
  const [promotionResults, setPromotionResults] = useState(null);
  const [selectedFlags, setSelectedFlags] = useState(new Set());
  const [valuePopup, setValuePopup] = useState({ show: false, value: null, title: '' });

  // Initialize environments based on env flow when market changes
  useEffect(() => {
    if (selectedMarket && selectedMarket.env_flow) {
      const envFlow = selectedMarket.env_flow.split('->').map(e => e.trim());
      if (envFlow.length >= 2) {
        setSourceEnv(envFlow[0]);
        setTargetEnv(envFlow[1]);
      }
    }
  }, [selectedMarket]);

  // Auto-select target environment based on source and env flow
  const handleSourceEnvChange = (newSourceEnv) => {
    setSourceEnv(newSourceEnv);
    
    if (selectedMarket && selectedMarket.env_flow) {
      const envFlow = selectedMarket.env_flow.split('->').map(e => e.trim());
      const sourceIndex = envFlow.indexOf(newSourceEnv);
      
      if (sourceIndex !== -1 && sourceIndex < envFlow.length - 1) {
        setTargetEnv(envFlow[sourceIndex + 1]);
      }
    }
  };

  const handleCompare = async (isAutoRefresh = false) => {
    setError('');
    setIsLoading(true);
    setSelectedFlags(new Set()); // Reset selections when comparing
    
    // Always clear promotion results on manual compare
    if (!isAutoRefresh) {
      setPromotionResults(null);
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_environment: sourceEnv,
          target_environment: targetEnv,
          market_id: selectedMarket ? selectedMarket.id : 1,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Comparison failed');
      }

      const data = await response.json();
      setComparisons(data.comparisons);
      setStats({
        total: data.total_flags,
        inSync: data.in_sync_count,
        different: data.different_count,
        missingInTarget: data.missing_in_target_count,
        missingInSource: data.missing_in_source_count,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePromote = async () => {
    setIsPromoting(true);
    setError('');
    setPromotionResults(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/promote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_environment: sourceEnv,
          target_environment: targetEnv,
          market_id: selectedMarket ? selectedMarket.id : 1,
          flag_keys: Array.from(selectedFlags),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Promotion failed');
      }

      const data = await response.json();
      setPromotionResults(data);
      setShowPromotionDialog(false);
      
      // Clear selections after promotion
      setSelectedFlags(new Set());
      
      // Refresh comparison after promotion
      await handleCompare(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsPromoting(false);
    }
  };

  const handleShowPromotionDialog = () => {
    // Only show dialog if flags are selected
    if (selectedFlags.size === 0) {
      setError('Please select at least one flag to promote.');
      return;
    }
    
    setShowPromotionDialog(true);
  };

  const handleFlagSelection = (flagKey) => {
    const newSelected = new Set(selectedFlags);
    if (newSelected.has(flagKey)) {
      newSelected.delete(flagKey);
    } else {
      newSelected.add(flagKey);
    }
    setSelectedFlags(newSelected);
  };

  const handleSelectAll = () => {
    // Select all flags that need promotion (different or missing in target)
    const flagsToPromote = comparisons.filter(
      c => c.status === 'different' || c.status === 'missing_in_target'
    );
    
    if (flagsToPromote.length === selectedFlags.size) {
      // Deselect all
      setSelectedFlags(new Set());
    } else {
      // Select all promotable flags
      setSelectedFlags(new Set(flagsToPromote.map(c => c.key)));
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'in_sync':
        return '#4caf50';
      case 'different':
        return '#ff9800';
      case 'missing_in_target':
        return '#f44336';
      case 'missing_in_source':
        return '#2196f3';
      default:
        return '#757575';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'in_sync':
        return 'In Sync';
      case 'different':
        return 'Different';
      case 'missing_in_target':
        return 'Missing in Target';
      case 'missing_in_source':
        return 'Missing in Source';
      default:
        return status;
    }
  };

  const handleValueClick = (value, title) => {
    setValuePopup({ show: true, value, title, type: 'value' });
  };

  const handleRulesClick = (rules, title) => {
    setValuePopup({ show: true, value: rules, title, type: 'rules' });
  };

  const truncateValue = (value) => {
    if (!value) return '-';
    const strValue = String(value);
    if (strValue.length > 20) {
      return strValue.substring(0, 20) + '...';
    }
    return strValue;
  };

  return (
    <div className="comparison-view">
      <h2>Environment Comparison</h2>
      
      <div className="comparison-controls">
        <div className="control-group">
          <label htmlFor="source-env">Source Environment:</label>
          <select
            id="source-env"
            value={sourceEnv}
            onChange={(e) => handleSourceEnvChange(e.target.value)}
          >
            <option value="dev">Dev</option>
            <option value="qa">QA</option>
            <option value="uat">UAT</option>
            <option value="pre-prod">Pre-Prod</option>
            <option value="production">Production</option>
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="target-env">Target Environment:</label>
          <select
            id="target-env"
            value={targetEnv}
            onChange={(e) => setTargetEnv(e.target.value)}
          >
            <option value="dev">Dev</option>
            <option value="qa">QA</option>
            <option value="uat">UAT</option>
            <option value="pre-prod">Pre-Prod</option>
            <option value="production">Production</option>
          </select>
        </div>

        <button
          onClick={() => handleCompare(false)}
          disabled={isLoading || sourceEnv === targetEnv}
          className="compare-button"
        >
          {isLoading ? 'Comparing...' : 'Compare'}
        </button>
        {stats && stats.different + stats.missingInTarget > 0 && (
          <button
            onClick={handleShowPromotionDialog}
            disabled={isPromoting || selectedFlags.size === 0}
            className="promote-button"
          >
            {isPromoting ? 'Promoting...' : `Promote (${selectedFlags.size})`}
          </button>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      {stats && (
        <div className="comparison-stats">
          <h3>Comparison Results</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Total Flags:</span>
              <span className="stat-value">{stats.total}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">In Sync:</span>
              <span className="stat-value" style={{ color: '#4caf50' }}>{stats.inSync}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Different:</span>
              <span className="stat-value" style={{ color: '#ff9800' }}>{stats.different}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Missing in Target:</span>
              <span className="stat-value" style={{ color: '#f44336' }}>{stats.missingInTarget}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Missing in Source:</span>
              <span className="stat-value" style={{ color: '#2196f3' }}>{stats.missingInSource}</span>
            </div>
          </div>
        </div>
      )}

      {comparisons.length > 0 && (
        <div className="comparison-results">
          <h3>Flag Details</h3>
          <table className="comparison-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={
                      comparisons.filter(
                        c => c.status === 'different' || c.status === 'missing_in_target'
                      ).length > 0 &&
                      comparisons.filter(
                        c => c.status === 'different' || c.status === 'missing_in_target'
                      ).length === selectedFlags.size
                    }
                    onChange={handleSelectAll}
                  />
                </th>
                <th>Key</th>
                <th>Status</th>
                <th>Source Value</th>
                <th>Target Value</th>
                <th>Source Enabled</th>
                <th>Target Enabled</th>
                <th>Source Rules</th>
                <th>Target Rules</th>
                <th>Draft</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((comparison, index) => (
                <tr key={index}>
                  <td>
                    {(comparison.status === 'different' || comparison.status === 'missing_in_target') && !comparison.draft && (
                      <input
                        type="checkbox"
                        checked={selectedFlags.has(comparison.key)}
                        onChange={() => handleFlagSelection(comparison.key)}
                      />
                    )}
                  </td>
                  <td>{comparison.key}</td>
                  <td>
                    <span
                      className="status-badge"
                      style={{ backgroundColor: getStatusColor(comparison.status) }}
                    >
                      {getStatusLabel(comparison.status)}
                    </span>
                  </td>
                  <td>
                    <button 
                      className="value-button"
                      onClick={() => handleValueClick(comparison.source_value, 'Source Value')}
                    >
                      {truncateValue(comparison.source_value)}
                    </button>
                  </td>
                  <td>
                    <button 
                      className="value-button"
                      onClick={() => handleValueClick(comparison.target_value, 'Target Value')}
                    >
                      {truncateValue(comparison.target_value)}
                    </button>
                  </td>
                  <td>
                    <span className={`enabled-badge ${comparison.source_enabled ? 'enabled' : 'disabled'}`}>
                      {comparison.source_enabled ? '✓ Enabled' : '✕ Disabled'}
                    </span>
                  </td>
                  <td>
                    <span className={`enabled-badge ${comparison.target_enabled ? 'enabled' : 'disabled'}`}>
                      {comparison.target_enabled ? '✓ Enabled' : '✕ Disabled'}
                    </span>
                  </td>
                  <td>
                    {comparison.source_rules && comparison.source_rules.length > 0 ? (
                      <div 
                        className="rules-cell clickable"
                        onClick={() => handleRulesClick(comparison.source_rules, 'Source Rules')}
                      >
                        {comparison.source_rules.filter(rule => rule.condition).map((rule, idx) => (
                          <div key={idx} className="rule-item">
                            <div className="rule-header">
                              <strong>Rule {idx + 1}</strong>
                              <span className={`rule-status ${rule.enabled ? 'enabled' : 'disabled'}`}>
                                {rule.enabled ? '✓ Enabled' : '✗ Disabled'}
                              </span>
                            </div>
                            <div className="rule-details">
                              <div><strong>Type:</strong> {rule.type || 'N/A'}</div>
                              <div><strong>Condition:</strong> {rule.condition || 'N/A'}</div>
                              <div><strong>Value:</strong> {rule.value || 'N/A'}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="no-rules">-</span>
                    )}
                  </td>
                  <td>
                    {comparison.target_rules && comparison.target_rules.length > 0 ? (
                      <div 
                        className="rules-cell clickable"
                        onClick={() => handleRulesClick(comparison.target_rules, 'Target Rules')}
                      >
                        {comparison.target_rules.filter(rule => rule.condition).map((rule, idx) => (
                          <div key={idx} className="rule-item">
                            <div className="rule-header">
                              <strong>Rule {idx + 1}</strong>
                              <span className={`rule-status ${rule.enabled ? 'enabled' : 'disabled'}`}>
                                {rule.enabled ? '✓ Enabled' : '✗ Disabled'}
                              </span>
                            </div>
                            <div className="rule-details">
                              <div><strong>Type:</strong> {rule.type || 'N/A'}</div>
                              <div><strong>Condition:</strong> {rule.condition || 'N/A'}</div>
                              <div><strong>Value:</strong> {rule.value || 'N/A'}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="no-rules">-</span>
                    )}
                  </td>
                  <td>
                    <span className={`draft-badge ${comparison.draft ? 'draft' : 'published'}`}>
                      {comparison.draft ? '📝 Draft' : '✓ Published'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {promotionResults && (
        <div className="promotion-results">
          <h3>Promotion Results</h3>
          <div className="promotion-summary">
            <span className="promotion-success">{promotionResults.successful_count} successful</span>
            <span className="promotion-failed">{promotionResults.failed_count} failed</span>
            <span className="promotion-skipped">{promotionResults.skipped_count} skipped</span>
          </div>
        </div>
      )}

      <PromotionDialog
        isOpen={showPromotionDialog}
        onClose={() => setShowPromotionDialog(false)}
        onConfirm={handlePromote}
        sourceEnv={sourceEnv}
        targetEnv={targetEnv}
        flagCount={selectedFlags.size}
      />

      {valuePopup.show && (
        <div className="value-popup-overlay" onClick={() => setValuePopup({ show: false, value: null, title: '', type: '' })}>
          <div className="value-popup-modal" onClick={(e) => e.stopPropagation()}>
            <div className="value-popup-header">
              <h3>{valuePopup.title}</h3>
              <button 
                className="value-popup-close"
                onClick={() => setValuePopup({ show: false, value: null, title: '', type: '' })}
              >
                ×
              </button>
            </div>
            <div className="value-popup-content">
              {valuePopup.type === 'rules' ? (
                <div className="rules-popup-display">
                  {valuePopup.value.filter(rule => rule.condition).map((rule, idx) => (
                    <div key={idx} className="rule-item">
                      <div className="rule-header">
                        <strong>Rule {idx + 1}</strong>
                        <span className={`rule-status ${rule.enabled ? 'enabled' : 'disabled'}`}>
                          {rule.enabled ? '✓ Enabled' : '✗ Disabled'}
                        </span>
                      </div>
                      <div className="rule-details">
                        <div><strong>Type:</strong> {rule.type || 'N/A'}</div>
                        <div><strong>Condition:</strong> {rule.condition || 'N/A'}</div>
                        <div><strong>Value:</strong> {rule.value || 'N/A'}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <pre>{JSON.stringify(valuePopup.value, null, 2)}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComparisonView;

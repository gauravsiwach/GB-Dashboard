import React, { useState, useEffect, useMemo } from 'react';
import RuleEditor from './RuleEditor';

const EditFlagModal = ({ isOpen, onClose, flag, selectedMarket, onSuccess, onError }) => {
  const [environment, setEnvironment] = useState('dev');
  const [enabled, setEnabled] = useState(false);
  const [defaultValue, setDefaultValue] = useState('false');
  const [loading, setLoading] = useState(false);
  const [fetchingDetails, setFetchingDetails] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [error, setError] = useState('');
  const [flagDetails, setFlagDetails] = useState(null);

  // Parse environment flow from market - memoize to prevent recreating
  const environments = useMemo(() => {
    return selectedMarket && selectedMarket.env_flow 
      ? selectedMarket.env_flow.split('->').map(e => e.trim()) 
      : ['dev', 'qa', 'uat', 'production'];
  }, [selectedMarket]);

  // Fetch flag details from GrowthBook when modal opens
  useEffect(() => {
    const fetchFlagDetails = async () => {
      if (isOpen && flag) {
        setFetchingDetails(true);
        setError('');
        
        // Set initial environment before fetching
        const firstEnv = environments[0];
        setEnvironment(firstEnv);
        
        console.log('Fetching flag details for flag:', flag);
        console.log('Fetching from URL:', `http://localhost:8000/api/v1/flags/${flag.id}/gb-details?environment=${firstEnv}`);
        
        try {
          const response = await fetch(`http://localhost:8000/api/v1/flags/${flag.id}/gb-details?environment=${firstEnv}`);
          
          console.log('Response status:', response.status);
          
          if (!response.ok) {
            throw new Error('Failed to fetch flag details');
          }
          
          const data = await response.json();
          console.log('Flag details response:', data);
          setFlagDetails(data);
          
          // Set values for first environment
          const envConfig = data.environments[firstEnv] || {};
          setEnabled(envConfig.enabled || false);
          setDefaultValue(envConfig.defaultValue || data.defaultValue || 'false');
        } catch (err) {
          console.error('Error fetching flag details:', err);
          setError(`Error fetching flag details: ${err.message}`);
          // Set defaults on error
          setEnvironment(environments[0]);
          setEnabled(false);
          setDefaultValue('false');
        } finally {
          setFetchingDetails(false);
        }
      }
    };
    
    fetchFlagDetails();
  }, [isOpen, flag]);

  // Update form values when environment changes
  useEffect(() => {
    if (flagDetails && environment) {
      const envConfig = flagDetails.environments[environment] || {};
      setEnabled(envConfig.enabled || false);
      setDefaultValue(envConfig.defaultValue || flagDetails.defaultValue || 'false');
    }
  }, [environment, flagDetails]);

  // Fetch rules when environment changes
  useEffect(() => {
    const fetchRulesForEnvironment = async () => {
      if (flag && environment) {
        try {
          const response = await fetch(`http://localhost:8000/api/v1/flags/${flag.id}/gb-details?environment=${environment}`);
          if (response.ok) {
            const data = await response.json();
            setFlagDetails(data);
          }
        } catch (err) {
          console.error('Error fetching rules for environment:', err);
        }
      }
    };
    
    fetchRulesForEnvironment();
  }, [environment]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`http://localhost:8000/api/v1/flags/${flag.id}/update-gb-value`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          environment,
          enabled,
          default_value: defaultValue,
        }),
      });

      const data = await response.json();

      if (data.success) {
        if (onSuccess) {
          onSuccess('Flag updated successfully in GrowthBook');
        }
        onClose();
      } else {
        setError(data.message || 'Failed to update flag');
        if (onError) {
          onError(data.message || 'Failed to update flag');
        }
      }
    } catch (err) {
      const errorMsg = `Error updating flag: ${err.message}`;
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleArchive = async () => {
    if (!confirm('Are you sure you want to archive this flag in GrowthBook? This action cannot be undone from the dashboard.')) {
      return;
    }

    setArchiving(true);
    setError('');

    try {
      const response = await fetch(`http://localhost:8000/api/v1/flags/${flag.id}/archive`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        if (onSuccess) {
          onSuccess('Flag archived successfully in GrowthBook');
        }
        onClose();
      } else {
        const errorMsg = data.message || 'Failed to archive flag';
        setError(errorMsg);
        if (onError) {
          onError(errorMsg);
        }
      }
    } catch (err) {
      const errorMsg = `Error archiving flag: ${err.message}`;
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    } finally {
      setArchiving(false);
    }
  };

  if (!isOpen || !flag) return null;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2>Edit Flag in GrowthBook</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p><strong>Flag:</strong> {flag.key}</p>
          <p><strong>GrowthBook ID:</strong> {flag.growthbook_feature_id}</p>
          
          {fetchingDetails ? (
            <div className="loading">Loading flag details...</div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="environment">Environment:</label>
                <select
                  id="environment"
                  value={environment}
                  onChange={(e) => setEnvironment(e.target.value)}
                >
                  {environments.map(env => (
                    <option key={env} value={env}>{env}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="enabled">Enabled:</label>
                <select
                  id="enabled"
                  value={enabled.toString()}
                  onChange={(e) => setEnabled(e.target.value === 'true')}
                >
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="defaultValue">Default Value:</label>
                <input
                  id="defaultValue"
                  type="text"
                  value={defaultValue}
                  onChange={(e) => setDefaultValue(e.target.value)}
                />
              </div>

              <RuleEditor
                rules={flagDetails?.rules || []}
                environment={environment}
                flagId={flag?.id}
                onRulesChange={(newRules) => {
                  setFlagDetails({ ...flagDetails, rules: newRules });
                }}
              />

              {error && <div className="error">{error}</div>}

              <div className="modal-actions">
                <button type="submit" disabled={loading || fetchingDetails || archiving}>
                  {loading ? 'Updating...' : 'Update in GrowthBook'}
                </button>
                <button 
                  type="button" 
                  className="archive-button"
                  onClick={handleArchive}
                  disabled={loading || fetchingDetails || archiving}
                >
                  {archiving ? 'Archiving...' : '🗄️ Archive Flag'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default EditFlagModal;

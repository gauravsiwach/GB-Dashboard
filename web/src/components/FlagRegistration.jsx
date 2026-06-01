import React, { useState } from 'react';

const FlagRegistration = ({ selectedMarketId, onFlagCreated }) => {
  const [formData, setFormData] = useState({
    key: '',
    market_id: selectedMarketId || '',
    description: '',
    default_value: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/flags', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create flag');
      }

      const newFlag = await response.json();
      onFlagCreated(newFlag);
      setFormData({
        key: '',
        market_id: selectedMarketId || '',
        description: '',
        default_value: '',
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flag-registration">
      <h3>Create New Flag</h3>
      <p className="flag-registration-note">Creates flag in GrowthBook and saves locally</p>
      {error && <div className="error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="flag-key">Flag Key:</label>
          <input
            type="text"
            id="flag-key"
            name="key"
            value={formData.key}
            onChange={handleChange}
            required
            disabled={!selectedMarketId}
          />
        </div>
        <div className="form-group">
          <label htmlFor="flag-description">Description:</label>
          <input
            type="text"
            id="flag-description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            disabled={!selectedMarketId}
          />
        </div>
        <div className="form-group">
          <label htmlFor="flag-default-value">Default Value:</label>
          <input
            type="text"
            id="flag-default-value"
            name="default_value"
            value={formData.default_value}
            onChange={handleChange}
            disabled={!selectedMarketId}
          />
        </div>
        <button type="submit" disabled={!selectedMarketId || isSubmitting}>
          {isSubmitting ? 'Creating...' : 'Create Flag'}
        </button>
      </form>
    </div>
  );
};

export default FlagRegistration;

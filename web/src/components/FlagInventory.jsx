import React, { useState, useCallback } from 'react';
import { FaSpinner } from 'react-icons/fa';

const FlagInventory = ({ flags, onEditFlag, onSearch, loading }) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Debounce function to delay API calls
  const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  };

  // Debounced search handler
  const debouncedSearch = useCallback(
    debounce((term) => {
      if (onSearch) {
        onSearch(term);
      }
    }, 1000),
    [onSearch]
  );

  const handleSearchChange = (e) => {
    const term = e.target.value;
    setSearchTerm(term);
    debouncedSearch(term);
  };

  // Filter flags locally if no onSearch callback provided
  const filteredFlags = searchTerm && !onSearch
    ? flags.filter(flag => flag.key.toLowerCase().includes(searchTerm.toLowerCase()))
    : flags;

  const displayFlags = onSearch ? flags : filteredFlags;

  if (!flags || flags.length === 0) {
    return (
      <div className="flag-inventory">
        <h3>Flags Inventory</h3>
        <div className="search-container">
          <input
            type="text"
            placeholder="Search flags by key..."
            value={searchTerm}
            onChange={handleSearchChange}
            className="search-input"
          />
        </div>
        {loading ? (
          <div className="flag-inventory loading">
            <FaSpinner className="loading-spinner" />
            <span>Loading flags...</span>
          </div>
        ) : (
          <div className="flag-inventory empty">No flags found for this market.</div>
        )}
      </div>
    );
  }

  return (
    <div className="flag-inventory">
      <h3>Flags Inventory</h3>
      <div className="search-container">
        <input
          type="text"
          placeholder="Search flags by key..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="search-input"
        />
      </div>
      
      {loading ? (
        <div className="flag-inventory loading">
          <FaSpinner className="loading-spinner" />
          <span>Loading flags...</span>
        </div>
      ) : !displayFlags || displayFlags.length === 0 ? (
        <div className="flag-inventory empty">{searchTerm ? 'No flags found matching your search.' : 'No flags found for this market.'}</div>
      ) : (
        <table className="flags-table">
          <thead>
            <tr>
              <th>Flag Key</th>
              <th>GrowthBook Feature ID</th>
              <th>Rules</th>
              <th>Updated At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {displayFlags.map((flag) => (
              <tr key={flag.id}>
                <td>{flag.key}</td>
                <td>{flag.growthbook_feature_id}</td>
                <td className="rules-cell">
                  <span className="rule-count">{flag.rule_count !== undefined ? flag.rule_count : '-'}</span>
                  {flag.rule_count > 0 && (
                    <span className="rule-indicator" title={`${flag.rule_count} rule(s) configured`}>⚙️</span>
                  )}
                </td>
                <td>{new Date(flag.updated_at).toLocaleString()}</td>
                <td>
                  <button onClick={() => onEditFlag(flag)}>Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default FlagInventory;

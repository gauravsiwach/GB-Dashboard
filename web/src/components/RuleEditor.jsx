import React, { useState, useEffect } from 'react';

const RuleEditor = ({ rules, onRulesChange, environment, flagId }) => {
  const [ruleText, setRuleText] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (rules && rules.length > 0) {
      setRuleText(JSON.stringify(rules, null, 2));
    } else {
      setRuleText('');
    }
  }, [rules]);

  const handleTextChange = (e) => {
    setRuleText(e.target.value);
    setValidationError('');
  };

  const handleSave = async () => {
    try {
      const parsedRules = JSON.parse(ruleText);
      
      // Basic validation
      if (!Array.isArray(parsedRules)) {
        setValidationError('Rules must be an array');
        return;
      }

      // Validate each rule structure
      for (const rule of parsedRules) {
        if (!rule.type || !rule.condition) {
          setValidationError('Each rule must have type and condition');
          return;
        }
      }

      // Call API to update rules
      const apiUrl = `http://localhost:8000/api/v1/flags/${flagId}/rules?environment=${environment}`;
      
      const response = await fetch(apiUrl, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rules: parsedRules
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update rules');
      }

      onRulesChange(parsedRules);
      setIsEditing(false);
    } catch (err) {
      if (err instanceof SyntaxError) {
        setValidationError('Invalid JSON format');
      } else {
        setValidationError(err.message || 'Failed to save rules');
      }
    }
  };

  const handleCancel = () => {
    setRuleText(rules ? JSON.stringify(rules, null, 2) : '');
    setValidationError('');
    setIsEditing(false);
  };

  const handleEditClick = () => {
    setRuleText(rules ? JSON.stringify(rules, null, 2) : '');
    setValidationError('');
    setIsEditing(true);
  };

  const handleAddRule = () => {
    const newRule = {
      type: 'force',
      condition: '{"id": "example"}',
      value: 'true',
      enabled: true,
      environments: [environment]
    };
    
    const currentRules = ruleText ? JSON.parse(ruleText) : [];
    currentRules.push(newRule);
    setRuleText(JSON.stringify(currentRules, null, 2));
  };

  return (
    <div className="rule-editor">
      <div className="rule-editor-header">
        <h4>Rule Editor ({environment})</h4>
        {!isEditing ? (
          <button onClick={handleEditClick}>Edit Rules</button>
        ) : (
          <div className="rule-editor-actions">
            <button onClick={handleCancel} className="cancel-button">Cancel</button>
            <button onClick={handleSave} className="save-button">Save</button>
          </div>
        )}
      </div>
      
      {isEditing ? (
        <div className="rule-editor-content">
          <textarea
            value={ruleText}
            onChange={handleTextChange}
            className="rule-textarea"
            placeholder="Enter rules in JSON format"
            rows={10}
            style={{ width: '100%', minHeight: '200px' }}
          />
          
          <button type="button" onClick={handleAddRule} className="add-rule-button">
            + Add Rule
          </button>
          
          {validationError && (
            <div className="validation-error">{validationError}</div>
          )}
        </div>
      ) : (
        <div className="rule-editor-content">
          {rules && rules.length > 0 ? (
            <div className="rules-display">
              {rules.map((rule, index) => (
                <div key={index} className="rule-item">
                  <div className="rule-header">
                    <strong>Rule {index + 1}</strong>
                    <span className={`rule-status ${rule.enabled ? 'enabled' : 'disabled'}`}>
                      {rule.enabled ? '✓ Enabled' : '✗ Disabled'}
                    </span>
                  </div>
                  <div className="rule-details">
                    <div><strong>Type:</strong> {rule.type || 'N/A'}</div>
                    <div><strong>Condition:</strong> {rule.condition ? rule.condition : 'N/A'}</div>
                    <div><strong>Value:</strong> {rule.value || 'N/A'}</div>
                    {rule.description && <div><strong>Description:</strong> {rule.description}</div>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-rules">No rules configured</div>
          )}
        </div>
      )}
    </div>
  );
};

export default RuleEditor;

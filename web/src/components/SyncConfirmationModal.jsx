import React from 'react';

const SyncConfirmationModal = ({ isOpen, onClose, onConfirm, syncPlan }) => {
  if (!isOpen) return null;

  const { to_add, to_update, to_delete } = syncPlan;

  return (
    <div className="modal-overlay">
      <div className="modal-content sync-confirmation-modal">
        <div className="modal-header">
          <h2>Confirm Sync</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p>The following changes will be made:</p>
          
          <div className="sync-summary">
            <div className="sync-item add">
              <span className="sync-count">{to_add.length}</span>
              <span className="sync-label">flags to add</span>
            </div>
            <div className="sync-item update">
              <span className="sync-count">{to_update.length}</span>
              <span className="sync-label">flags to update</span>
            </div>
            <div className="sync-item delete">
              <span className="sync-count">{to_delete.length}</span>
              <span className="sync-label">flags to delete</span>
            </div>
          </div>

          {to_add.length > 0 && (
            <div className="sync-section">
              <h4>Flags to Add:</h4>
              <ul>
                {to_add.map((flag, index) => (
                  <li key={index}>{flag.key}</li>
                ))}
              </ul>
            </div>
          )}

          {to_update.length > 0 && (
            <div className="sync-section">
              <h4>Flags to Update:</h4>
              <ul>
                {to_update.map((flag, index) => (
                  <li key={index}>{flag.key}</li>
                ))}
              </ul>
            </div>
          )}

          {to_delete.length > 0 && (
            <div className="sync-section">
              <h4>Flags to Delete:</h4>
              <ul>
                {to_delete.map((flag, index) => (
                  <li key={index}>{flag.key}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="modal-actions">
          <button className="cancel-button" onClick={onClose}>Cancel</button>
          <button className="confirm-button" onClick={onConfirm}>Confirm Sync</button>
        </div>
      </div>
    </div>
  );
};

export default SyncConfirmationModal;

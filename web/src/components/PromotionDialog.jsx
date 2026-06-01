import React from 'react';

const PromotionDialog = ({ isOpen, onClose, onConfirm, sourceEnv, targetEnv, flagCount }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content promotion-dialog">
        <div className="modal-header">
          <h2>Confirm Promotion</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <p>Are you sure you want to promote <strong>{flagCount}</strong> selected flags from <strong>{sourceEnv}</strong> to <strong>{targetEnv}</strong>?</p>
          <p>This will:</p>
          <ul>
            <li>Create flags that exist in {sourceEnv} but not in {targetEnv}</li>
            <li>Update flags that have different values between environments</li>
          </ul>
        </div>
        <div className="modal-actions">
          <button className="cancel-button" onClick={onClose}>Cancel</button>
          <button className="confirm-button" onClick={onConfirm}>Promote</button>
        </div>
      </div>
    </div>
  );
};

export default PromotionDialog;

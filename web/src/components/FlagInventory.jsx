import React from 'react';

const FlagInventory = ({ flags, onEditFlag }) => {
  if (!flags || flags.length === 0) {
    return <div className="flag-inventory empty">No flags found for this market.</div>;
  }

  return (
    <div className="flag-inventory">
      <h3>Flags Inventory</h3>
      <table className="flags-table">
        <thead>
          <tr>
            <th>Flag Key</th>
            <th>GrowthBook Feature ID</th>
            <th>Updated At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {flags.map((flag) => (
            <tr key={flag.id}>
              <td>{flag.key}</td>
              <td>{flag.growthbook_feature_id}</td>
              <td>{new Date(flag.updated_at).toLocaleString()}</td>
              <td>
                <button onClick={() => onEditFlag(flag)}>Edit</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default FlagInventory;

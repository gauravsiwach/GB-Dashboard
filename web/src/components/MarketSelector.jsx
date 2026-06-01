import React from 'react';

const MarketSelector = ({ markets, selectedMarket, onSelectMarket }) => {
  return (
    <div className="market-selector">
      <label htmlFor="market-select">Select Market:</label>
      <select
        id="market-select"
        value={selectedMarket || ''}
        onChange={(e) => onSelectMarket(e.target.value)}
        disabled={!markets || markets.length === 0}
      >
        <option value="">-- Select a market --</option>
        {markets?.map((market) => (
          <option key={market.id} value={market.id}>
            {market.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default MarketSelector;

import { useState, useEffect } from 'react';
import MarketSelector from './components/MarketSelector';
import FlagInventory from './components/FlagInventory';
import FlagRegistration from './components/FlagRegistration';
import ImportFlagModal from './components/ImportFlagModal';
import ComparisonView from './components/ComparisonView';
import SyncConfirmationModal from './components/SyncConfirmationModal';
import EditFlagModal from './components/EditFlagModal';
import Toast from './components/Toast';
import './App.css';

function App() {
  const [markets, setMarkets] = useState([]);
  const [selectedMarketId, setSelectedMarketId] = useState('');
  const [flags, setFlags] = useState([]);
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [currentView, setCurrentView] = useState('environment');
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);
  const [syncPlan, setSyncPlan] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedFlag, setSelectedFlag] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
  };

  useEffect(() => {
    fetchMarkets();
  }, []);

  useEffect(() => {
    if (selectedMarketId) {
      const market = markets.find(m => m.id === parseInt(selectedMarketId));
      setSelectedMarket(market);
      fetchFlags(selectedMarketId);
    } else {
      setSelectedMarket(null);
      setFlags([]);
    }
  }, [selectedMarketId, markets]);

  const fetchMarkets = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('http://localhost:8000/api/v1/markets');
      if (!response.ok) throw new Error('Failed to fetch markets');
      const data = await response.json();
      setMarkets(data);
      
      // Select the first market by default
      if (data.length > 0) {
        setSelectedMarketId(data[0].id.toString());
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchFlags = async (marketId) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`http://localhost:8000/api/v1/flags?market_id=${marketId}`);
      if (!response.ok) throw new Error('Failed to fetch flags');
      const data = await response.json();
      setFlags(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFlagCreated = (newFlag) => {
    setFlags([...flags, newFlag]);
  };

  const handleImportFlag = (importedFlag) => {
    setFlags([...flags, importedFlag]);
  };

  const handleImportAllFlags = async (importedFlags) => {
    setFlags([...flags, ...importedFlags]);
  };

  const handleImportAll = async () => {
    if (!selectedMarketId) return;
    
    try {
      // First, do a dry run to get the sync plan
      const response = await fetch('http://localhost:8000/api/v1/flags/import-all', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          market_id: parseInt(selectedMarketId),
          dry_run: true,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        // Show confirmation modal with sync plan
        setSyncPlan(data);
        setIsSyncModalOpen(true);
      } else {
        showToast(`Failed to get sync plan: ${data.message}`, 'error');
      }
    } catch (err) {
      showToast(`Error getting sync plan: ${err.message}`, 'error');
    }
  };

  const handleConfirmSync = async () => {
    if (!selectedMarketId || !syncPlan) return;
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/flags/import-all', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          market_id: parseInt(selectedMarketId),
          dry_run: false,
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        showToast(`Sync completed: ${data.imported_count} added, ${data.updated_count} updated, ${data.deleted_count} deleted`);
        fetchFlags(selectedMarketId); // Refresh flags list
      } else {
        showToast(`Failed to sync flags: ${data.message}`, 'error');
      }
    } catch (err) {
      showToast(`Error syncing flags: ${err.message}`, 'error');
    } finally {
      setIsSyncModalOpen(false);
      setSyncPlan(null);
    }
  };

  const handleEditFlag = (flag) => {
    setSelectedFlag(flag);
    setIsEditModalOpen(true);
  };

  return (
    <div className="app">
      <header>
        <h1>Feature Flag Promotion Dashboard</h1>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main>
        <section className="market-section">
          <MarketSelector
            markets={markets}
            selectedMarket={selectedMarketId}
            onSelectMarket={setSelectedMarketId}
          />
        </section>

        {selectedMarket && (
          <>
            <section className="env-flow">
              <h3>Environment Flow: {selectedMarket.env_flow}</h3>
            </section>

            <section className="view-toggle">
              <button
                className={currentView === 'environment' ? 'active' : ''}
                onClick={() => setCurrentView('environment')}
              >
                Flag Inventory
              </button>
              <button
                className={currentView === 'compare' ? 'active' : ''}
                onClick={() => setCurrentView('compare')}
              >
                Environment compare
              </button>
              <button
                className={currentView === 'create' ? 'active' : ''}
                onClick={() => setCurrentView('create')}
              >
                Create New Flag
              </button>
            </section>

            {currentView === 'environment' && (
              <section className="flags-section">
                <div className="section-header">
                  <h3>Flags Inventory</h3>
                  <div className="import-buttons">
                    <button 
                      className="import-button"
                      onClick={() => setIsImportModalOpen(true)}
                    >
                      Import from GrowthBook
                    </button>
                    <button 
                      className="import-all-button"
                      onClick={handleImportAll}
                    >
                      Import All
                    </button>
                  </div>
                </div>
                <FlagInventory
                  flags={flags}
                  onEditFlag={handleEditFlag}
                />
              </section>
            )}

            {currentView === 'compare' && (
              <section className="comparison-section">
                <ComparisonView selectedMarket={selectedMarket} />
              </section>
            )}

            {currentView === 'create' && (
              <section className="registration-section">
                <FlagRegistration
                  selectedMarketId={selectedMarketId}
                  onFlagCreated={handleFlagCreated}
                />
              </section>
            )}
          </>
        )}

        {!selectedMarket && (
          <div className="placeholder">
            <p>Select a market to view and manage flags</p>
          </div>
        )}
      </main>

      <ImportFlagModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImportFlag}
        selectedMarketId={selectedMarketId}
      />
      <SyncConfirmationModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        onConfirm={handleConfirmSync}
        syncPlan={syncPlan}
      />
      <EditFlagModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        flag={selectedFlag}
        selectedMarket={selectedMarket}
        onSuccess={(msg) => showToast(msg, 'success')}
        onError={(msg) => showToast(msg, 'error')}
      />
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;

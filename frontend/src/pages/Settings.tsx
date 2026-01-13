import { useState } from 'react';
import { Eye, EyeOff, ExternalLink, Check, Trash2, Key } from 'lucide-react';
import { useApiKeys, API_KEY_INFO, type ApiKeyService } from '../contexts/ApiKeyContext';

interface ApiKeyInputProps {
  service: ApiKeyService;
}

function ApiKeyInput({ service }: ApiKeyInputProps) {
  const { getApiKey, setApiKey, clearApiKey, hasApiKey } = useApiKeys();
  const [inputValue, setInputValue] = useState(getApiKey(service) || '');
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);

  const info = API_KEY_INFO[service];
  const isConfigured = hasApiKey(service);

  const handleSave = () => {
    if (inputValue.trim()) {
      setApiKey(service, inputValue.trim());
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  const handleClear = () => {
    clearApiKey(service);
    setInputValue('');
  };

  return (
    <div className="api-key-card">
      <div className="api-key-header">
        <div className="api-key-title">
          <Key size={18} />
          <h3>{info.name}</h3>
          {isConfigured && (
            <span className="api-key-badge configured">Configured</span>
          )}
        </div>
        <a href={info.url} target="_blank" rel="noopener noreferrer" className="api-key-link">
          Get API Key <ExternalLink size={14} />
        </a>
      </div>

      <p className="api-key-description">{info.description}</p>

      <div className="api-key-input-group">
        <div className="input-wrapper">
          <input
            type={showKey ? 'text' : 'password'}
            className="form-input"
            placeholder="Enter your API key..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
          />
          <button
            type="button"
            className="input-icon-btn"
            onClick={() => setShowKey(!showKey)}
            title={showKey ? 'Hide key' : 'Show key'}
          >
            {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <div className="api-key-actions">
          <button
            className={`btn btn-primary ${saved ? 'btn-success' : ''}`}
            onClick={handleSave}
            disabled={!inputValue.trim()}
          >
            {saved ? <><Check size={16} /> Saved</> : 'Save'}
          </button>
          {isConfigured && (
            <button className="btn btn-secondary" onClick={handleClear}>
              <Trash2 size={16} /> Clear
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Settings() {
  return (
    <div className="settings-page">
      <div className="page-header">
        <h1>Settings</h1>
        <p>Configure API keys for external data sources. Keys are stored locally in your browser.</p>
      </div>

      <div className="settings-section">
        <h2>API Keys</h2>
        <p className="section-description">
          Some data sources require API keys for access. Your keys are stored securely in your browser's
          local storage and are never sent to our servers.
        </p>

        <div className="api-keys-list">
          <ApiKeyInput service="renewablesNinja" />
          <ApiKeyInput service="era5Cds" />
        </div>
      </div>

      <div className="settings-section">
        <h2>About Data Storage</h2>
        <div className="info-card">
          <p>
            <strong>Privacy:</strong> API keys are stored only in your browser's localStorage.
            They are included in requests to fetch data from external APIs but are not stored on any server.
          </p>
          <p>
            <strong>Clearing data:</strong> To remove all stored settings, you can clear your browser's
            local storage or use the Clear buttons above for individual keys.
          </p>
        </div>
      </div>
    </div>
  );
}

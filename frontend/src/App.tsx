import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Link, NavLink } from 'react-router-dom';
import { Database, Map, BarChart3, Info, ShieldCheck, Settings as SettingsIcon, Code, Download } from 'lucide-react';
import { ApiKeyProvider } from './contexts/ApiKeyContext';
import { LoadingProvider, useLoading } from './contexts/LoadingContext';
import LoadingProgress from './components/LoadingProgress';
import DataExplorer from './pages/DataExplorer';
import Catalog from './pages/Catalog';
import About from './pages/About';
import DataQuality from './pages/DataQuality';
import Settings from './pages/Settings';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function AppContent() {
  return (
    <div className="app">
      <header className="header">
              <Link to="/" className="logo">
                <Database size={24} />
                <span>OpenEnergyData</span>
              </Link>
              <nav className="nav">
                <div className="nav-main">
                  <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                    <Map size={18} />
                    Explorer
                  </NavLink>
                  <NavLink to="/catalog" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                    <BarChart3 size={18} />
                    Catalog
                  </NavLink>
                </div>
                <div className="nav-utility">
                  <NavLink to="/quality" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                    <ShieldCheck size={18} />
                    Data Quality
                  </NavLink>
                  <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer" className="nav-link">
                    <Code size={18} />
                    API
                  </a>
                  <div className="nav-dropdown">
                    <button className="nav-link nav-dropdown-trigger">
                      <Download size={18} />
                      Export
                    </button>
                    <div className="nav-dropdown-content">
                      <a href={`${API_BASE_URL}/api/exports/power-plants/csv?region=sapp`} download>
                        Power Plants (CSV)
                      </a>
                      <a href={`${API_BASE_URL}/api/exports/power-plants/geojson?region=sapp`} download>
                        Power Plants (GeoJSON)
                      </a>
                      <a href={`${API_BASE_URL}/api/exports/load-profiles/csv?region=sapp&year=2020`} download>
                        Load Profiles (CSV)
                      </a>
                    </div>
                  </div>
                  <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                    <SettingsIcon size={18} />
                    Settings
                  </NavLink>
                  <NavLink to="/about" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                    <Info size={18} />
                    About
                  </NavLink>
                </div>
              </nav>
            </header>

            <main className="main">
              <Routes>
                <Route path="/" element={<DataExplorer />} />
                <Route path="/quality" element={<DataQuality />} />
                <Route path="/catalog" element={<Catalog />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/about" element={<About />} />
              </Routes>
            </main>
          </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ApiKeyProvider>
        <LoadingProvider>
          <BrowserRouter>
            <AppWithLoading />
          </BrowserRouter>
        </LoadingProvider>
      </ApiKeyProvider>
    </QueryClientProvider>
  );
}

function AppWithLoading() {
  const { isLoading, loadingMessage } = useLoading();

  return (
    <>
      <LoadingProgress isVisible={isLoading} message={loadingMessage} />
      <AppContent />
    </>
  );
}

export default App;

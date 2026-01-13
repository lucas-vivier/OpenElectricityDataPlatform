import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Link, NavLink } from 'react-router-dom';
import { Database, Map, BarChart3, Info } from 'lucide-react';
import DataExplorer from './pages/DataExplorer';
import Catalog from './pages/Catalog';
import About from './pages/About';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app">
          <header className="header">
            <Link to="/" className="logo">
              <Database size={24} />
              <span>OpenEnergyData</span>
            </Link>
            <nav className="nav">
              <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <Map size={18} />
                Explorer
              </NavLink>
              <NavLink to="/catalog" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <BarChart3 size={18} />
                Catalog
              </NavLink>
              <NavLink to="/about" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <Info size={18} />
                About
              </NavLink>
            </nav>
          </header>

          <main className="main">
            <Routes>
              <Route path="/" element={<DataExplorer />} />
              <Route path="/catalog" element={<Catalog />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

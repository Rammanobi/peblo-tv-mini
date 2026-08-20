import React from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './lib/AuthContext';
import LoginPage from './pages/LoginPage';
import ShowListPage from './pages/ShowListPage';
import ShowFormPage from './pages/ShowFormPage';
import EpisodeFormPage from './pages/EpisodeFormPage';
import PublishPage from './pages/PublishPage';
import { LoadingState } from './components/DataState';

function RequireAuth({ children }: { children: React.ReactElement }) {
  const { status } = useAuth();
  if (status === 'loading') return <LoadingState label="Checking session..." />;
  if (status === 'anonymous') return <Navigate to="/login" replace />;
  return children;
}

function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout, status } = useAuth();
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-brand">Peblo TV — CMS</div>
        {status === 'authenticated' && (
          <nav className="app-nav">
            <NavLink to="/shows" className={({ isActive }) => (isActive ? 'active' : '')}>
              Shows
            </NavLink>
            <NavLink to="/publish" className={({ isActive }) => (isActive ? 'active' : '')}>
              Publish
            </NavLink>
          </nav>
        )}
        {user && (
          <div className="app-header-user">
            <span>
              {user.name} <span className="badge">{user.role}</span>
            </span>
            <button className="btn btn-link" onClick={logout} type="button">
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route path="/" element={<Navigate to="/shows" replace />} />
                <Route path="/shows" element={<ShowListPage />} />
                <Route path="/shows/new" element={<ShowFormPage />} />
                <Route path="/shows/:showId" element={<ShowFormPage />} />
                <Route
                  path="/shows/:showId/seasons/:seasonId/episodes/new"
                  element={<EpisodeFormPage />}
                />
                <Route path="/episodes/:episodeId" element={<EpisodeFormPage />} />
                <Route path="/publish" element={<PublishPage />} />
                <Route path="*" element={<Navigate to="/shows" replace />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}

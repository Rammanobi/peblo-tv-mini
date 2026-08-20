import { Routes, Route } from "react-router-dom";
import { NavBar } from "./components/NavBar";
import { HomePage } from "./pages/HomePage";
import { SearchPage } from "./pages/SearchPage";
import { ShowDetailPage } from "./pages/ShowDetailPage";

export function App() {
  return (
    <div className="app-shell">
      <NavBar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/shows/:slug" element={<ShowDetailPage />} />
          <Route
            path="*"
            element={
              <div className="state-panel state-panel--empty">
                <span className="state-panel__icon">🧭</span>
                <h2>Page not found</h2>
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

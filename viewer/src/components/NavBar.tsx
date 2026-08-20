import { Link, NavLink } from "react-router-dom";

export function NavBar() {
  return (
    <header className="navbar">
      <Link to="/" className="navbar__brand">
        Peblo<span>TV</span>
      </Link>
      <nav className="navbar__links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Home
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => (isActive ? "active" : "")}>
          Search
        </NavLink>
      </nav>
    </header>
  );
}

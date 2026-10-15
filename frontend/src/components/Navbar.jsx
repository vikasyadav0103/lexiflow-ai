import React from "react";
import { Link, useLocation } from "react-router-dom";
import "./Navbar.css";

const Navbar = () => {
  const location = useLocation();

  const links = [
    { to: "/", label: "Search" },
    { to: "/analysis", label: "Analysis" },
    { to: "/history", label: "History" },
    { to: "/frequency", label: "Frequency" },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="navbar-logo">LexiFlow AI</Link>
      </div>
      <div className="navbar-links">
        {links.map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            className={`nav-link ${location.pathname === to ? "active" : ""}`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
};

export default Navbar;

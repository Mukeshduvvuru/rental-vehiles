/**
 * components/Navbar.jsx — Top navigation bar
 *
 * Reads auth state from AuthContext to show role-appropriate navigation links.
 * No props needed — Context does all the heavy lifting.
 *
 * NAVIGATION BY ROLE:
 *   Guest      : Browse Vehicles | Login | Register
 *   Customer   : Browse Vehicles | My Rentals | Logout
 *   Admin      : Browse Vehicles | Admin Dashboard | Fleet Dashboard | Logout
 *   Fleet Mgr  : Browse Vehicles | Fleet Dashboard | Logout
 *
 * WHY useNavigate instead of <Link> for logout?
 *   After calling logout() we want to programmatically redirect to /login.
 *   <Link> is for static navigation; useNavigate() is for conditional/programmatic.
 */

import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout, isAdmin, isFleetManager } = useAuth();
  const navigate  = useNavigate();
  const location  = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // ── Logout handler ─────────────────────────────────────────
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // ── Active link helper (highlights current page in nav) ───
  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  // ── Role badge label ────────────────────────────────────────
  const getRoleBadge = () => {
    if (isAdmin())        return { label: 'Admin',        color: '#e74c3c' };
    if (isFleetManager()) return { label: 'Fleet',        color: '#3498db' };
    return                       { label: 'Customer',     color: '#2ecc71' };
  };

  return (
    <nav style={styles.nav}>
      <div style={styles.inner}>
        {/* ── Brand logo ─────────────────────────────────── */}
        <Link to="/" style={styles.brand}>
          <span style={styles.brandIcon}>🚗</span>
          <span>Drive<span style={{ color: '#f4a261' }}>Easy</span></span>
        </Link>

        {/* ── Desktop nav links ──────────────────────────── */}
        <div style={styles.links}>
          <Link
            to="/vehicles"
            style={{ ...styles.link, ...(isActive('/vehicles') ? styles.linkActive : {}) }}
          >
            Browse Vehicles
          </Link>

          {user && user.role === 'customer' && (
            <Link
              to="/my-rentals"
              style={{ ...styles.link, ...(isActive('/my-rentals') ? styles.linkActive : {}) }}
            >
              My Rentals
            </Link>
          )}

          {(isAdmin() || isFleetManager()) && (
            <Link
              to="/fleet"
              style={{ ...styles.link, ...(isActive('/fleet') ? styles.linkActive : {}) }}
            >
              Fleet Dashboard
            </Link>
          )}

          {isAdmin() && (
            <Link
              to="/admin"
              style={{ ...styles.link, ...(isActive('/admin') ? styles.linkActive : {}) }}
            >
              Admin Panel
            </Link>
          )}
        </div>

        {/* ── Auth section ───────────────────────────────── */}
        <div style={styles.authSection}>
          {user ? (
            /* Logged-in user info + logout */
            <div style={styles.userInfo}>
              <div style={styles.userDetails}>
                <span style={styles.userName}>{user.name.split(' ')[0]}</span>
                <span style={{
                  ...styles.roleBadge,
                  background: getRoleBadge().color + '22',
                  color: getRoleBadge().color,
                }}>
                  {getRoleBadge().label}
                </span>
              </div>
              <button onClick={handleLogout} style={styles.logoutBtn}>
                Logout
              </button>
            </div>
          ) : (
            /* Guest: login + register */
            <div style={styles.guestLinks}>
              <Link to="/login"    style={styles.loginBtn}>Login</Link>
              <Link to="/register" style={styles.registerBtn}>Sign Up</Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

/* ── Inline styles for navbar ──────────────────────────────────
   Why inline styles here?
   - Navbar styles are tightly coupled to this component
   - No risk of CSS class name collisions
   - Self-contained component
*/
const styles = {
  nav: {
    background: '#1a1a2e',
    boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
    position: 'sticky',
    top: 0,
    zIndex: 1000,
    height: '70px',
  },
  inner: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '24px',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    color: '#ffffff',
    textDecoration: 'none',
    fontSize: '1.4rem',
    fontWeight: '800',
    letterSpacing: '-0.5px',
    flexShrink: 0,
  },
  brandIcon: { fontSize: '1.6rem' },
  links: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    flex: 1,
  },
  link: {
    color: '#a0aec0',
    textDecoration: 'none',
    padding: '8px 14px',
    borderRadius: '8px',
    fontSize: '0.9rem',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  linkActive: {
    color: '#f4a261',
    background: 'rgba(244,162,97,0.12)',
  },
  authSection: {
    display: 'flex',
    alignItems: 'center',
    flexShrink: 0,
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  userDetails: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
  },
  userName: {
    color: '#ffffff',
    fontSize: '0.9rem',
    fontWeight: '600',
  },
  roleBadge: {
    fontSize: '0.7rem',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '20px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  logoutBtn: {
    background: 'rgba(231,76,60,0.15)',
    color: '#e74c3c',
    border: '1px solid rgba(231,76,60,0.3)',
    padding: '7px 16px',
    borderRadius: '8px',
    fontSize: '0.85rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  guestLinks: {
    display: 'flex',
    gap: '10px',
  },
  loginBtn: {
    color: '#a0aec0',
    textDecoration: 'none',
    padding: '8px 16px',
    borderRadius: '8px',
    fontSize: '0.9rem',
    fontWeight: '500',
    border: '1px solid rgba(255,255,255,0.1)',
    transition: 'all 0.2s',
  },
  registerBtn: {
    background: '#f4a261',
    color: '#ffffff',
    textDecoration: 'none',
    padding: '8px 16px',
    borderRadius: '8px',
    fontSize: '0.9rem',
    fontWeight: '600',
    transition: 'all 0.2s',
  },
};

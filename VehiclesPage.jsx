/**
 * context/AuthContext.js — Global authentication state
 *
 * WHY REACT CONTEXT?
 *   Without Context, every component that needs to know "is the user logged in?"
 *   or "what role are they?" must receive those values via props — passed down
 *   through every intermediate component. This is called "prop drilling" and
 *   becomes painful in deep component trees.
 *
 *   Context solves this: we store auth state in one place, and ANY component
 *   in the tree can read it with useContext(AuthContext) — no prop drilling.
 *
 * WHAT THIS CONTEXT PROVIDES:
 *   - user      → the currently logged-in user object (or null)
 *   - token     → the JWT string (or null)
 *   - login()   → call after successful API /login; stores user + token
 *   - logout()  → clears state and localStorage
 *   - isAdmin() → convenience boolean check
 *   - isFleet() → convenience boolean check
 *
 * PERSISTENCE:
 *   Token is saved to localStorage so the user stays logged in after
 *   a page refresh. On mount, we read localStorage to restore session.
 *
 * WHY localStorage AND NOT cookies?
 *   For a hackathon demo, localStorage is simpler to implement.
 *   In production you'd use httpOnly cookies for better XSS resistance.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

// Create the context — null is the default before the Provider renders
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // user  = full user object from API (id, name, email, role, etc.)
  // token = the JWT string
  const [user,  setUser]  = useState(null);
  const [token, setToken] = useState(null);

  // ── Restore session on page refresh ────────────────────────
  useEffect(() => {
    const savedToken = localStorage.getItem('rental_token');
    const savedUser  = localStorage.getItem('rental_user');

    if (savedToken && savedUser) {
      const parsedUser = JSON.parse(savedUser);
      setToken(savedToken);
      setUser(parsedUser);
      // Set the default Authorization header for all future API calls
      api.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
    }
  }, []);

  // ── Login ───────────────────────────────────────────────────
  /**
   * Called by LoginPage after a successful POST /api/auth/login.
   * Stores the token and user in state AND localStorage.
   *
   * Also sets the Axios default header so every subsequent API call
   * automatically includes: Authorization: Bearer <token>
   */
  const login = (userData, jwtToken) => {
    setUser(userData);
    setToken(jwtToken);

    localStorage.setItem('rental_token', jwtToken);
    localStorage.setItem('rental_user',  JSON.stringify(userData));

    // Set default Axios header — no need to pass token to every api call
    api.defaults.headers.common['Authorization'] = `Bearer ${jwtToken}`;
  };

  // ── Logout ──────────────────────────────────────────────────
  /**
   * Clears all auth state. The user is redirected to /login by the
   * ProtectedRoute component (which watches for null user).
   */
  const logout = () => {
    setUser(null);
    setToken(null);

    localStorage.removeItem('rental_token');
    localStorage.removeItem('rental_user');

    delete api.defaults.headers.common['Authorization'];
  };

  // ── Convenience role helpers ─────────────────────────────────
  const isAdmin        = () => user?.role === 'admin';
  const isFleetManager = () => user?.role === 'fleet_manager';
  const isCustomer     = () => user?.role === 'customer';

  // Provide all auth state and helpers to the entire component tree
  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAdmin, isFleetManager, isCustomer }}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Custom hook for consuming auth context.
 * Usage anywhere in the app:
 *   const { user, logout, isAdmin } = useAuth();
 */
export function useAuth() {
  return useContext(AuthContext);
}

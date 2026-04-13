/**
 * components/ProtectedRoute.jsx — Authentication & role guard
 *
 * WHY DO WE NEED THIS?
 *   React Router renders whatever component matches the URL.
 *   Without a guard, typing /admin in the browser would render
 *   AdminDashboard even if you're not logged in or not an admin.
 *
 * HOW IT WORKS:
 *   1. Read current user from AuthContext
 *   2. Not logged in → redirect to /login (preserve the intended URL)
 *   3. Logged in but wrong role → redirect to /vehicles with error
 *   4. Correct role → render the protected component
 *
 * USAGE (in App.js):
 *   <Route path="/admin" element={
 *     <ProtectedRoute roles={['admin']}>
 *       <AdminDashboard />
 *     </ProtectedRoute>
 *   } />
 *
 * The 'roles' prop is an array so one route can allow multiple roles:
 *   roles={['admin', 'fleet_manager']}
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children, roles = [] }) {
  const { user } = useAuth();
  const location = useLocation();   // current URL — used to redirect back after login

  // ── Not authenticated ─────────────────────────────────────────
  if (!user) {
    /**
     * <Navigate> performs a client-side redirect.
     * state={{ from: location }} passes the current URL to the login page,
     * so after login the user is sent to where they were trying to go.
     * replace={true} replaces the history entry (Back button won't return
     * to the protected page once redirected to login).
     */
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // ── Authenticated but wrong role ──────────────────────────────
  if (roles.length > 0 && !roles.includes(user.role)) {
    // Redirect to the appropriate home for their actual role
    const fallback = user.role === 'admin' ? '/admin'
                   : user.role === 'fleet_manager' ? '/fleet'
                   : '/vehicles';
    return <Navigate to={fallback} replace />;
  }

  // ── Authorized — render the protected page ───────────────────
  return children;
}

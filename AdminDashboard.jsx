/**
 * App.js — Root component: routing & layout
 *
 * WHY REACT ROUTER v6?
 *   React apps are Single Page Applications (SPA) — the browser loads ONE HTML
 *   page, and React swaps content based on the URL without full page reloads.
 *   React Router intercepts URL changes and renders the matching component.
 *
 *   v6 improvements over v5:
 *   - <Routes> replaces <Switch> — more predictable matching
 *   - Nested routes are declarative (no need for useRouteMatch)
 *   - useNavigate() replaces useHistory()
 *
 * ROUTE STRUCTURE:
 *   /             → redirect to /vehicles (or /login if not authenticated)
 *   /login        → LoginPage
 *   /register     → RegisterPage
 *   /vehicles     → VehiclesPage (browse & filter)        [customer + public]
 *   /vehicles/:id → BookingPage (book a specific vehicle) [customer only]
 *   /my-rentals   → MyRentalsPage (booking history)       [customer only]
 *   /admin        → AdminDashboard                        [admin only]
 *   /fleet        → FleetDashboard                        [fleet_manager + admin]
 *
 * PROTECTED ROUTES:
 *   <ProtectedRoute> wraps any route that requires authentication.
 *   It reads from AuthContext — if not logged in, redirects to /login.
 *   The 'roles' prop further restricts to specific roles.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// Layout
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import LoginPage      from './pages/LoginPage';
import RegisterPage   from './pages/RegisterPage';
import VehiclesPage   from './pages/VehiclesPage';
import BookingPage    from './pages/BookingPage';
import MyRentalsPage  from './pages/MyRentalsPage';
import AdminDashboard from './pages/AdminDashboard';
import FleetDashboard from './pages/FleetDashboard';

export default function App() {
  return (
    /**
     * AuthProvider wraps everything so every child component can access
     * auth state via useAuth() hook — no prop drilling needed.
     *
     * BrowserRouter uses the HTML5 History API for clean URLs (/vehicles, /login).
     * (vs HashRouter which uses /# prefix — less clean but no server config needed)
     */
    <AuthProvider>
      <BrowserRouter>
        {/* Navbar is always visible — it reads auth state to show/hide items */}
        <Navbar />

        <Routes>
          {/* Public routes — accessible without login */}
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Semi-public: vehicles list is public, but booking requires login */}
          <Route path="/vehicles" element={<VehiclesPage />} />

          {/* Customer-only routes */}
          <Route
            path="/vehicles/:vehicleId/book"
            element={
              <ProtectedRoute roles={['customer']}>
                <BookingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-rentals"
            element={
              <ProtectedRoute roles={['customer']}>
                <MyRentalsPage />
              </ProtectedRoute>
            }
          />

          {/* Admin-only dashboard */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Fleet manager + admin */}
          <Route
            path="/fleet"
            element={
              <ProtectedRoute roles={['fleet_manager', 'admin']}>
                <FleetDashboard />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/vehicles" replace />} />
          {/* Catch-all 404 */}
          <Route path="*" element={<Navigate to="/vehicles" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

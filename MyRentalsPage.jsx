/**
 * components/VehicleCard.jsx — Individual vehicle display card
 *
 * Reusable card component used on the VehiclesPage grid.
 * Displays vehicle photo, key specs, price, status badge, and a Book button.
 *
 * WHY A SEPARATE COMPONENT?
 *   VehiclesPage might show 20+ vehicles. If the card markup lived inside
 *   VehiclesPage, that file would become enormous. Extracting to a component:
 *   - Makes each piece independently testable
 *   - Can be reused on other pages (admin vehicle list, search results, etc.)
 *   - Props interface clearly documents what data the card needs
 *
 * PROPS:
 *   vehicle   — the full vehicle object from the API
 *   onBook    — callback function called when "Book Now" is clicked
 *               (VehiclesPage handles navigation; card just triggers it)
 */

import React from 'react';

/* Maps fuel type to an emoji for visual scanning */
const fuelEmoji = {
  petrol: '⛽',
  diesel: '🛢️',
  electric: '⚡',
  hybrid: '🔋',
  cng: '🌿',
};

/* Maps vehicle type to an emoji */
const typeEmoji = {
  car: '🚗',
  suv: '🚙',
  bike: '🏍️',
  van: '🚌',
  truck: '🚛',
};

export default function VehicleCard({ vehicle, onBook }) {
  // ── Status badge config ──────────────────────────────────────
  const statusConfig = {
    available:         { label: 'Available',      class: 'badge-available' },
    rented:            { label: 'Currently Rented', class: 'badge-rented' },
    under_maintenance: { label: 'Maintenance',    class: 'badge-maintenance' },
    inactive:          { label: 'Inactive',        class: 'badge-inactive' },
  };
  const status = statusConfig[vehicle.status] || statusConfig.inactive;

  const isAvailable = vehicle.status === 'available';

  return (
    <div className="card" style={cardStyles.container}>
      {/* ── Vehicle Photo ─────────────────────────────────── */}
      <div style={cardStyles.imageWrapper}>
        <img
          src={
            vehicle.photo_path
              ? `http://localhost:8000${vehicle.photo_path}`
              : `https://via.placeholder.com/400x200?text=${vehicle.brand}+${vehicle.model}`
          }
          alt={`${vehicle.brand} ${vehicle.model}`}
          style={cardStyles.image}
          onError={(e) => {
            /* If photo fails to load, show a placeholder */
            e.target.src = `https://via.placeholder.com/400x200/1a1a2e/ffffff?text=${encodeURIComponent(vehicle.brand)}`;
          }}
        />
        {/* Status badge overlaid on photo */}
        <span className={`badge ${status.class}`} style={cardStyles.statusBadge}>
          {status.label}
        </span>
        {/* Vehicle type emoji badge */}
        <span style={cardStyles.typeBadge}>
          {typeEmoji[vehicle.vehicle_type] || '🚗'}
        </span>
      </div>

      {/* ── Card body ─────────────────────────────────────── */}
      <div className="card-body" style={cardStyles.body}>
        {/* Title */}
        <h3 style={cardStyles.title}>
          {vehicle.brand} {vehicle.model}
          {vehicle.year && <span style={cardStyles.year}> '{String(vehicle.year).slice(2)}</span>}
        </h3>

        {/* Quick specs row */}
        <div style={cardStyles.specs}>
          <span style={cardStyles.spec}>
            👥 {vehicle.seating_capacity} seats
          </span>
          <span style={cardStyles.spec}>
            {fuelEmoji[vehicle.fuel_type]} {vehicle.fuel_type}
          </span>
          <span style={cardStyles.spec}>
            📍 {vehicle.location}
          </span>
        </div>

        {/* Description */}
        {vehicle.description && (
          <p style={cardStyles.description}>
            {vehicle.description.length > 80
              ? vehicle.description.slice(0, 80) + '…'
              : vehicle.description}
          </p>
        )}

        {/* ── Pricing + CTA ───────────────────────────────── */}
        <div style={cardStyles.footer}>
          <div style={cardStyles.pricing}>
            <div style={cardStyles.priceMain}>
              ₹{vehicle.price_per_day.toLocaleString()}
              <span style={cardStyles.priceUnit}>/day</span>
            </div>
            <div style={cardStyles.priceSub}>
              ₹{vehicle.price_per_hour}/hr
            </div>
          </div>

          <button
            className={`btn ${isAvailable ? 'btn-primary' : ''}`}
            style={isAvailable ? cardStyles.bookBtn : cardStyles.disabledBtn}
            onClick={() => isAvailable && onBook(vehicle)}
            disabled={!isAvailable}
          >
            {isAvailable ? 'Book Now' : 'Unavailable'}
          </button>
        </div>
      </div>
    </div>
  );
}

const cardStyles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
  },
  imageWrapper: {
    position: 'relative',
    height: '180px',
    overflow: 'hidden',
    background: '#f0f2f5',
  },
  image: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transition: 'transform 0.3s ease',
  },
  statusBadge: {
    position: 'absolute',
    top: '10px',
    right: '10px',
  },
  typeBadge: {
    position: 'absolute',
    top: '10px',
    left: '10px',
    background: 'rgba(255,255,255,0.9)',
    padding: '4px 8px',
    borderRadius: '8px',
    fontSize: '1.2rem',
  },
  body: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  title: {
    fontSize: '1.1rem',
    fontWeight: '700',
    color: '#1a1a2e',
    lineHeight: '1.2',
  },
  year: {
    color: '#6b7280',
    fontWeight: '400',
    fontSize: '0.9rem',
  },
  specs: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
  },
  spec: {
    fontSize: '0.78rem',
    color: '#6b7280',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center',
    gap: '3px',
  },
  description: {
    fontSize: '0.82rem',
    color: '#6b7280',
    lineHeight: '1.5',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 'auto',
    paddingTop: '10px',
    borderTop: '1px solid #f0f2f5',
  },
  pricing: {
    display: 'flex',
    flexDirection: 'column',
  },
  priceMain: {
    fontSize: '1.3rem',
    fontWeight: '800',
    color: '#1a1a2e',
  },
  priceUnit: {
    fontSize: '0.8rem',
    fontWeight: '500',
    color: '#6b7280',
  },
  priceSub: {
    fontSize: '0.75rem',
    color: '#9ca3af',
  },
  bookBtn: {
    padding: '8px 18px',
    fontSize: '0.85rem',
  },
  disabledBtn: {
    padding: '8px 18px',
    fontSize: '0.85rem',
    background: '#f3f4f6',
    color: '#9ca3af',
    border: 'none',
    borderRadius: '8px',
    cursor: 'not-allowed',
    fontWeight: '600',
  },
};

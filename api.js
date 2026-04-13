/*
  index.css — Global styles & CSS design system

  WHY CSS CUSTOM PROPERTIES (variables)?
    Define colors/spacing once at :root, use everywhere.
    Changing --primary from blue to green updates the entire site.
    No need for a CSS preprocessor like Sass.

  DESIGN DECISIONS:
    - Dark navy primary color (#1a1a2e) — professional, automotive feel
    - Accent orange (#f4a261) — energy, warmth, calls to action
    - Card-based layout with subtle shadows for depth
    - 8px spacing unit for consistent rhythm
    - Smooth transitions on all interactive elements
*/

/* ── Reset & Base ─────────────────────────────────────── */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  /* Color palette */
  --primary:       #1a1a2e;    /* deep navy — header, sidebar */
  --primary-light: #16213e;    /* slightly lighter navy */
  --accent:        #f4a261;    /* orange — buttons, highlights */
  --accent-dark:   #e76f51;    /* darker orange for hover */
  --success:       #2ecc71;    /* green — available, success */
  --warning:       #f39c12;    /* yellow — maintenance, warning */
  --danger:        #e74c3c;    /* red — errors, danger */
  --info:          #3498db;    /* blue — info, links */
  --text-primary:  #1a1a2e;    /* main text on white bg */
  --text-secondary:#6b7280;    /* muted text */
  --text-white:    #ffffff;
  --bg-page:       #f0f2f5;    /* light grey page background */
  --bg-card:       #ffffff;    /* white card background */
  --border:        #e5e7eb;    /* subtle borders */
  --border-focus:  #f4a261;    /* orange focus ring */

  /* Spacing */
  --space-xs:  4px;
  --space-sm:  8px;
  --space-md:  16px;
  --space-lg:  24px;
  --space-xl:  32px;
  --space-2xl: 48px;

  /* Border radius */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0,0,0,.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,.10);
  --shadow-lg: 0 8px 24px rgba(0,0,0,.12);
  --shadow-card: 0 2px 8px rgba(26,26,46,.08);

  /* Typography */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-sm:  0.875rem;   /* 14px */
  --font-md:  1rem;       /* 16px */
  --font-lg:  1.125rem;   /* 18px */
  --font-xl:  1.25rem;    /* 20px */
  --font-2xl: 1.5rem;     /* 24px */
  --font-3xl: 2rem;       /* 32px */

  /* Transitions */
  --transition: all 0.2s ease;
}

html {
  font-size: 16px;
  scroll-behavior: smooth;
}

body {
  font-family: var(--font-family);
  background-color: var(--bg-page);
  color: var(--text-primary);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ── Typography ───────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
}

a {
  color: var(--accent);
  text-decoration: none;
  transition: var(--transition);
}

a:hover { color: var(--accent-dark); }

/* ── Layout utilities ─────────────────────────────────── */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

.page-wrapper {
  min-height: calc(100vh - 70px);  /* subtract navbar height */
  padding: var(--space-xl) 0;
}

.flex          { display: flex; }
.flex-center   { display: flex; align-items: center; justify-content: center; }
.flex-between  { display: flex; align-items: center; justify-content: space-between; }
.flex-col      { display: flex; flex-direction: column; }
.gap-sm        { gap: var(--space-sm); }
.gap-md        { gap: var(--space-md); }
.gap-lg        { gap: var(--space-lg); }

.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-lg); }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-lg); }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-lg); }

/* ── Card ─────────────────────────────────────────────── */
.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
  overflow: hidden;
  transition: var(--transition);
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.card-body    { padding: var(--space-lg); }
.card-header  {
  padding: var(--space-lg);
  border-bottom: 1px solid var(--border);
  background: var(--bg-page);
}

/* ── Buttons ──────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-size: var(--font-md);
  font-weight: 600;
  font-family: var(--font-family);
  cursor: pointer;
  border: none;
  transition: var(--transition);
  text-decoration: none;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent);
  color: var(--text-white);
}
.btn-primary:hover:not(:disabled) {
  background: var(--accent-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(244,162,97,.4);
}

.btn-secondary {
  background: transparent;
  color: var(--accent);
  border: 2px solid var(--accent);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--accent);
  color: var(--text-white);
}

.btn-danger {
  background: var(--danger);
  color: var(--text-white);
}
.btn-danger:hover:not(:disabled) {
  background: #c0392b;
}

.btn-success {
  background: var(--success);
  color: var(--text-white);
}

.btn-sm {
  padding: 6px 14px;
  font-size: var(--font-sm);
}

.btn-lg {
  padding: 14px 28px;
  font-size: var(--font-lg);
}

.btn-full { width: 100%; justify-content: center; }

/* ── Form elements ────────────────────────────────────── */
.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  margin-bottom: var(--space-md);
}

.form-label {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.form-input,
.form-select {
  padding: 10px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: var(--font-md);
  font-family: var(--font-family);
  color: var(--text-primary);
  background: var(--bg-card);
  transition: var(--transition);
  width: 100%;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(244,162,97,.15);
}

/* ── Status badges ────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-available  { background: #d1fae5; color: #065f46; }
.badge-rented     { background: #dbeafe; color: #1e40af; }
.badge-maintenance{ background: #fef3c7; color: #92400e; }
.badge-inactive   { background: #f3f4f6; color: #6b7280; }
.badge-booked     { background: #ede9fe; color: #5b21b6; }
.badge-picked_up  { background: #dbeafe; color: #1e40af; }
.badge-returned   { background: #d1fae5; color: #065f46; }
.badge-cancelled  { background: #fee2e2; color: #991b1b; }
.badge-completed  { background: #d1fae5; color: #065f46; }
.badge-pending    { background: #fef3c7; color: #92400e; }

/* ── Stat card (dashboard) ────────────────────────────── */
.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.stat-card .stat-icon {
  font-size: 2rem;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-sm);
}

.stat-card .stat-value {
  font-size: var(--font-3xl);
  font-weight: 800;
  color: var(--text-primary);
}

.stat-card .stat-label {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

/* ── Alert / message ──────────────────────────────────── */
.alert {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  font-size: var(--font-sm);
  font-weight: 500;
  margin-bottom: var(--space-md);
}

.alert-error   { background: #fee2e2; color: #991b1b; border-left: 4px solid var(--danger); }
.alert-success { background: #d1fae5; color: #065f46; border-left: 4px solid var(--success); }
.alert-info    { background: #dbeafe; color: #1e40af; border-left: 4px solid var(--info); }

/* ── Loading spinner ──────────────────────────────────── */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-center {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

/* ── Table ────────────────────────────────────────────── */
.table-wrapper {
  overflow-x: auto;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-card);
}

thead {
  background: var(--primary);
  color: var(--text-white);
}

th, td {
  padding: 12px 16px;
  text-align: left;
  font-size: var(--font-sm);
}

th { font-weight: 600; }

tbody tr { border-bottom: 1px solid var(--border); }
tbody tr:hover { background: #f9fafb; }
tbody tr:last-child { border-bottom: none; }

/* ── Section title ────────────────────────────────────── */
.section-title {
  font-size: var(--font-2xl);
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: var(--space-lg);
}

.section-title span { color: var(--accent); }

/* ── Responsive ───────────────────────────────────────── */
@media (max-width: 768px) {
  .grid-3, .grid-4 { grid-template-columns: repeat(2, 1fr); }
  .grid-2          { grid-template-columns: 1fr; }
  .container       { padding: 0 var(--space-md); }
}

@media (max-width: 480px) {
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
}

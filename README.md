/**
 * index.js — React application bootstrap
 *
 * This is the first JS file that runs. It:
 *   1. Imports React and ReactDOM
 *   2. Imports our global CSS
 *   3. Renders <App /> into the #root div in public/index.html
 *
 * React.StrictMode is a development tool that:
 *   - Highlights potential problems by intentionally double-rendering
 *   - Has zero effect in production builds
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

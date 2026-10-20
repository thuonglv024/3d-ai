'use strict';

/**
 * Resolve Playwright for the verification scripts.
 *
 * Playwright is installed as a dev dependency of `frontend/`. These scripts live
 * in `verification/scripts/`, so Node's default resolution would not find it.
 * Try a normal local install first, then the frontend workspace copy.
 */

const path = require('node:path');

const candidates = [
  'playwright',
  path.join(__dirname, '..', '..', 'frontend', 'node_modules', 'playwright'),
];

let playwright = null;
let lastError = null;

for (const candidate of candidates) {
  try {
    playwright = require(candidate);
    break;
  } catch (error) {
    if (!error || error.code !== 'MODULE_NOT_FOUND') {
      throw error;
    }
    lastError = error;
  }
}

if (!playwright) {
  throw new Error(
    'Playwright is not installed. Run "cd frontend && npm install" and "npx playwright install chromium".',
    { cause: lastError },
  );
}

module.exports = playwright;

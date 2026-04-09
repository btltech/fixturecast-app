// Compatibility wrapper: prefer importing from ../config.js.
// Keeping this file prevents breaking older imports.

import { ML_API_URL, BACKEND_API_URL } from "../config.js";

export { ML_API_URL, BACKEND_API_URL };

export const getMLApiUrl = (path) => `${ML_API_URL}${path}`;
export const getBackendApiUrl = (path) => `${BACKEND_API_URL}${path}`;

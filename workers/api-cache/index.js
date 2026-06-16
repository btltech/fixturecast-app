/**
 * FixtureCast API Cache Worker
 *
 * Reverse proxy in front of the Railway backend, serving from Cloudflare's Edge
 * Cache when possible. Cache policy is PATH-AWARE so time-sensitive endpoints
 * stay fresh:
 *   - /health*                    → never cached (always live), no-store
 *   - live / time-sensitive paths → short TTL (60s), enforced
 *   - everything else             → default TTL (15 min)
 *
 * Previously every GET was cached for 15 minutes, which let health checks and
 * "today's fixtures" read up to 15 min stale. This version bypasses health and
 * caps the live endpoints at 60s.
 */

const LIVE_TTL = 20;      // seconds — in-play live scores (needs to feel live)
const SHORT_TTL = 60;     // seconds — other time-sensitive endpoints
const DEFAULT_TTL = 900;  // seconds — everything else (static-ish data)

// In-play endpoints: refresh fast so goals/minutes aren't stale.
const LIVE_TTL_PREFIXES = ['/api/live'];
// Time-sensitive but not live-by-the-second. Matched as path prefixes.
const SHORT_TTL_PREFIXES = [
    '/api/fixtures/today',
    '/api/match-of-the-day',
    '/api/results',
];

function isHealthPath(pathname) {
    return pathname === '/health' || pathname.startsWith('/health/');
}

function cacheTtlForPath(pathname) {
    for (const prefix of LIVE_TTL_PREFIXES) {
        if (pathname === prefix || pathname.startsWith(prefix)) return LIVE_TTL;
    }
    for (const prefix of SHORT_TTL_PREFIXES) {
        if (pathname === prefix || pathname.startsWith(prefix)) return SHORT_TTL;
    }
    return DEFAULT_TTL;
}

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);

        // Determine which Railway backend to route to based on the subdomain.
        let targetDomain;
        if (url.hostname.startsWith('ml.')) {
            targetDomain = 'ml-api-production-6cfc.up.railway.app';
        } else {
            targetDomain = 'backend-api-production-7b7d.up.railway.app';
        }

        // Rewrite the URL to point to Railway.
        const targetUrl = new URL(request.url);
        targetUrl.hostname = targetDomain;
        targetUrl.protocol = 'https:';

        const proxyRequest = new Request(targetUrl, request);

        // Never cache non-GET requests or health checks — always hit the origin
        // so liveness/readiness and write operations are never served stale.
        const bypassCache = request.method !== 'GET' || isHealthPath(url.pathname);

        if (bypassCache) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000);
                const resp = await fetch(new Request(proxyRequest, { signal: controller.signal }));
                clearTimeout(timeoutId);

                // Make sure health responses are not stored by any downstream cache.
                if (isHealthPath(url.pathname)) {
                    const fresh = new Response(resp.body, resp);
                    fresh.headers.set('Cache-Control', 'no-store, max-age=0');
                    return fresh;
                }
                return resp;
            } catch (error) {
                const isTimeout = error.name === 'AbortError';
                return new Response(JSON.stringify({ error: isTimeout ? 'Origin timeout' : 'Origin Server Error', details: error.message }), {
                    status: isTimeout ? 504 : 502,
                    headers: { 'Content-Type': 'application/json', 'Retry-After': '10' }
                });
            }
        }

        // Cloudflare Edge Cache API
        const cache = caches.default;

        // Check if the response is already in the cache
        let response = await cache.match(request);

        if (!response) {
            // Cache miss: fetch from Railway with a hard 10s timeout so the
            // worker never hangs for the full 15s when Railway is down.
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000);
                response = await fetch(new Request(proxyRequest, { signal: controller.signal }));
                clearTimeout(timeoutId);

                // Only cache successful requests
                if (response.status === 200) {
                    // Clone the response so we can both cache it and return it
                    response = new Response(response.body, response);

                    const ttl = cacheTtlForPath(url.pathname);
                    const enforce = ttl !== DEFAULT_TTL;

                    // Enforce the short TTL on time-sensitive/live endpoints (so they
                    // can never inherit a long cache); for everything else keep the
                    // existing behaviour of only setting a default when the origin
                    // sent none.
                    if (enforce || !response.headers.has('Cache-Control')) {
                        response.headers.set('Cache-Control', `public, max-age=${ttl}, s-maxage=${ttl}`);
                    }

                    // Store the response in the Edge Cache asynchronously
                    ctx.waitUntil(cache.put(request, response.clone()));
                }
            } catch (error) {
                const isTimeout = error.name === 'AbortError';
                return new Response(JSON.stringify({ error: isTimeout ? 'Origin timeout — backend may be restarting, try again in 30s' : 'Origin Server Error', details: error.message }), {
                    status: isTimeout ? 504 : 502,
                    headers: { 'Content-Type': 'application/json', 'Retry-After': '30' }
                });
            }
        }

        // Return the cached or freshly fetched response
        return response;
    },
};

/**
 * FixtureCast API Cache Worker
 * 
 * This worker acts as a reverse proxy in front of the Railway backend.
 * It intercepts requests and serves them from Cloudflare's Edge Cache if available.
 * If the cache misses, it fetches from Railway, caches the response, and returns it.
 */

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);

        // Determine which Railway backend to route to based on the subdomain or path
        let targetDomain;
        if (url.hostname.startsWith('ml.')) {
            targetDomain = 'ml-api-production-6cfc.up.railway.app';
        } else {
            targetDomain = 'backend-api-production-7b7d.up.railway.app';
        }

        // Rewrite the URL to point to Railway
        const targetUrl = new URL(request.url);
        targetUrl.hostname = targetDomain;
        targetUrl.protocol = 'https:';

        // Create a new request based on the original, but pointing to Railway
        const proxyRequest = new Request(targetUrl, request);

        // If it's not a GET request, don't cache it, just proxy it directly
        if (request.method !== 'GET') {
            return fetch(proxyRequest);
        }

        // Cloudflare Edge Cache API
        const cache = caches.default;

        // Check if the response is already in the cache
        let response = await cache.match(request);

        if (!response) {
            // Cache miss: fetch from Railway
            try {
                response = await fetch(proxyRequest);

                // Only cache successful requests
                if (response.status === 200) {
                    // Clone the response so we can both cache it and return it
                    response = new Response(response.body, response);

                    // Ensure Cloudflare caches it for 15 minutes at the edge if no header exists
                    if (!response.headers.has('Cache-Control')) {
                        response.headers.set('Cache-Control', 'public, max-age=900, s-maxage=900');
                    }

                    // Store the response in the Edge Cache asynchronously
                    ctx.waitUntil(cache.put(request, response.clone()));
                }
            } catch (error) {
                return new Response(JSON.stringify({ error: 'Origin Server Error', details: error.message }), {
                    status: 502,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
        }

        // Return the cached or freshly fetched response
        return response;
    },
};

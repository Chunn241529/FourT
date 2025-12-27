/**
 * Cloudflare Worker - Sepay Webhook Proxy
 * 
 * This worker acts as a fixed endpoint for Sepay webhooks.
 * It fetches the current API URL from npoint.io and forwards the webhook request.
 * 
 * Setup:
 * 1. Create a new Cloudflare Worker
 * 2. Deploy and use the worker URL as Sepay webhook in Sepay dashboard
 * 3. That's it! Worker will auto-fetch latest URL from npoint.io
 */

// ========== CONFIGURATION ==========
// npoint.io endpoint (same as in run_server.py)
const NPOINT_URL = "https://api.npoint.io/c6878ec0e82ad63a767f";
const WEBHOOK_PATH = "/sepay/webhook"; // Path on backend server
// ====================================

export default {
    async fetch(request) {
        // Only allow POST (webhook from Sepay)
        if (request.method !== "POST") {
            return new Response(JSON.stringify({
                error: "Method not allowed",
                allowed: ["POST"]
            }), {
                status: 405,
                headers: { "Content-Type": "application/json" }
            });
        }

        try {
            // 1. Fetch current API URL from npoint.io
            const npointRes = await fetch(NPOINT_URL, {
                headers: { "Cache-Control": "no-cache" }
            });

            if (!npointRes.ok) {
                return new Response(JSON.stringify({
                    error: "Failed to fetch API URL from npoint.io",
                    status: npointRes.status
                }), { status: 502, headers: { "Content-Type": "application/json" } });
            }

            const data = await npointRes.json();

            // Priority order: fourt.io.vn > cloudflare > ngrok > bore > server (same as config.py)
            // fourt.io.vn added as hardcoded fallback if not in npoint.io
            const targetUrl = data.fourt_url || "https://fourt.io.vn" ||
                data.cloudflare_url || data.ngrok_url || data.bore_url || data.server_url;

            if (!targetUrl) {
                return new Response(JSON.stringify({
                    error: "No target URL configured in npoint.io",
                    available_keys: Object.keys(data)
                }), { status: 500, headers: { "Content-Type": "application/json" } });
            }

            // 2. Forward request to target URL
            const body = await request.text();
            const originalHeaders = Object.fromEntries(request.headers);

            // Clean up Cloudflare headers
            delete originalHeaders["host"];
            delete originalHeaders["cf-connecting-ip"];
            delete originalHeaders["cf-ray"];
            delete originalHeaders["cf-visitor"];
            delete originalHeaders["cf-ipcountry"];

            console.log(`Proxying to: ${targetUrl}${WEBHOOK_PATH}`);

            const proxyRes = await fetch(targetUrl + WEBHOOK_PATH, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Forwarded-For": request.headers.get("cf-connecting-ip") || "",
                    "X-Original-Host": request.headers.get("host") || "",
                    // Forward authorization header (Sepay sends API key here)
                    "Authorization": request.headers.get("authorization") || "",
                },
                body: body
            });

            // 3. Return response from backend
            const responseBody = await proxyRes.text();

            return new Response(responseBody, {
                status: proxyRes.status,
                headers: {
                    "Content-Type": "application/json",
                    "X-Proxied-To": targetUrl
                }
            });

        } catch (error) {
            console.error("Proxy error:", error);
            return new Response(JSON.stringify({
                error: "Proxy error",
                message: error.message
            }), {
                status: 500,
                headers: { "Content-Type": "application/json" }
            });
        }
    }
};

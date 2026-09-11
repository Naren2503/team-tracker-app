const ORIGIN = "https://naren2503-team-tracker.onrender.com";
const HEALTH_PATH = "/__dq-team-tracker-health";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname === HEALTH_PATH) {
      return healthResponse();
    }

    const response = await fetchOrigin(request, url);
    if (response || !isDocumentNavigation(request)) {
      return response ?? new Response("Service temporarily unavailable", { status: 503 });
    }

    return loadingResponse();
  },
};

async function fetchOrigin(request, url) {
  const originUrl = new URL(`${url.pathname}${url.search}`, ORIGIN);
  try {
    const response = await fetch(new Request(originUrl, request));
    return [502, 503, 504].includes(response.status) ? null : response;
  } catch {
    return null;
  }
}

async function healthResponse() {
  try {
    const response = await fetch(`${ORIGIN}/health`, {
      headers: { "Cache-Control": "no-store" },
    });
    return new Response(null, {
      status: response.ok ? 204 : 503,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return new Response(null, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}

function isDocumentNavigation(request) {
  return request.method === "GET" && request.headers.get("Accept")?.includes("text/html");
}

function loadingResponse() {
  return new Response(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#101815">
  <title>DQ Team Tracker</title>
  <style>
    :root { color-scheme: dark; --bg: #101815; --line: #31413a; --ink: #f1f7f3; --muted: #a9bbb3; --mint: #5ac8ad; --orange: #efa061; }
    * { box-sizing: border-box; }
    body { min-height: 100vh; margin: 0; display: grid; place-items: center; padding: 32px 20px; color: var(--ink); background: linear-gradient(90deg, rgba(90, 200, 173, .04) 1px, transparent 1px), linear-gradient(rgba(90, 200, 173, .04) 1px, transparent 1px), radial-gradient(circle at 50% 40%, #1e3029 0, var(--bg) 58%); background-size: 32px 32px, 32px 32px, auto; font-family: Aptos, Candara, "Segoe UI", sans-serif; }
    main { width: min(560px, 100%); display: grid; justify-items: center; text-align: center; animation: reveal .55s ease-out both; }
    .mark { width: 164px; height: 98px; margin: 0 0 26px; position: relative; }
    .track { position: absolute; left: 6px; right: 6px; top: 45px; height: 2px; background: var(--line); }
    .pulse { position: absolute; top: 39px; width: 14px; height: 14px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 0 8px rgba(90, 200, 173, .12); animation: travel 2.1s ease-in-out infinite; }
    .bar { position: absolute; bottom: 0; width: 12px; border-radius: 3px 3px 0 0; transform-origin: bottom; animation: rise 1.4s ease-in-out infinite alternate; }
    .bar:nth-child(2) { left: 32px; height: 25px; background: var(--orange); } .bar:nth-child(3) { left: 54px; height: 46px; background: var(--mint); animation-delay: .2s; } .bar:nth-child(4) { left: 76px; height: 34px; background: #9aaba3; animation-delay: .4s; } .bar:nth-child(5) { left: 98px; height: 64px; background: var(--orange); animation-delay: .6s; }
    h1 { margin: 0; font-size: clamp(2.2rem, 8vw, 3.6rem); font-weight: 720; line-height: 1.04; letter-spacing: 0; } .eyebrow { margin: 0 0 12px; color: var(--orange); font-size: .75rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; } #status { min-height: 1.5em; margin: 22px 0 24px; color: var(--muted); font-size: 1rem; } .progress { width: min(356px, 100%); height: 4px; overflow: hidden; background: var(--line); border-radius: 99px; } .progress::after { content: ""; display: block; width: 42%; height: 100%; background: var(--mint); animation: progress 1.4s ease-in-out infinite; }
    @keyframes reveal { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } } @keyframes travel { 0%, 100% { left: 10px; } 50% { left: 140px; } } @keyframes rise { from { transform: scaleY(.55); opacity: .65; } to { transform: scaleY(1); opacity: 1; } } @keyframes progress { from { transform: translateX(-105%); } to { transform: translateX(340%); } }
    @media (prefers-reduced-motion: reduce) { *, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; } }
  </style>
</head>
<body>
  <main>
    <div class="mark" aria-hidden="true"><div class="track"></div><i class="bar"></i><i class="bar"></i><i class="bar"></i><i class="bar"></i><i class="pulse"></i></div>
    <p class="eyebrow">Data Quality</p>
    <h1>DQ Team Tracker</h1>
    <p id="status" role="status" aria-live="polite">Starting your workspace...</p>
    <div class="progress" aria-hidden="true"></div>
  </main>
  <script>
    const status = document.getElementById("status");
    let attempts = 0;
    async function waitForTracker() {
      attempts += 1;
      status.textContent = attempts > 1 ? "Almost ready. Loading tracker data..." : "Starting your workspace...";
      try {
        const response = await fetch("${HEALTH_PATH}?wake=" + Date.now(), { cache: "no-store" });
        if (response.ok) return location.reload();
      } catch {}
      setTimeout(waitForTracker, 2500);
    }
    waitForTracker();
  </script>
</body>
</html>`, { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
}

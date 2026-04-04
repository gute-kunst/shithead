const CACHE_NAME = "shithead-alpha-v31";
const APP_SHELL = [
  "/",
  "/static/styles.css?v=20260404c",
  "/static/app.js?v=20260404c",
  "/static/manifest.webmanifest?v=20260404c",
  "/static/icons/icon-180.png?v=20260404c",
  "/static/icons/icon-192.png?v=20260404c",
  "/static/icons/icon-512.png?v=20260404c",
];

function isSameOrigin(url) {
  return url.origin === self.location.origin;
}

function isApiRequest(url) {
  return isSameOrigin(url) && url.pathname.startsWith("/api/");
}

function isNavigationRequest(request) {
  return request.mode === "navigate";
}

function isStaticAssetRequest(url) {
  return isSameOrigin(url) && url.pathname.startsWith("/static/");
}

async function putIfOk(request, response) {
  if (!response || !response.ok) {
    return response;
  }
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
  return response;
}

async function navigationStrategy(request) {
  try {
    const response = await fetch(request);
    await putIfOk(request, response);
    return response;
  } catch {
    return (await caches.match(request)) || (await caches.match("/"));
  }
}

async function staticAssetStrategy(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  const response = await fetch(request);
  await putIfOk(request, response);
  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);
  if (!isSameOrigin(url) || isApiRequest(url)) {
    return;
  }

  if (isNavigationRequest(event.request)) {
    event.respondWith(navigationStrategy(event.request));
    return;
  }

  if (isStaticAssetRequest(url)) {
    event.respondWith(staticAssetStrategy(event.request));
  }
});

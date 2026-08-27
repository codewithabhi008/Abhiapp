const CACHE_NAME = 'abhiapp-vault-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/main.css',
  '/static/css/components.css',
  '/static/css/previews.css',
  '/static/js/app.js',
  '/static/js/auth.js',
  '/static/js/upload.js',
  '/static/js/vault.js',
  '/static/js/folders.js',
  '/static/js/preview.js',
  '/static/icons/icon-192.svg',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Handle API and dynamic requests with network-first strategy
  if (event.request.url.includes('/api/') || event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

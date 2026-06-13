const CACHE_NAME = 'ja1-court-manager-v2';
const ASSETS = [
  './',
  'index.html',
  'logo.jpg',
  'manifest.json',
  'vendor/tailwind.min.js',
  'vendor/dexie.js',
  'vendor/all.min.css',
  'vendor/webfonts/fa-solid-900.woff2',
  'vendor/webfonts/fa-regular-400.woff2'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

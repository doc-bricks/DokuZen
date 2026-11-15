// Service Worker für DokuZen Web Companion (Offline Cache)
const CACHE_NAME = 'dokuzen-companion-v2';
// Inhalts-Hash aller ASSETS-Dateien inkl. Manifest und Icons (web_companion/tests/sw_asset_hash.test.mjs prueft ihn):
// aendert sich eine davon, CACHE_NAME erhoehen, sonst behalten installierte PWAs den alten Code.
const ASSET_HASH = '8db11a3a9bcd'; // eslint-disable-line no-unused-vars
const ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './library.js',
  './manifest.webmanifest',
  './sample_workspace.json',
  './icons/dokureader-companion-192.png',
  './icons/dokureader-companion-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});

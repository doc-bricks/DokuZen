// Service Worker für DokuZen Web Companion (Offline Cache)
const CACHE_NAME = 'dokuzen-companion-v1';
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

const CACHE_NAME = 'chronicle-pwa-v1';
const OFFLINE_URL = '/static/offline.html';
const PRECACHE_URLS = [
  OFFLINE_URL,
  '/static/css/output.css',
  '/static/assets/logo.png',
  '/static/assets/favicon.ico',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    (async () => {
      try {
        if (event.request.mode === 'navigate') {
          const networkResponse = await fetch(event.request);
          const cache = await caches.open(CACHE_NAME);
          cache.put(event.request, networkResponse.clone());
          return networkResponse;
        }

        const cached = await caches.match(event.request);
        if (cached) {
          return cached;
        }

        const networkResponse = await fetch(event.request);
        const cache = await caches.open(CACHE_NAME);
        cache.put(event.request, networkResponse.clone());
        return networkResponse;
      } catch (error) {
        if (event.request.mode === 'navigate') {
          const cachedPage = await caches.match(event.request);
          return cachedPage || caches.match(OFFLINE_URL);
        }
        return caches.match(event.request) || Response.error();
      }
    })()
  );
});

self.addEventListener('push', (event) => {
  event.waitUntil((async () => {
    let data = {};
    try {
      data = event.data ? event.data.json() : {};
    } catch (err) {
      data = { message: event.data ? event.data.text() : '' };
    }

    const title = data.title || 'Chronicle';
    const message = data.message || '';
    const link = data.link || '/';
    const unreadCount = typeof data.unread_count === 'number' ? data.unread_count : null;
    const options = {
      body: message,
      icon: '/static/assets/logo.png',
      badge: '/static/assets/logo.png',
      data: { url: link },
      tag: data.type || 'chronicle-notification',
      renotify: true,
    };

    if (unreadCount !== null && self.registration.setAppBadge) {
      try {
        await self.registration.setAppBadge(unreadCount);
      } catch (err) {
        // ignore
      }
    }

    const clientsList = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });
    clientsList.forEach((client) => {
      client.postMessage({ type: 'badge-update', unread_count: unreadCount });
    });

    return self.registration.showNotification(title, options);
  })());
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil((async () => {
    const allClients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of allClients) {
      if ('focus' in client) {
        client.focus();
        client.postMessage({ type: 'navigate', url });
        return;
      }
    }
    if (self.clients.openWindow) {
      await self.clients.openWindow(url);
    }
  })());
});

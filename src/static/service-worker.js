const CACHE_NAME = 'chronicle-pwa-v2';
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

function shouldCache(request) {
  if (request.method !== 'GET') {
    return false;
  }
  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;
  if (sameOrigin && url.pathname.startsWith('/static/')) {
    return true;
  }
  if (url.pathname === OFFLINE_URL) {
    return true;
  }
  return false;
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    (async () => {
      try {
        const networkResponse = await fetch(event.request);
        if (shouldCache(event.request)) {
          const cache = await caches.open(CACHE_NAME);
          cache.put(event.request, networkResponse.clone());
        }
        return networkResponse;
      } catch (error) {
        const cache = await caches.open(CACHE_NAME);
        const cached = await cache.match(event.request);
        if (cached) {
          return cached;
        }
        if (event.request.mode === 'navigate') {
          const offline = await cache.match(OFFLINE_URL);
          if (offline) {
            return offline;
          }
        }
        throw error;
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

const CACHE_NAME = "grid-shell-v3";

const APP_SHELL = [
    "/",
    "/static/styles.css",
    "/static/app.js",
    "/static/manifest.json"
];

self.addEventListener("install", (event) => {

    self.skipWaiting();

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(APP_SHELL))
    );
});

self.addEventListener("activate", (event) => {

    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );

    clients.claim();
});

self.addEventListener("fetch", (event) => {

    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});

self.addEventListener("message", (event) => {

    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

self.addEventListener("push", (event) => {

    const payload =
        event.data ? event.data.json() : {};

    event.waitUntil(
        self.registration.showNotification(
            payload.title || "Collaborative Grid",
            {
                body: payload.body || "Push notification",
                tag: "grid-launch"
            }
        )
    );
});

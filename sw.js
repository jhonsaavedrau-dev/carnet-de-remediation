// Service worker : page en réseau d'abord, audio mis en cache à la première écoute.
const V = "carnet-202609181615", AUDIO = "carnet-audio";
self.addEventListener("install", e => { e.waitUntil(caches.open(V).then(c => c.addAll(["./", "manifest.webmanifest", "icone.svg"]))); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V && k !== AUDIO).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
async function audio(req) {
  const url = req.url.split("#")[0];
  const cache = await caches.open(AUDIO);
  let res = await cache.match(url);
  if (!res) { res = await fetch(url); if (res.ok && res.status === 200) await cache.put(url, res.clone()); else return res; }
  const range = req.headers.get("range");
  if (!range) return res;
  const blob = await res.blob(), m = /bytes=(\d*)-(\d*)/.exec(range) || [];
  const start = m[1] ? +m[1] : 0, end = m[2] ? +m[2] : blob.size - 1;
  return new Response(blob.slice(start, end + 1), { status: 206, headers: {
    "Content-Type": "audio/mpeg", "Accept-Ranges": "bytes",
    "Content-Range": `bytes ${start}-${end}/${blob.size}`, "Content-Length": String(end - start + 1) } });
}
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/audio/")) { e.respondWith(audio(req)); return; }
  e.respondWith(fetch(req).then(res => { if (res.ok) { const c = res.clone(); caches.open(V).then(k => k.put(req, c)); } return res; })
    .catch(() => caches.match(req).then(r => r || caches.match("./"))));
});

"""Construit la version web publique (GitHub Pages) à partir de carnet-de-remediation.html.

Le même fichier source sert l'artifact claude.ai. Ici on ajoute le squelette HTML complet,
un manifeste pour l'installer sur le téléphone et un service worker pour l'écoute hors ligne.
Hors de claude.ai, la page se passe de Claude (atelier, « Pourquoi ? ») et garde la
progression dans le navigateur de chaque visiteur.

    python construire-site.py
"""
import json
import re
import struct
import time
import zlib
from pathlib import Path

ICI = Path(__file__).parent
IVOIRE, ENCRE, TERRE = (0xF3, 0xF0, 0xE8), (0x11, 0x11, 0x11), (0x7C, 0x3B, 0x2E)

# Icône : un accent aigu à l'encre et un filet terre cuite, sur fond ivoire (repère 100 × 100).
ACCENT = [(48, 20), (63, 20), (47, 55), (35, 55)]
FILET = [(28, 67), (72, 67), (72, 73), (28, 73)]


def dans(poly, x, y):
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def png(taille):
    lignes = bytearray()
    ech = [(i + 0.5) / 3 for i in range(3)]
    for py in range(taille):
        lignes.append(0)
        for px in range(taille):
            acc = [0, 0, 0]
            for sy in ech:
                for sx in ech:
                    x, y = (px + sx) * 100 / taille, (py + sy) * 100 / taille
                    col = ENCRE if dans(ACCENT, x, y) else TERRE if dans(FILET, x, y) else IVOIRE
                    for k in range(3):
                        acc[k] += col[k]
            lignes += bytes(round(v / 9) for v in acc)

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", taille, taille, 8, 2, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(bytes(lignes), 9)) + bloc(b"IEND", b""))


def svg():
    pts = lambda p: " ".join(f"{x},{y}" for x, y in p)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="#F3F0E8"/>'
            f'<polygon points="{pts(ACCENT)}" fill="#111111"/><polygon points="{pts(FILET)}" fill="#7C3B2E"/></svg>')


SW = """// Service worker : page en réseau d'abord, audio mis en cache à la première écoute.
const V = "carnet-__VERSION__", AUDIO = "carnet-audio";
self.addEventListener("install", e => { e.waitUntil(caches.open(V).then(c => c.addAll(["./", "manifest.webmanifest", "icone.svg"]))); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V && k !== AUDIO).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
async function audio(req) {
  const url = req.url.split("#")[0];
  const cache = await caches.open(AUDIO);
  let res = await cache.match(url);
  if (!res) { res = await fetch(url); if (res.ok && res.status === 200) await cache.put(url, res.clone()); else return res; }
  const range = req.headers.get("range");
  if (!range) return res;
  const blob = await res.blob(), m = /bytes=(\\d*)-(\\d*)/.exec(range) || [];
  const start = m[1] ? +m[1] : 0, end = m[2] ? +m[2] : blob.size - 1;
  return new Response(blob.slice(start, end + 1), { status: 206, headers: {
    "Content-Type": "audio/mpeg", "Accept-Ranges": "bytes",
    "Content-Range": `bytes ${start}-${end}/${blob.size}`, "Content-Length": String(end - start + 1) } });
}
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/audio/")) { e.respondWith(audio(req)); return; }
  e.respondWith(fetch(req.mode === "navigate" ? new Request(req.url, { cache: "no-cache" }) : req).then(res => { if (res.ok) { const c = res.clone(); caches.open(V).then(k => k.put(req, c)); } return res; })
    .catch(() => caches.match(req).then(r => r || caches.match("./"))));
});
"""


def main():
    src = (ICI / "carnet-de-remediation.html").read_text(encoding="utf-8")
    coupe = src.index('<header class="top">')
    tete, corps = src[:coupe], src[coupe:]
    tete = re.sub(r'<meta charset="utf-8">\s*|<meta name="viewport"[^>]*>\s*', "", tete)
    version = time.strftime("%Y%m%d%H%M")
    entete = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#F3F0E8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#131210" media="(prefers-color-scheme: dark)">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icone.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icone-180.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Carnet">
<style>html,body{margin:0}[hidden]{display:none!important}img{max-width:100%}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>
"""
    enregistrement = ('<script>if("serviceWorker" in navigator&&location.protocol==="https:")'
                      '{navigator.serviceWorker.register("sw.js").catch(()=>{});}</script>\n')
    page = entete + tete + "</head>\n<body>\n" + corps + enregistrement + "</body>\n</html>\n"
    (ICI / "index.html").write_text(page, encoding="utf-8")
    (ICI / "sw.js").write_text(SW.replace("__VERSION__", version), encoding="utf-8")
    (ICI / "manifest.webmanifest").write_text(json.dumps({
        "name": "Carnet de remédiation", "short_name": "Carnet", "lang": "fr",
        "description": "Parcours de français B2 → C1 : leçons, dictées, accents, carnet d'erreurs.",
        "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": "#F3F0E8", "theme_color": "#F3F0E8",
        "icons": [{"src": "icone.svg", "sizes": "any", "type": "image/svg+xml"},
                  {"src": "icone-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icone-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (ICI / "icone.svg").write_text(svg(), encoding="utf-8")
    for t in (180, 192, 512):
        (ICI / f"icone-{t}.png").write_bytes(png(t))
    (ICI / ".nojekyll").write_text("", encoding="utf-8")
    print(f"site construit · version {version} · index.html {len(page) / 1024:.0f} Ko")


if __name__ == "__main__":
    main()

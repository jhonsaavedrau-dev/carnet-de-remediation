"""Génère les enregistrements fr-FR de la page et écrit le manifeste AUDIO dans le HTML.

Voix neuronales Microsoft (edge-tts) : Denise pour les leçons et les phrases,
Henri pour les dictées de nombres. Relancer après avoir modifié un texte :
seuls les fichiers manquants sont générés.

    python -m pip install edge-tts
    python generer-audio.py
"""
import asyncio
import hashlib
import html
import json
import re
from pathlib import Path

import edge_tts

ICI = Path(__file__).parent
PAGE = ICI / "carnet-de-remediation.html"
DOSSIER = ICI / "audio"
DENISE, HENRI = "fr-FR-DeniseNeural", "fr-FR-HenriNeural"
LENT = "-35%"


def court(texte):
    return hashlib.sha1(texte.encode("utf-8")).hexdigest()[:10]


def narration(titre, theorie):
    t = theorie
    t = re.sub(r"<tr>\s*<th>.*?</tr>", "", t, flags=re.S)   # en-têtes de tableau
    t = re.sub(r"<td>(f|m)\.</td>", lambda m: "<td>" + ("féminin" if m.group(1) == "f" else "masculin") + "</td>", t)
    t = re.sub(r"</td>\s*</tr>", ". ", t)
    t = re.sub(r"</td>", ", ", t)
    t = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</tr>", ". ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"\s*\[[^\]]*\]", "", t)          # transcriptions API
    t = t.replace("→", " : ").replace("·", ", ").replace("‿", " ").replace("|", "")
    t = t.replace("≠", ", différent de ").replace("(f.)", "(féminin)").replace("(m.)", "(masculin)")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\(\s*,\s*", "(", t)
    t = re.sub(r":\s*\.", ".", t)
    t = re.sub(r"\s*([,.])(\s*[,.])+", lambda m: "." if "." in m.group(0) else ",", t)
    t = re.sub(r"\s+([,.)])", r"\1", t)
    return (titre + ". " + t).strip()


# Leçons dont le tableau n'a pas de sens à l'oral : texte dit à la place.
NARRATIONS = {
    "notes": "La prise de notes. On note les idées, pas les phrases : les mots-clés, les chiffres, "
    "les dates, les noms, et surtout les liens logiques. Quelques signes à connaître. La flèche "
    "signifie : entraîne, a pour conséquence. Le signe différent marque une opposition. Une flèche "
    "vers le haut indique une hausse ; vers le bas, une baisse. Un cercle barré signifie : absence. "
    "On abrège aussi les mots fréquents : p b pour problème, g v t pour gouvernement, q q n pour "
    "quelqu'un, q q c h pour quelque chose, t j s pour toujours. Le petit rond en exposant remplace "
    "la terminaison tion : popula, petit rond, se lit population. Enfin, structurez la page avec des "
    "numéros, et laissez une marge pour compléter après l'écoute.",
}


def collecter(source):
    clips = {}
    constantes = dict(re.findall(r"const (DOC_\w+)=`(.*?)`;", source, re.S))
    for m in re.finditer(r'\{ id:"([^"]+)",[^`{]*?title:"([^"]+)"[^`{]*?theory:`(.*?)`', source, re.S):
        ident, titre, theorie = m.groups()
        theorie = re.sub(r"\$\{(DOC_\w+)\}", lambda c: constantes.get(c.group(1), ""), theorie)
        texte = NARRATIONS.get(ident) or narration(titre, theorie)
        clips["t:" + ident] = (f"t-{ident}.mp3", texte, DENISE, None)
    phrases = [(s, DENISE) for s in re.findall(r'say:"([^"]+)"', source)]
    phrases += [(s, HENRI) for s in re.findall(r'LI\("([^"]+)"', source)]
    for texte, voix in phrases:
        clips["s:" + texte] = (f"s-{court(texte)}.mp3", texte, voix, None)
        clips["z:" + texte] = (f"z-{court(texte)}.mp3", texte, voix, LENT)
    return clips


def dicter(segment):
    """Version lue en dictée : la ponctuation est prononcée."""
    s = segment.replace("«", "ouvrez les guillemets,").replace("»", ", fermez les guillemets,")
    s = re.sub(r"\s*,", ", virgule,", s)
    s = re.sub(r"\s*:", ", deux-points,", s)
    s = re.sub(r"\s*;", ", point-virgule,", s)
    s = re.sub(r"\s*\?", ", point d'interrogation.", s)
    s = re.sub(r"\s*!", ", point d'exclamation.", s)
    s = re.sub(r"\.\s*$", ". Point.", s)
    return s


def json_bloc(source, ident):
    m = re.search(rf'<script type="application/json" id="{ident}">(.*?)</script>', source, re.S)
    return json.loads(m.group(1)) if m else None


def collecter_sprites(source):
    """Regroupe dictées et mots en quelques fichiers (limite de 255 fichiers par artifact)."""
    sprites = {}
    for d in json_bloc(source, "dictees") or []:
        parts = [(f"d:{d['id']}:full", " ".join(d["segs"]), HENRI, "-5%")]
        for i, seg in enumerate(d["segs"]):
            parts.append((f"d:{d['id']}:p{i}", dicter(seg), HENRI, "-25%"))
            parts.append((f"d:{d['id']}:s{i}", seg, HENRI, "-25%"))
        sprites[f"dz-{d['id']}.mp3"] = parts
    for fam, mots in (json_bloc(source, "signes") or {}).items():
        parts = []
        for entree in mots:
            mot = entree.split("|")[0].split("/")[0]
            parts.append(("s:" + mot, mot, DENISE, None))
        sprites[f"sg-{fam}.mp3"] = parts
    return sprites


OCTETS_PAR_SECONDE = 6000  # mp3 CBR 48 kbit/s, 24 kHz, sans en-tête ID3


async def generer_sprites(sprites):
    pieces = DOSSIER / "_pieces"
    pieces.mkdir(parents=True, exist_ok=True)
    verrou = asyncio.Semaphore(4)

    def chemin(texte, voix, vitesse):
        return pieces / (hashlib.sha1(f"{voix}|{vitesse}|{texte}".encode()).hexdigest()[:16] + ".mp3")

    async def un(texte, voix, vitesse):
        cible = chemin(texte, voix, vitesse)
        if cible.exists() and cible.stat().st_size > 0:
            return
        async with verrou:
            options = {"rate": vitesse} if vitesse else {}
            await edge_tts.Communicate(texte, voix, **options).save(str(cible))

    await asyncio.gather(*(un(t, v, r) for parts in sprites.values() for (_, t, v, r) in parts))
    manifeste = {}
    for nom, parts in sprites.items():
        octets, t = bytearray(), 0.0
        for cle, texte, voix, vitesse in parts:
            donnees = chemin(texte, voix, vitesse).read_bytes()
            duree = len(donnees) / OCTETS_PAR_SECONDE
            manifeste[cle] = f"audio/{nom}#{t:.3f},{t + duree - 0.03:.3f}"
            octets += donnees
            t += duree
        (DOSSIER / nom).write_bytes(octets)
        print(f"  = {nom} · {len(parts)} extraits · {t:.0f} s")
    return manifeste


async def generer(clips):
    DOSSIER.mkdir(exist_ok=True)
    verrou = asyncio.Semaphore(4)

    async def un(nom, texte, voix, vitesse):
        cible = DOSSIER / nom
        if cible.exists() and cible.stat().st_size > 0:
            return
        async with verrou:
            options = {"rate": vitesse} if vitesse else {}
            await edge_tts.Communicate(texte, voix, **options).save(str(cible))
            print("  +", nom)

    await asyncio.gather(*(un(*c) for c in clips.values()))


def main():
    source = PAGE.read_text(encoding="utf-8")
    clips = collecter(source)
    print(f"{len(clips)} enregistrements")
    asyncio.run(generer(clips))
    manifeste = {cle: "audio/" + c[0] for cle, c in sorted(clips.items())}
    manifeste.update(asyncio.run(generer_sprites(collecter_sprites(source))))
    bloc = "/*AUDIO*/const AUDIO=" + json.dumps(manifeste, ensure_ascii=False) + ";/*/AUDIO*/"
    source = re.sub(r"/\*AUDIO\*/.*?/\*/AUDIO\*/", lambda _: bloc, source, flags=re.S)
    PAGE.write_text(source, encoding="utf-8")
    taille = sum(f.stat().st_size for f in DOSSIER.glob("*.mp3"))  # hors _pieces
    print(f"manifeste écrit · {taille / 1e6:.1f} Mo au total")


if __name__ == "__main__":
    main()

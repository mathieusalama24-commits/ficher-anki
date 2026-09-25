#!/usr/bin/env python3
"""
portraits.py — Portraits de personnalités (Wikipédia / Wikimedia Commons) pour les cartes Ficher.

Deux usages :
  1. Téléchargement (sur une machine qui a accès à Internet, ex. le Mac ; bibliothèque standard seulement) :
         python3 portraits.py cartes.json
     → pour chaque « portraits » des cartes, récupère la photo principale de l'article Wikipédia,
       l'enregistre dans portraits/ (à côté du JSON) et note l'auteur et la licence dans portraits/credits.json.
  2. Construction : build_apkg.py lit ce cache (html_verso, html_visage) ; il ne télécharge rien lui-même
     s'il n'a pas de réseau.

Format JSON d'une carte :
  "portraits": [{"wiki": "Zbigniew Brzeziński", "[nom]": "…", "[legende]": "Conseiller à la sécurité nationale (1977-1981)",
                 "[langue]": "fr", "[fichier]": "photo_perso.jpg", "[carte]": "Auteur du « Grand Échiquier » (1997)"}]
  - "wiki"    : titre exact de l'article Wikipédia (langue « fr » par défaut, sinon « en »).
  - "fichier" : une image fournie par l'utilisateur (posée dans portraits/) remplace la recherche.
  - "carte"   : crée une carte « Qui est-ce ? » (photo au recto, ce texte comme indice ; le nom au verso).

Images quelconques (courbe, carte, photo d'événement, affiche…) : même mécanique, champ « images » :
  "images": [{"commons": "Kuznets curve-en.svg", "[legende]": "…", "[face]": "verso|recto"},
             {"url": "https://…/image.jpg", "source": "https://page-d-origine", "[legende]": "…"}]
  - "commons" : nom du fichier sur Wikimedia Commons (licence libre, crédit automatique) — à privilégier.
  - "url"     : image directe d'un autre site (usage personnel) ; "source" = page d'origine, citée sous l'image.
"""
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Ficher/1.0 (flashcards Anki open source)"
DOSSIER = "portraits"


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:50]


def nom_fichier(p):
    return p.get("fichier") or f"v11_portrait_{slug(p['wiki'])}.jpg"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def _texte(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h or ""))).strip()


def telecharger(p, dossier):
    """Télécharge la photo de l'article et renvoie son crédit {auteur, licence, source}."""
    langues = [p.get("langue", "fr")] + (["en"] if p.get("langue", "fr") != "en" else [])
    for lg in langues:
        try:
            titre = urllib.parse.quote(p["wiki"].replace(" ", "_"), safe="")
            summ = json.loads(_get(f"https://{lg}.wikipedia.org/api/rest_v1/page/summary/{titre}"))
        except Exception:
            continue
        th = (summ.get("thumbnail") or {}).get("source")
        if not th:
            continue
        img = _get(th)  # vignette standard de Wikipédia (≈ 330 px) : taille imposée par Wikimedia
        th = th.split("?")[0]
        (dossier / nom_fichier(p)).write_bytes(img)
        fichier_commons = urllib.parse.unquote(th.split("/")[-2]) if "/thumb/" in th else urllib.parse.unquote(th.split("/")[-1])
        credit = {"source": summ.get("content_urls", {}).get("desktop", {}).get("page", ""), "auteur": "", "licence": ""}
        try:
            api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=extmetadata&titles="
                   + urllib.parse.quote("File:" + fichier_commons))
            pages = json.loads(_get(api))["query"]["pages"]
            meta = next(iter(pages.values()))["imageinfo"][0]["extmetadata"]
            credit["auteur"] = _texte(meta.get("Artist", {}).get("value", ""))[:60]
            credit["licence"] = _texte(meta.get("LicenseShortName", {}).get("value", ""))
            credit["source"] = "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(fichier_commons.replace(" ", "_"))
        except Exception:
            pass
        return credit
    raise RuntimeError(f"aucune photo trouvée pour « {p['wiki']} » (vérifie le titre exact de l'article)")


def nom_image(im):
    if im.get("fichier"):
        return im["fichier"]
    base = im.get("commons") or im.get("url", "")
    ext = ".png" if base.lower().endswith((".svg", ".png")) else ".jpg"
    return f"v11_img_{slug(re.sub(r'^(File|Fichier):', '', base.split('/')[-1]).rsplit('.', 1)[0])}{ext}"


def _meta_commons(fichier):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata"
           "&iiurlwidth=960&titles=" + urllib.parse.quote("File:" + fichier))
    return next(iter(json.loads(_get(api))["query"]["pages"].values()))["imageinfo"][0]


def telecharger_image(im, dossier):
    if im.get("commons"):
        fichier = re.sub(r"^(File|Fichier):", "", im["commons"]).replace("_", " ")
        info = _meta_commons(fichier)
        (dossier / nom_image(im)).write_bytes(_get(info.get("thumburl") or info["url"]))  # 960 px (SVG → PNG)
        meta = info.get("extmetadata", {})
        return {"auteur": _texte(meta.get("Artist", {}).get("value", ""))[:60],
                "licence": _texte(meta.get("LicenseShortName", {}).get("value", "")),
                "source": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(fichier.replace(" ", "_"))}
    (dossier / nom_image(im)).write_bytes(_get(im["url"]))
    dom = urllib.parse.urlparse(im.get("source") or im["url"]).netloc.replace("www.", "")
    return {"auteur": dom, "licence": "", "source": im.get("source") or im["url"]}


def main(json_path):
    base = Path(json_path).resolve().parent
    dossier = base / DOSSIER
    dossier.mkdir(exist_ok=True)
    cred_path = dossier / "credits.json"
    credits = json.loads(cred_path.read_text(encoding="utf-8")) if cred_path.exists() else {}
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    for c in data.get("cartes", []):
        items = list(c.get("portraits", [])) + ([c["portrait"]] if c.get("portrait") else []) + list(c.get("images", [])) \
            + list(c.get("images_noeuds", [])) + [x for x in c.get("images_branches", []) if not x.get("visuel")]
        for it in items:
            portrait = it.get("wiki") and not (it.get("commons") or it.get("url"))
            f = nom_fichier(it) if portrait else nom_image(it)
            if it.get("fichier") or (dossier / f).exists():
                print(f"= {f} (déjà là)")
                continue
            try:
                credits[f] = telecharger(it, dossier) if portrait else telecharger_image(it, dossier)
                print(f"✓ {f} — {credits[f].get('auteur') or '?'} · {credits[f].get('licence') or '?'}")
            except Exception as e:
                print(f"✗ {it.get('wiki') or it.get('commons') or it.get('url')} : {e}")
    cred_path.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")


# ════════════════════════════════════════════════════════════════════
# Rendu (utilisé par build_apkg.py)
# ════════════════════════════════════════════════════════════════════
def charger(json_dir):
    d = Path(json_dir) / DOSSIER
    cp = d / "credits.json"
    return d, (json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {})


def html_verso(portraits, credits):
    """Rangée de portraits ronds + nom + légende + crédit (verso)."""
    out = []
    for p in portraits:
        f = nom_fichier(p)
        cr = credits.get(f, {})
        nom = html.escape(p.get("nom") or p["wiki"])
        leg = f'<span class="pt-leg">{html.escape(p["legende"])}</span>' if p.get("legende") else ""
        crd = " · ".join(x for x in (cr.get("auteur"), cr.get("licence")) if x)
        crd = f'<span class="pt-cr">Photo : {html.escape(crd)}, Wikimedia Commons</span>' if crd else ""
        out.append(f'<figure class="pt"><img src="{html.escape(f)}" alt=""><figcaption><b>{nom}</b>{leg}{crd}</figcaption></figure>')
    return "".join(out)


def html_nom(p, credits):
    """Verso de la carte « Qui est-ce ? » : nom, légende, crédit."""
    cr = credits.get(nom_fichier(p), {})
    crd = " · ".join(x for x in (cr.get("auteur"), cr.get("licence")) if x)
    return (f'<div class="pt-nom">{html.escape(p.get("nom") or p["wiki"])}</div>'
            + (f'<div class="pt-sous">{html.escape(p["legende"])}</div>' if p.get("legende") else "")
            + (f'<div class="pt-sous pt-cr">Photo : {html.escape(crd)}, Wikimedia Commons</div>' if crd else ""))


def html_recto(portraits, credits):
    """Photo(s) au recto, sous la question, quand la personne y est nommée (sans nom : il est déjà dans la question)."""
    return "".join(f'<img class="pt-r" src="{html.escape(nom_fichier(p))}" alt="">' for p in portraits)


def html_images(images, credits):
    """Image(s) importée(s) : image nette, légende et crédit discret dessous."""
    out = []
    for im in images:
        f = nom_image(im)
        cr = credits.get(f, {})
        crd = " · ".join(x for x in (cr.get("auteur"), cr.get("licence")) if x)
        src = "Wikimedia Commons" if im.get("commons") else ""
        crd = f'<span class="im-cr">{html.escape(crd)}{", " + src if src and crd else src}</span>' if (crd or src) else ""
        leg = f'<span class="im-leg">{html.escape(im["legende"])}</span>' if im.get("legende") else ""
        out.append(f'<figure class="im"><img src="{html.escape(f)}" alt="">'
                   + (f"<figcaption>{leg}{crd}</figcaption>" if leg or crd else "") + "</figure>")
    return "".join(out)


def html_visage(p):
    return f'<div class="pt-visage"><img src="{html.escape(nom_fichier(p))}" alt=""></div>'


CSS = """
/* ═══ V11 : portraits ═══ */
.portraits { display:flex; flex-wrap:wrap; gap:10px 22px; margin:10px 0 6px; }
.pt { display:flex; align-items:center; gap:12px; margin:0; min-width:0; }
.pt img { width:92px; height:92px; border-radius:50%; object-fit:cover; object-position:50% 22%; flex:none;
  border:2px solid var(--line); background:var(--chip); }
.pt figcaption { display:flex; flex-direction:column; line-height:1.3; font-size:15px; }
.pt-leg { font-size:13.5px; color:var(--muted); }
.pt-cr { font-size:10.5px; color:var(--muted); opacity:.75; margin-top:2px; }
.portraits-r { display:flex; justify-content:center; gap:12px; margin:12px 0 4px; }
.pt-r { width:150px; height:170px; border-radius:12px; object-fit:cover; object-position:50% 20%;
  box-shadow:0 6px 22px -10px rgba(0,0,0,.45); }
@media (max-width:600px) { .pt-r { width:120px; height:136px; } }
.im { margin:8px auto 4px; text-align:center; }
.im img { max-width:min(100%, 520px); max-height:34vh; border-radius:8px; background:#fff; padding:4px; box-sizing:border-box; }
.im figcaption { display:flex; flex-direction:column; align-items:center; margin-top:4px; }
.im-leg { font-size:14px; }
.im-cr { font-size:10.5px; color:var(--muted); opacity:.75; }
.images-r .im img { max-height:30vh; }
.pt-visage { text-align:center; margin:14px 0 6px; }
.pt-visage img { width:190px; height:190px; border-radius:50%; object-fit:cover; object-position:50% 22%;
  border:3px solid var(--line); box-shadow:0 6px 24px -10px rgba(0,0,0,.35); }
.pt-nom { font-size:26px; font-weight:750; text-align:center; margin:4px 0 2px; }
.pt-sous { text-align:center; color:var(--muted); font-size:15px; }
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage : python3 portraits.py cartes.json")
    main(sys.argv[1])

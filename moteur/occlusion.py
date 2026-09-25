"""
occlusion.py — Occlusion d'image (façon « Image Occlusion Enhanced ») pour le moteur V10.

Une note JSON {"modele": "occlusion", ...} est DÉPLIÉE en autant de cartes « basique » qu'il y a de
zones ciblées : au recto, l'image avec les étiquettes masquées et la zone visée en orange « ? » ;
au verso, l'image avec toutes les étiquettes et la bonne réponse surlignée.

Image : un SVG écrit directement dans le JSON (schéma original dessiné par Claude) ou un fichier
(PNG, JPG, SVG) posé à côté du JSON (figure d'un cours, capture de diapositive). Les zones sont des
points (x, y) dans le repère de l'image ; les étiquettes se rangent seules à gauche et à droite.
"""
import html
import re
from pathlib import Path

from visuels import text_w

MARGE = 18          # espace entre l'image et les colonnes d'étiquettes
FS = 13
H_BOITE = 24
ECART = 30          # écart vertical minimal entre deux étiquettes


class OcclusionError(ValueError):
    pass


def _viewbox(svg):
    m = re.search(r'viewBox="([-\d.\s,]+)"', svg)
    if m:
        vx, vy, vw, vh = [float(v) for v in re.split(r"[\s,]+", m.group(1).strip())]
        return vx, vy, vw, vh
    w = re.search(r'\bwidth="([\d.]+)', svg)
    h = re.search(r'\bheight="([\d.]+)', svg)
    if w and h:
        return 0.0, 0.0, float(w.group(1)), float(h.group(1))
    raise OcclusionError("le SVG de l'image doit avoir un viewBox (ou width et height)")


def _range(ys, top, bottom):
    """Place des boîtes au plus près des y voulus, sans chevauchement, entre top et bottom."""
    out = []
    for y in ys:
        out.append(max(y, (out[-1] + ECART) if out else top))
    over = (out[-1] if out else 0) - bottom
    if over > 0:  # trop bas : on remonte le paquet, sans dépasser le haut
        out = [y - over for y in out]
        for k in range(len(out)):
            out[k] = max(out[k], top + k * ECART)
    return out


def rendre(image, zones, cible=None, revele=True, mode="tout_masquer", largeur=None, hauteur=None):
    """image : SVG inline (chaîne commençant par <svg) ou nom de fichier (href relatif, média Anki).
    zones : [{"label", "x", "y"}] dans le repère de l'image. cible : index (0-based) de la zone
    visée. revele=False → recto (masques), True → verso (seule la cible est dévoilée, surlignée)."""
    if image.lstrip().startswith("<svg"):
        vx, vy, W, H = _viewbox(image)
        inner = re.sub(r"^\s*<svg\b[^>]*>", "", image.strip())
        inner = re.sub(r"</svg>\s*$", "", inner)
        # groupe translaté plutôt qu'un <svg> imbriqué : le CSS des cartes (width:100%) le déformerait
        corps = f'<g transform="translate({{TX}},{{TY}})">{inner}</g>'
    else:
        if not (largeur and hauteur):
            raise OcclusionError("image en fichier : indique \"largeur\" et \"hauteur\" (repère des points)")
        vx, vy, W, H = 0.0, 0.0, float(largeur), float(hauteur)
        corps = (f'<image href="{html.escape(image)}" x="{{X}}" y="{{Y}}" width="{W:g}" height="{H:g}" '
                 f'preserveAspectRatio="xMidYMid meet"/>')
    if not zones:
        raise OcclusionError("aucune zone")
    for z in zones:
        if not (vx <= z["x"] <= vx + W and vy <= z["y"] <= vy + H):
            raise OcclusionError(f"zone « {z['label']} » hors de l'image ({z['x']}, {z['y']})")
    bw = max(text_w(z["label"], FS) for z in zones) + 22
    bw = max(bw, 70)
    gauche = [k for k, z in enumerate(zones) if z["x"] - vx < W / 2]
    droite = [k for k, z in enumerate(zones) if z["x"] - vx >= W / 2]
    LW = (bw + MARGE) if gauche else 4
    RW = (bw + MARGE) if droite else 4
    ox, oy = LW, 14            # origine de l'image dans le SVG final
    TW, TH = LW + W + RW, H + 28
    P = lambda z: (ox + z["x"] - vx, oy + z["y"] - vy)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TW:g} {TH:g}" width="100%" '
         f'style="max-width:{min(TW * 1.1, 640):.0f}px;display:block;margin:0 auto" '
         f'font-family="Helvetica, Arial, sans-serif" class="vz-occlusion {"vz-occ-verso" if revele else "vz-occ-recto"}">',
         corps.replace("{X}", f"{ox:g}").replace("{Y}", f"{oy:g}").replace("{TX}", f"{ox - vx:g}").replace("{TY}", f"{oy - vy:g}")]
    for cote, ids in (("g", gauche), ("d", droite)):
        ids = sorted(ids, key=lambda k: zones[k]["y"])
        ys = _range([P(zones[k])[1] for k in ids], 14, TH - 14)
        for k, ly in zip(ids, ys):
            z = zones[k]
            px, py = P(z)
            bx = 4 if cote == "g" else ox + W + MARGE
            ax = bx + bw if cote == "g" else bx
            hl = (k == cible)
            s.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{ax:.1f}" y2="{ly:.1f}" stroke="#6b7280" stroke-width="1.2"/>')
            s.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.4" fill="#374151" stroke="#ffffff" stroke-width="1"/>')
            cx = bx + bw / 2
            if revele and hl:  # verso : seule la zone cherchée est dévoilée
                s.append(f'<rect x="{bx:.1f}" y="{ly - H_BOITE / 2:.1f}" width="{bw:.1f}" height="{H_BOITE}" rx="6" fill="#FFF3C4" stroke="#E0A100" stroke-width="2"/>')
                s.append(f'<text x="{cx:.1f}" y="{ly + 4.5:.1f}" text-anchor="middle" font-size="{FS}" fill="#1f2937" font-weight="700">{html.escape(z["label"])}</text>')
            elif hl:
                s.append(f'<rect x="{bx:.1f}" y="{ly - H_BOITE / 2:.1f}" width="{bw:.1f}" height="{H_BOITE}" rx="6" fill="#F59E0B" stroke="#B45309" stroke-width="2"/>')
                s.append(f'<text x="{cx:.1f}" y="{ly + 5.5:.1f}" text-anchor="middle" font-size="16" fill="#ffffff" font-weight="800">?</text>')
            elif mode == "un_seul":   # les autres étiquettes restent lisibles
                s.append(f'<rect x="{bx:.1f}" y="{ly - H_BOITE / 2:.1f}" width="{bw:.1f}" height="{H_BOITE}" rx="6" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>')
                s.append(f'<text x="{cx:.1f}" y="{ly + 4.5:.1f}" text-anchor="middle" font-size="{FS}" fill="#4b5563">{html.escape(z["label"])}</text>')
            else:                      # tout masquer : boîtes grises numérotées
                s.append(f'<rect x="{bx:.1f}" y="{ly - H_BOITE / 2:.1f}" width="{bw:.1f}" height="{H_BOITE}" rx="6" fill="#E5E7EB" stroke="#9CA3AF" stroke-width="1"/>')
                s.append(f'<text x="{cx:.1f}" y="{ly + 4.5:.1f}" text-anchor="middle" font-size="12" fill="#6B7280">{k + 1}</text>')
    s.append("</svg>")
    return "".join(s)


def deplier(c, i, json_dir, media):
    """Transforme une note {"modele": "occlusion"} en liste de cartes « basique » (une par cible).
    media : ensemble où ajouter le chemin du fichier image à embarquer dans le .apkg."""
    image = c.get("image") or ""
    if not image:
        raise OcclusionError("champ \"image\" manquant (SVG inline ou nom de fichier)")
    if not image.lstrip().startswith("<svg"):
        p = (Path(json_dir) / image)
        if not p.exists():
            raise OcclusionError(f"fichier image introuvable : {p}")
        media.add(str(p.resolve()))
        image = p.name
    zones = c.get("zones") or []
    for z in zones:
        if not all(k in z for k in ("label", "x", "y")):
            raise OcclusionError("chaque zone a \"label\", \"x\" et \"y\"")
    cibles = c.get("cibles", "toutes")
    if cibles == "toutes":
        cibles = list(range(len(zones)))
    else:  # numéros 1-based ou libellés
        cibles = [(k - 1) if isinstance(k, int) else next(j for j, z in enumerate(zones) if z["label"] == k) for k in cibles]
    mode = c.get("mode", "tout_masquer")
    kw = dict(mode=mode, largeur=c.get("largeur"), hauteur=c.get("hauteur"))
    base = {k: v for k, v in c.items() if k not in ("modele", "image", "zones", "cibles", "mode", "largeur", "hauteur")}
    out = []
    for k in cibles:
        z = zones[k]
        carte = dict(base)
        carte["modele"] = "basique"
        if not c.get("type"):
            carte.setdefault("icone", "🖼️")
        carte["ancre"] = f"{c.get('ancre', 'Occlusion')} — zone {k + 1}"   # le recto ne doit pas trahir la réponse
        carte["_guid"] = f"{c.get('ancre', 'Occlusion')} — {z['label']}"     # identité stable (réimport = mise à jour)
        carte["_sans_n"] = True
        carte["question"] = z.get("question", c.get("question", "Quelle structure est cachée sous le « ? » ?"))
        carte["reponse"] = z.get("reponse") or f"<span class=\"hl act\">{html.escape(z['label'])}</span>"
        for champ in ("puces", "piege", "memo", "lien", "indice", "anecdote", "saisie", "saisie_consigne"):
            if champ in z:
                carte[champ] = z[champ]
        if "saisie" not in z:  # une saisie commune n'aurait pas de sens pour chaque zone
            carte.pop("saisie", None)
            carte.pop("saisie_consigne", None)
        carte["visuel_recto"] = rendre(image, zones, k, revele=False, **kw)
        carte["visuel"] = rendre(image, zones, k, revele=True, **kw)
        carte["tags"] = list(dict.fromkeys(c.get("tags", []) + ["occlusion"]))
        out.append(carte)
    return out

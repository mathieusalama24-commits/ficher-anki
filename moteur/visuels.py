"""
visuels.py — Moteur visuel des cartes Ficher.

Le modèle écrit une SPEC JSON courte ; ce module produit le SVG/HTML final avec une géométrie
calculée (pas de chevauchement, textes renvoyés à la ligne, lisible en mode clair ET sombre).

Types disponibles (clé "type" de la spec) :
  chaine, bifurcation, boucle, frise, periodes, barres, jauge, courbe, matrice,
  reseau, balance, carte, chiffre, tableau, arbre, avant_apres
Voir SPEC_DOC en bas de fichier pour le format exact de chacun.

Style « manuel de cours » : boîtes pastel à bordure fine de la couleur de la catégorie, texte foncé,
liaisons fines, annotations en italique ("note" sur nœuds et liens), légende discrète ("legende").
Les couleurs des schémas passent par des variables CSS (--vz-*) : schema_css() renvoie leur définition
en mode clair et sombre, à inclure dans le CSS des cartes. Sans ce CSS, les valeurs de repli (clair)
s'appliquent.

Nouveaux types :
  arbre        décomposition hiérarchique descendante (causes d'un conflit, niveaux d'une organisation),
               avec annotations de niveau à gauche ("niveaux") et verbes sur les branches.
  avant_apres  deux états côte à côte ; les éléments communs sont alignés, les changements marqués
               automatiquement (+ apparaît, − disparaît, Δ change).
"""
import html
import json
import math
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
# PALETTE — source unique (le builder l'importe)
# code : (libellé, fond, texte sur fond, mot-clé clair, mot-clé sombre)
# ════════════════════════════════════════════════════════════════════
PALETTE = {
    "risk":  ("Conflit / risque",            "#C62828", "#fff", "#C62828", "#EF9A9A"),
    "eco":   ("Économie",                    "#7B1FA2", "#fff", "#7B1FA2", "#CE93D8"),
    "pol":   ("Politique",                   "#1F4E9C", "#fff", "#1F4E9C", "#90B4F0"),
    "soc":   ("Social",                      "#F48FB1", "#111", "#C2185B", "#F48FB1"),
    "env":   ("Environnement / climat",      "#2E7D32", "#fff", "#2E7D32", "#81C784"),
    "date":  ("Date / période",              "#455A64", "#fff", "#455A64", "#B0BEC5"),
    "act":   ("Acteur / exemple / auteur",   "#0277BD", "#fff", "#0277BD", "#4FC3F7"),
    "enj":   ("Enjeu géopolitique",          "#FDD835", "#111", "#9A7B00", "#FFEE58"),
    "conc":  ("Concept théorique",           "#00897B", "#fff", "#00796B", "#4DB6AC"),
    "inst":  ("Institution / OI",            "#BDBDBD", "#111", "#616161", "#BDBDBD"),
    "instr": ("Instrument de puissance",     "#E65100", "#fff", "#D84315", "#FFB74D"),
    "res":   ("Ressource / infrastructure",  "#6D4C41", "#fff", "#6D4C41", "#BCAAA4"),
    "prosp": ("Prospective / scénario",      "#FFF59D", "#111", "#8D7B00", "#FFF59D"),
}
TERM_FILL, TERM_STROKE, TERM_TXT = "#E0F2F1", "#00695C", "#004D40"
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"
W = 420  # largeur logique : ≈ 0,9× sur mobile → textes 13px ≈ 12px réels

REGIONS_FILE = Path(__file__).with_name("regions.json")
REGIONS = {
    # id: (lon0, lon1, lat0, lat1, W, H) — correspond aux fichiers média _geo_<id>.svg
    "monde": (-170, 180, -56, 78, 680, 265), "europe": (-12, 42, 34, 71, 391, 440),
    "baltique": (9, 32, 53, 66.5, 378, 440), "ukraine": (21, 41, 43.5, 53, 617, 440),
    "mer_noire": (26, 43, 40, 48, 673, 440), "caucase": (36, 51, 37.5, 44.5, 680, 420),
    "levant": (32, 40, 29, 35.5, 458, 440), "moyen_orient": (25, 63, 12, 42, 497, 440),
    "ormuz": (47, 62, 21, 31.5, 564, 440), "mer_rouge": (29, 45, 11, 32, 312, 440),
    "bab_el_mandeb": (36, 53, 8, 20, 605, 440), "inde_pakistan": (60, 98, 5, 37, 488, 440),
    "malacca": (94, 110, -7, 10, 414, 440), "mer_chine_sud": (102, 124, -1, 25, 364, 440),
    "taiwan": (115, 128, 18, 29, 477, 440), "asie_est": (115, 146, 22, 46, 471, 440),
    "indo_pacifique": (40, 180, -48, 45, 662, 440), "afrique": (-20, 55, -36, 38, 446, 440),
    "sahel": (-18, 25, 8, 25, 680, 280), "rdc_grands_lacs": (11, 36, -14, 6, 549, 440),
    "caraibes": (-92, -58, 5, 28, 624, 440), "arctique_nord": (-45, 35, 55, 78, 610, 440),
}


class SpecError(ValueError):
    pass


# ─── utilitaires ────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def col(cat, default="date"):
    if cat not in PALETTE:
        if cat:
            raise SpecError(f'catégorie inconnue « {cat} » (autorisées : {", ".join(PALETTE)})')
        cat = default
    return PALETTE[cat]


def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _hex(c):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in c)


def tint(h, t):
    return _hex([v + (255 - v) * t for v in _rgb(h)])


def shade(h, t):
    return _hex([v * (1 - t) for v in _rgb(h)])


def text_w(s, fs):
    w = 0
    for ch in str(s):
        o = ord(ch)
        w += fs * (1.15 if o > 0x1F000 else 0.58 if ch.isupper() or ch.isdigit() else 0.52 if o > 32 else 0.3)
    return w


def _cut(word, maxw, fs):
    """Coupe un mot trop long pour la boîte, avec trait d'union (« Élargisse-/ment »)."""
    out, cur = [], ""
    for ch in word:
        if cur and text_w(cur + ch + "-", fs) > maxw:
            out.append(cur + "-")
            cur = ch
        else:
            cur += ch
    return out + [cur]


def wrap(s, maxw, fs, maxlines=3):
    words, lines, cur = [], [], ""
    for w_ in str(s or "").split():
        words += _cut(w_, maxw, fs) if text_w(w_, fs) > maxw and len(w_) > 4 else [w_]
    for w_ in words:
        if cur.endswith("-"):
            lines.append(cur)
            cur = w_
            continue
        t = f"{cur} {w_}".strip()
        if text_w(t, fs) > maxw and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        lines[-1] = lines[-1].rstrip(" ,;") + "…"
    return lines or [""]


# ════════════════════════════════════════════════════════════════════
# STYLE « MANUEL DE COURS » — boîtes pastel à bordure fine, liaisons fines, annotations en italique.
# Les couleurs passent par des variables CSS (--vz-<cat>-p/-b/-d, --vz-term-*, --vz-edge, --vz-note)
# définies par schema_css() : pastel clair en mode jour, teinte sombre + bordure vive en mode nuit.
# Chaque var() porte une valeur de repli (mode clair) : le schéma reste lisible même sans ce CSS.
# ════════════════════════════════════════════════════════════════════
NIGHT_BG = "#16181d"
FS_MIN = 12.5  # plus petit corps de texte : ≈ 11,2 px réels sur un téléphone de 400 px (échelle 376/420)


def _mix(h1, h2, t):
    """t × h1 + (1 − t) × h2."""
    a, b = _rgb(h1), _rgb(h2)
    return _hex([x * t + y * (1 - t) for x, y in zip(a, b)])


def _vz_tables():
    light, dark = {}, {}
    for k, (_, bg, _, kl, kd) in PALETTE.items():
        light[k] = {"p": tint(bg, 0.86), "b": kl, "d": shade(kl, 0.3)}
        dark[k] = {"p": _mix(bg, NIGHT_BG, 0.3), "b": kd, "d": tint(kd, 0.55)}
    light["term"] = {"p": TERM_FILL, "b": TERM_STROKE, "d": TERM_TXT}
    dark["term"] = {"p": _mix("#00897B", NIGHT_BG, 0.3), "b": "#4DB6AC", "d": "#B2DFDB"}
    light["n"] = {"edge": "#8b929c", "note": "#5f6773", "ghost": "#c9cdd3"}
    dark["n"] = {"edge": "#7d8591", "note": "#aab2bd", "ghost": "#4a4f58"}
    return light, dark


VZ_LIGHT, VZ_DARK = _vz_tables()


def schema_css():
    """Variables CSS des schémas (à ajouter au CSS commun des cartes). Mêmes sélecteurs que build_css()."""
    def decl(t):
        out = []
        for k, d in t.items():
            for s, v in d.items():
                out.append(f"--vz-{k}-{s}:{v};" if k != "n" else f"--vz-{s}:{v};")
        return " ".join(out)
    return (f".card {{ {decl(VZ_LIGHT)} }}\n"
            f".nightMode, .night_mode, .nightMode .card, .night_mode .card, .card.nightMode, .card.night_mode {{ {decl(VZ_DARK)} }}\n")


def cv(cat, k):
    """Couleur de catégorie en variable CSS avec repli : k = p (fond pastel), b (bordure), d (texte)."""
    return f"var(--vz-{cat}-{k},{VZ_LIGHT[cat][k]})"


def nv(k):
    """Couleur neutre : edge (liaisons), note (annotations), ghost (emplacements vides)."""
    return f"var(--vz-{k},{VZ_LIGHT['n'][k]})"


BG = "var(--bg,#fbfbfa)"
HALO = f"paint-order:stroke;stroke:{BG};stroke-width:3.5px;stroke-linejoin:round;"


def ck(cat, default="date"):
    """Valide une catégorie et renvoie sa clé."""
    col(cat, default)
    return cat if cat in PALETTE else default


def txt(x, y, lines, fs, fill, weight=400, anchor="middle", italic=False, opacity=None, lh=1.25, halo=False):
    if isinstance(lines, str):
        lines = [lines]
    n = len(lines)
    y0 = y - (n - 1) * fs * lh / 2
    extra = (' font-style="italic"' if italic else "") + (f' opacity="{opacity}"' if opacity else "")
    style = (f"fill:{fill};" if str(fill).startswith("var(") else "") + (HALO if halo else "")
    fill_attr = (f'style="{style}"' if style else "") + ("" if str(fill).startswith("var(") else f' fill="{fill}"')
    spans = "".join(
        f'<tspan x="{x:.1f}" y="{y0 + i * fs * lh:.1f}">{esc(l)}</tspan>' for i, l in enumerate(lines)
    )
    return (f'<text text-anchor="{anchor}" dominant-baseline="central" font-size="{fs:g}" '
            f'font-weight="{weight}" {fill_attr}{extra}>{spans}</text>')


def paint(fill=None, stroke=None, sw=None, dash=None, extra=""):
    st = ""
    if fill:
        st += f"fill:{fill};"
    if stroke:
        st += f"stroke:{stroke};"
    if sw:
        st += f"stroke-width:{sw};"
    if dash:
        st += f"stroke-dasharray:{dash};"
    return f'style="{st}{extra}"'


class Svg:
    def __init__(self, w=W, arrow=8):
        self.w, self.parts, self.markers, self.asz = w, [], {}, arrow

    def add(self, s):
        self.parts.append(s)

    def arrow_id(self, color):
        mid = "vza" + "".join(c for c in color if c.isalnum())[-24:] + str(round(self.asz))
        self.markers[mid] = color
        return mid

    def out(self, h):
        defs = "".join(
            f'<marker id="{m}" viewBox="0 0 10 10" refX="8.6" refY="5" markerWidth="{self.asz:g}" markerHeight="{self.asz:g}" '
            f'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1,1.2 L9,5 L1,8.8 z" {paint(c)}/></marker>'
            for m, c in self.markers.items()
        )
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {h:.0f}" width="100%" '
                f'style="max-width:100%;height:auto;" font-family="{FONT}">'
                f'<defs>{defs}</defs>{"".join(self.parts)}</svg>')


def badge(s, x, y, label, cat, r=9.5):
    """Pastille numérotée : disque de la couleur de bordure, chiffre de la couleur du fond de carte."""
    s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" {paint(cv(cat, "b"), BG, 1.6)}/>')
    s.add(txt(x, y + 0.5, label, FS_MIN, BG, 800))


def node_h(label, sous, w, fs=13.5):
    lab = wrap(label, w - 22, fs, 3)
    sub = wrap(sous, w - 22, max(FS_MIN, fs - 1), 2) if sous else []
    return lab, sub, 14 + len(lab) * fs * 1.25 + (len(sub) * max(FS_MIN, fs - 1) * 1.25 + 3 if sub else 0)


def node(s, x, y, w, label, sous, cat, badge_=None, terminal=False, fs=13.5, strong=False, dashed=False, hmin=0):
    """Boîte pastel centrée en (x, y), bordure fine de la couleur de la catégorie. Retourne sa hauteur."""
    k = "term" if terminal else ck(cat)
    lab, sub, h0 = node_h(label, sous, w, fs)
    h = max(h0, hmin)
    top = y - h / 2
    ty = top + (h - h0) / 2  # texte centré verticalement dans une boîte agrandie
    sw = 2 if (terminal or strong) else 1.3
    s.add(f'<rect x="{x - w / 2:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" '
          f'{paint(cv(k, "p"), cv(k, "b"), sw, "5 4" if dashed else None)}/>')
    fsub = max(FS_MIN, fs - 1)
    s.add(txt(x, ty + 7 + len(lab) * fs * 1.25 / 2, lab, fs, cv(k, "d"), 650))
    if sub:
        s.add(txt(x, ty + 7 + len(lab) * fs * 1.25 + 3 + len(sub) * fsub * 1.25 / 2, sub, fsub, cv(k, "d"), 400, italic=True, opacity=0.85))
    if badge_:
        badge(s, x - w / 2 + 1, top + 1, badge_, k)
    return h


def note_txt(s, x, y, text, maxw, anchor="start", maxlines=3, fs=FS_MIN, color=None):
    """Petite annotation en italique (« Divide », « Merge »…). Retourne (nb de lignes, hauteur)."""
    if not text:
        return 0, 0
    lines = wrap(text, maxw, fs, maxlines)
    s.add(txt(x, y, lines, fs, color or nv("note"), 500, anchor=anchor, italic=True, halo=True))
    return len(lines), len(lines) * fs * 1.25


def ann(s, x, y, label, cat, anchor="middle", fs=FS_MIN, para=False):
    """Verbe de liaison : italique, couleur de la catégorie, halo pour rester net sur les traits."""
    s.add(txt(x, y, label, fs, cv("risk" if para else ck(cat), "d"), 600, anchor=anchor, italic=True, halo=True))


def link(s, x1, y1, x2, y2, color, dashed=False, width=1.4, curve=0.0, arrow=True):
    mid = s.arrow_id(color) if arrow else None
    if curve:
        mx, my = (x1 + x2) / 2 - (y2 - y1) * curve, (y1 + y2) / 2 + (x2 - x1) * curve
        d = f"M{x1:.1f},{y1:.1f} Q{mx:.1f},{my:.1f} {x2:.1f},{y2:.1f}"
    else:
        d = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
    s.add(f'<path d="{d}" {paint("none", color, width, "6 4" if dashed else None, "stroke-linecap:round;")}'
          + (f' marker-end="url(#{mid})"' if mid else "") + "/>")


def pill(s, x, y, label, cat, fs=12):
    """Étiquette à couleurs FIXES (sur les fonds de carte, qui restent clairs en mode sombre)."""
    c = col(cat or "date")[1]
    w = text_w(label, fs) + 16 * max(1.0, fs / 12)
    h = 20 * max(1.0, fs / 12)
    s.add(f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="#ffffff" fill-opacity="0.92" stroke="{c}" stroke-width="1.2"/>')
    s.add(txt(x, y + 0.5, label, fs, shade(c, 0.3), 600, italic=True))
    return w


def legende(s, y, items, x0=10):
    """Légende discrète : pastilles pastel + libellés gris, retour à la ligne automatique. Retourne le nouveau y."""
    if not items:
        return y
    x, y = x0, y + 12
    for it in items:
        if isinstance(it, str):
            it = {"label": it}
        lab = it.get("label", "")
        wl = text_w(lab, FS_MIN) + 26
        if x + wl > W - 6 and x > x0:
            x, y = x0, y + 20
        if it.get("badge"):
            k = ck(it.get("cat"))
            s.add(f'<circle cx="{x + 8}" cy="{y}" r="8.5" {paint(cv(k, "b"))}/>')
            s.add(txt(x + 8, y + 0.5, it["badge"], FS_MIN, BG, 800))
            s.add(txt(x + 21, y, lab, FS_MIN, nv("note"), 500, anchor="start"))
        elif it.get("cat"):
            k = ck(it["cat"])
            s.add(f'<rect x="{x}" y="{y - 6}" width="14" height="12" rx="3" {paint(cv(k, "p"), cv(k, "b"), 1.2)}/>')
            s.add(txt(x + 19, y, lab, FS_MIN, nv("note"), 500, anchor="start"))
        else:
            s.add(txt(x, y, lab, FS_MIN, nv("note"), 500, anchor="start", italic=True))
            wl -= 19
        x += wl + 10
    return y + 12


def need(spec, *keys):
    for k in keys:
        if k not in spec or spec[k] in (None, "", []):
            raise SpecError(f"spec « {spec.get('type')} » : clé obligatoire manquante « {k} »")


BADGES = "①②③④⑤⑥⑦⑧⑨"
NUMS = "123456789"


# ════════════════════════════════════════════════════════════════════
# 1. CHAÎNE CAUSALE (verticale : lisible sur mobile)
# ════════════════════════════════════════════════════════════════════
def r_chaine(sp):
    need(sp, "noeuds")
    nds, liens = sp["noeuds"], sp.get("liens", [])
    if not 2 <= len(nds) <= 5:
        raise SpecError("chaine : 2 à 5 nœuds")
    notes = any(n.get("note") for n in nds)
    bw = 250 if notes else 290
    cx = 14 + bw / 2 if notes else W / 2 - 34
    nx = cx + bw / 2 + 12  # colonne des annotations
    s, y = Svg(), 16
    for i, n in enumerate(nds):
        term = i == len(nds) - 1
        _, _, h = node_h(n.get("label"), n.get("sous"), bw)
        node(s, cx, y + h / 2, bw, n.get("label"), n.get("sous"), n.get("cat"),
             badge_="⚑" if term else NUMS[i], terminal=term)
        if n.get("note"):
            note_txt(s, nx, y + h / 2, n["note"], W - nx - 4)
        if term:
            y += h
            break
        l = liens[i] if i < len(liens) else {}
        lk, par = ck(l.get("cat")), l.get("paradoxal", False)
        gap = 58 if l.get("note") else 44
        link(s, cx, y + h + 3, cx, y + h + gap - 4, cv("risk" if par else lk, "b"), dashed=par)
        if l.get("verbe"):
            vy = y + h + gap / 2 - (7 if l.get("note") else 0)
            ann(s, cx + 12, vy, ("⚡ " if par else "") + l["verbe"], lk, anchor="start", para=par)
            if l.get("note"):
                note_txt(s, cx + 12, vy + 16, l["note"], W - cx - 20, maxlines=1)
        y += h + gap
    y = legende(s, y + 6, sp.get("legende"))
    return s.out(y + 12)


# ════════════════════════════════════════════════════════════════════
# 2. BIFURCATION (1 cause → 2 effets → 1 enjeu)
# ════════════════════════════════════════════════════════════════════
def r_bifurcation(sp):
    need(sp, "source", "branches", "terminal")
    br = sp["branches"]
    if len(br) != 2:
        raise SpecError("bifurcation : exactement 2 branches")
    s = Svg()
    src = sp["source"]
    _, _, h0 = node_h(src.get("label"), src.get("sous"), 270)
    y0 = 16 + h0 / 2
    node(s, W / 2, y0, 270, src.get("label"), src.get("sous"), src.get("cat"), badge_="1")
    bottom0 = y0 + h0 / 2
    if src.get("note"):
        _, nh = note_txt(s, W / 2, bottom0 + 12, src["note"], 260, anchor="middle", maxlines=1)
        bottom0 += nh + 4
    xs = [W * 0.255, W * 0.745]
    bw = 188
    hb = [node_h(b.get("label"), b.get("sous"), bw)[2] for b in br]
    yb = bottom0 + 80 + max(hb) / 2
    top_b = yb - max(hb) / 2
    for i, b in enumerate(br):
        x = xs[i]
        node(s, x, yb, bw, b.get("label"), b.get("sous"), b.get("cat"), badge_=NUMS[i + 1])
        lk = ck(b.get("lien_cat") or b.get("cat"))
        par = b.get("paradoxal", False)
        sx = W / 2 + (-50 if i == 0 else 50)
        link(s, sx, bottom0 + 3, x, top_b - 4, cv("risk" if par else lk, "b"), dashed=par, curve=0.1 if i == 0 else -0.1)
        if b.get("verbe"):
            mx = (sx + x) / 2 + (-10 if i == 0 else 10)
            ann(s, mx, (bottom0 + top_b) / 2, ("⚡ " if par else "") + b["verbe"], lk,
                anchor="end" if i == 0 else "start", para=par)
    bot_b = yb + max(hb) / 2
    nlines = 0
    for i, b in enumerate(br):
        if b.get("note"):
            nlines = max(nlines, note_txt(s, xs[i], yb + hb[i] / 2 + 10 + 7.5, b["note"], bw - 6, anchor="middle", maxlines=2)[0])
    bot_b += nlines * 15.6 + (6 if nlines else 0)
    t = sp["terminal"]
    _, _, ht = node_h(t.get("label"), t.get("sous"), 290)
    yt = bot_b + 58 + ht / 2
    node(s, W / 2, yt, 290, t.get("label"), t.get("sous"), None, badge_="⚑", terminal=True)
    for i in range(2):
        link(s, xs[i], bot_b + 4, W / 2 + (-70 if i == 0 else 70), yt - ht / 2 - 4, cv("term", "b"),
             curve=-0.08 if i == 0 else 0.08)
    y = yt + ht / 2
    if t.get("note"):
        y += note_txt(s, W / 2, y + 12, t["note"], 280, anchor="middle", maxlines=2)[1] + 4
    y = legende(s, y + 6, sp.get("legende"))
    return s.out(y + 12)


# ════════════════════════════════════════════════════════════════════
# 3. BOUCLE DE RÉTROACTION (cercle vicieux / vertueux, dilemme de sécurité)
# ════════════════════════════════════════════════════════════════════
def r_boucle(sp):
    need(sp, "noeuds")
    nds, liens = sp["noeuds"], sp.get("liens", [])
    n = len(nds)
    if not 3 <= n <= 5:
        raise SpecError("boucle : 3 à 5 nœuds")
    s = Svg()
    bw = 134
    hs = [node_h(nd.get("label"), nd.get("sous"), bw, 13)[2] for nd in nds]
    R, ry = 118, 106
    cx, cy = W / 2, 14 + hs[0] / 2 + ry
    ang = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]
    pos = [(cx + R * math.cos(a), cy + ry * math.sin(a)) for a in ang]

    def inside(px, py, i, pad=7):
        return abs(px - pos[i][0]) < bw / 2 + pad and abs(py - pos[i][1]) < hs[i] / 2 + pad

    for i in range(n):
        a1, a2 = ang[i], ang[i] + 2 * math.pi / n
        j = (i + 1) % n
        pts = [(cx + R * math.cos(a1 + (a2 - a1) * t / 80), cy + ry * math.sin(a1 + (a2 - a1) * t / 80)) for t in range(81)]
        pts = [p_ for p_ in pts if not inside(*p_, i) and not inside(*p_, j)]
        if len(pts) < 2:
            continue
        l = liens[i] if i < len(liens) else {}
        lk = ck(l.get("cat"))
        c = cv(lk, "b")
        mid = s.arrow_id(c)
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s.add(f'<path d="{d}" {paint("none", c, 1.5, None, "stroke-linejoin:round;")} marker-end="url(#{mid})"/>')
        if l.get("verbe"):
            am = (a1 + a2) / 2
            ca = math.cos(am)
            px, py = cx + (R + 14) * ca, cy + (ry + 14) * math.sin(am)
            anchor = "start" if ca > 0.25 else "end" if ca < -0.25 else "middle"
            ann(s, px, py, l["verbe"], lk, anchor=anchor)
    for i, nd in enumerate(nds):
        node(s, pos[i][0], pos[i][1], bw, nd.get("label"), nd.get("sous"), nd.get("cat"), badge_=NUMS[i], fs=13)
    if sp.get("centre"):
        s.add(txt(cx, cy - 6, wrap(sp["centre"], 118, 13.5, 2), 13.5, "currentColor", 700, italic=True))
        s.add(txt(cx, cy + 22, "↻", 18, nv("note"), 400))
    y = legende(s, cy + ry + max(hs) / 2 + 8, sp.get("legende"))
    return s.out(y + 10)


# ════════════════════════════════════════════════════════════════════
# 4. FRISE (jalons datés, étiquettes alternées haut/bas)
# ════════════════════════════════════════════════════════════════════
def r_frise(sp):
    need(sp, "jalons")
    j = sp["jalons"]
    if not 2 <= len(j) <= 7:
        raise SpecError("frise : 2 à 7 jalons")
    s = Svg()
    n = len(j)
    x0, x1 = 34, W - 34
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    slot = min(150, (x1 - x0) / max(n - 1, 1) * 1.85)
    nl = [len(wrap(it.get("label"), slot, FS_MIN + 0.5, 3)) for it in j]
    up_l = max(nl[0::2])
    dn_l = max(nl[1::2]) if n > 1 else 0
    axis_y = 68 + (2 * up_l - 1) * 8.1
    mid = s.arrow_id(nv("edge"))
    s.add(f'<path d="M10,{axis_y} L{W - 6},{axis_y}" {paint("none", nv("edge"), 1.5)} marker-end="url(#{mid})"/>')
    for i, (x, it) in enumerate(zip(xs, j)):
        last = i == n - 1
        k = "term" if last else ck(it.get("cat"))
        up = i % 2 == 0
        sgn = -1 if up else 1
        s.add(f'<line x1="{x:.1f}" y1="{axis_y + sgn * 9}" x2="{x:.1f}" y2="{axis_y + sgn * 30}" {paint(None, cv(k, "b"), 1)}/>')
        s.add(f'<circle cx="{x:.1f}" cy="{axis_y}" r="{10 if last else 7}" {paint(cv(k, "p"), cv(k, "b"), 2)}/>')
        if last:
            s.add(txt(x, axis_y + 0.5, "⚑", FS_MIN, cv(k, "d"), 700))
        lab = wrap(it.get("label"), slot, FS_MIN + 0.5, 3)
        half = max(text_w(l, 13) for l in lab) / 2 + 2
        ax = min(max(x, half), W - half)
        date = str(it.get("date", ""))
        dx = min(max(x, text_w(date, 14) / 2 + 2), W - text_w(date, 14) / 2 - 2)
        s.add(txt(dx, axis_y + sgn * 42, date, 14, cv(k, "d"), 800))
        ly = axis_y + sgn * (60 + (len(lab) - 1) * 8.1)
        s.add(txt(ax, ly, lab, 13, "currentColor", 500))
    y = legende(s, axis_y + 60 + (2 * dn_l - 1) * 8.1 + 4, sp.get("legende"))
    return s.out(y + 8)


# ════════════════════════════════════════════════════════════════════
# 5. PÉRIODES (bandes de durée sur un axe d'années)
# ════════════════════════════════════════════════════════════════════
def r_periodes(sp):
    need(sp, "bandes")
    bd = sp["bandes"]
    a0 = sp.get("debut", min(b["de"] for b in bd))
    a1 = sp.get("fin", max(b["a"] for b in bd))
    if a1 <= a0:
        raise SpecError("periodes : fin ≤ début")
    s = Svg()
    X = lambda a: 20 + (W - 40) * (a - a0) / (a1 - a0)
    rows = max(b.get("ligne", 0) for b in bd) + 1
    top = 20
    ay = top + rows * 54 + 6
    for r_ in sp.get("reperes", []):
        x = X(r_["annee"])
        s.add(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{ay}" {paint(None, cv("risk", "b"), 1.2, "3 3")}/>')
    for b in bd:
        r = b.get("ligne", 0)
        y = top + r * 54
        x1, x2 = X(b["de"]), X(b["a"])
        k = ck(b.get("cat"))
        s.add(f'<rect x="{x1:.1f}" y="{y}" width="{max(x2 - x1, 4):.1f}" height="30" rx="6" {paint(cv(k, "p"), cv(k, "b"), 1.3)}/>')
        lab = b.get("label", "")
        if text_w(lab, 13) < x2 - x1 - 12:
            s.add(txt((x1 + x2) / 2, y + 15, lab, 13, cv(k, "d"), 650))
        else:  # étiquette sous la bande, centrée et bornée au cadre
            hw = text_w(lab, 13) / 2 + 2
            s.add(txt(min(max((x1 + x2) / 2, hw), W - hw), y + 42, lab, 13, cv(k, "d"), 650))
    s.add(f'<line x1="20" y1="{ay}" x2="{W - 20}" y2="{ay}" {paint(None, nv("edge"), 1.2)}/>')
    ticks = sorted({a0, a1} | {b["de"] for b in bd} | {b["a"] for b in bd})
    last_x = -99
    for t in ticks:
        x = X(t)
        if x - last_x < 38 and t not in (a0, a1):
            continue
        last_x = x
        s.add(f'<line x1="{x:.1f}" y1="{ay}" x2="{x:.1f}" y2="{ay + 5}" {paint(None, nv("edge"), 1.2)}/>')
        s.add(txt(min(max(x, 16), W - 16), ay + 17, str(t), FS_MIN, nv("note"), 600))
    h = ay + 30
    for r_ in sp.get("reperes", []):
        s.add(txt(W / 2, h + 6, f'{r_["annee"]} — {r_.get("label", "")}', FS_MIN, cv("risk", "d"), 600, italic=True))
        h += 18
    h = legende(s, h, sp.get("legende"))
    return s.out(h + 8)


# ════════════════════════════════════════════════════════════════════
# 6. BARRES
# ════════════════════════════════════════════════════════════════════
def r_barres(sp):
    need(sp, "barres")
    b = sp["barres"]
    if not 2 <= len(b) <= 6:
        raise SpecError("barres : 2 à 6 barres")
    vmax = max(abs(float(x["valeur"])) for x in b) or 1
    s = Svg()
    lw = min(140, max(text_w(x["label"], 13) for x in b) + 10)
    vals = [x.get("affiche") or f'{float(x["valeur"]):g} {sp.get("unite", "")}'.strip() for x in b]
    vw = max(text_w(v, 13) for v in vals) + 12
    bx, bwmax = lw + 10, W - lw - 10 - vw - 4
    y = 12
    for x, val in zip(b, vals):
        v = float(x["valeur"])
        w_ = max(4, abs(v) / vmax * bwmax)
        k = ck(x.get("cat"), "act")
        lab = wrap(x["label"], lw - 6, 13, 2)
        s.add(txt(lw, y + 14, lab, 13, "currentColor", 600, anchor="end"))
        s.add(f'<rect x="{bx}" y="{y + 2}" width="{w_:.1f}" height="24" rx="5" {paint(cv(k, "p"), cv(k, "b"), 1.3)}/>')
        s.add(txt(bx + w_ + 7, y + 14.5, val, 13, cv(k, "d"), 700, anchor="start"))
        y += 38
    s.add(f'<line x1="{bx}" y1="6" x2="{bx}" y2="{y - 6}" {paint(None, nv("edge"), 1.2)}/>')
    if sp.get("note"):
        y += note_txt(s, W / 2, y + 8, sp["note"], W - 20, anchor="middle", maxlines=2)[1]
    y = legende(s, y, sp.get("legende"))
    return s.out(y + 6)


# ════════════════════════════════════════════════════════════════════
# 7. JAUGES EN ANNEAU
# ════════════════════════════════════════════════════════════════════
def r_jauge(sp):
    need(sp, "jauges")
    g = sp["jauges"]
    if not 1 <= len(g) <= 3:
        raise SpecError("jauge : 1 à 3 jauges")
    s = Svg()
    n, r = len(g), 46
    circ = 2 * math.pi * r
    hmax = 0
    for i, it in enumerate(g):
        cx = W * (i + 1) / (n + 1)
        pct = max(0.0, min(100.0, float(it["pct"])))
        k = ck(it.get("cat"), "act")
        s.add(f'<circle cx="{cx:.1f}" cy="72" r="{r}" {paint("none", cv(k, "p"), 13)}/>')
        s.add(f'<circle cx="{cx:.1f}" cy="72" r="{r + 6.5}" {paint("none", cv(k, "b"), 0.8)} opacity="0.5"/>')
        s.add(f'<circle cx="{cx:.1f}" cy="72" r="{r}" {paint("none", cv(k, "b"), 13, f"{circ * pct / 100:.1f} {circ:.1f}", "stroke-linecap:round;")} '
              f'transform="rotate(-90 {cx:.1f} 72)"/>')
        s.add(txt(cx, 72, f'{pct:g} %', 22, cv(k, "d"), 800))
        lab = wrap(it.get("label", ""), W / (n + 1) + 24, 13, 3)
        s.add(txt(cx, 146 + (len(lab) - 1) * 8.1, lab, 13, "currentColor", 600))
        hmax = max(hmax, 146 + len(lab) * 16.2)
        if it.get("note"):
            hmax = max(hmax, hmax + note_txt(s, cx, hmax + 6, it["note"], W / (n + 1) + 20, anchor="middle", maxlines=2)[1])
    y = legende(s, hmax, sp.get("legende"))
    return s.out(y + 8)


# ════════════════════════════════════════════════════════════════════
# 8. COURBE (évolution temporelle, 1 à 3 séries)
# ════════════════════════════════════════════════════════════════════
def nice_ticks(lo, hi, n=4):
    span = hi - lo or 1
    step = 10 ** math.floor(math.log10(span / n))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= n:
            step *= m
            break
    start = math.floor(lo / step) * step
    ticks, t = [], start
    while t <= hi + step * 0.001:
        ticks.append(round(t, 10))
        t += step
    if ticks[-1] < hi - step * 0.001:
        ticks.append(round(t, 10))
    return ticks


def r_courbe(sp):
    need(sp, "series")
    se = sp["series"]
    if not 1 <= len(se) <= 3:
        raise SpecError("courbe : 1 à 3 séries")
    xs = [p[0] for x in se for p in x["points"]]
    ys = [p[1] for x in se for p in x["points"]]
    x0, x1 = min(xs), max(xs)
    lo = min(0, min(ys)) if sp.get("zero", True) else min(ys)
    yt = nice_ticks(lo, max(ys))
    y0, y1 = yt[0], yt[-1]
    s = Svg()
    yl = max(text_w(f"{t:g}", FS_MIN) for t in yt)
    schema = sp.get("schema", False)  # courbe théorique : ni graduations chiffrées ni valeurs finales
    vl = 0 if schema else max(text_w(f"{sorted(x['points'])[-1][1]:g}", 13) for x in se)
    L, R_, T, B = 14 + yl, W - 16 - vl, 40, 200
    X = lambda v: L + (R_ - L) * (v - x0) / ((x1 - x0) or 1)
    Y = lambda v: B - (B - T) * (v - y0) / ((y1 - y0) or 1)
    for t in yt:
        s.add(f'<line x1="{L}" y1="{Y(t):.1f}" x2="{R_}" y2="{Y(t):.1f}" {paint(None, "var(--line,#d9d9d9)", 0.8)}/>')
        if not schema:
            s.add(txt(L - 6, Y(t), f"{t:g}", FS_MIN, nv("note"), 500, anchor="end"))
    xt = [t for t in nice_ticks(x0, x1, 5) if x0 <= t <= x1]
    step = max(1, math.ceil(len(xt) * 40 / (R_ - L)))
    for t in ([] if schema else xt[::step]):
        s.add(txt(X(t), B + 15, f"{t:g}", FS_MIN, nv("note"), 500))
    if sp.get("axe_x"):
        s.add(txt(R_, B + 15, sp["axe_x"] + " →", FS_MIN, nv("note"), 600, anchor="end", italic=True))
    s.add(f'<line x1="{L}" y1="{B}" x2="{R_}" y2="{B}" {paint(None, nv("edge"), 1.2)}/>')
    for a in sp.get("annotations", []):
        x = X(a["x"])
        s.add(f'<line x1="{x:.1f}" y1="{T - 4}" x2="{x:.1f}" y2="{B}" {paint(None, cv("risk", "b"), 1.1, "3 3")}/>')
        hw = text_w(a.get("label", ""), FS_MIN) / 2 + 4
        s.add(txt(min(max(x, hw), W - hw), T - 14, a.get("label", ""), FS_MIN, cv("risk", "d"), 600, italic=True, halo=True))
    legend_y = B + 38
    lx = L
    ends = []
    for x in se:
        k = ck(x.get("cat"), "act")
        c = cv(k, "b")
        pts = sorted(x["points"])
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(p[0]):.1f},{Y(p[1]):.1f}" for i, p in enumerate(pts))
        s.add(f'<path d="{d}" {paint("none", c, 2.4, None, "stroke-linejoin:round;stroke-linecap:round;")}/>')
        lp = pts[-1]
        if not schema:
            for p in pts:
                s.add(f'<circle cx="{X(p[0]):.1f}" cy="{Y(p[1]):.1f}" r="2.6" {paint(c)}/>')
            s.add(f'<circle cx="{X(lp[0]):.1f}" cy="{Y(lp[1]):.1f}" r="4.5" {paint(BG, c, 2)}/>')
            ends.append([Y(lp[1]), X(lp[0]) + 9, f"{lp[1]:g}", k])
        if len(se) > 1 or x.get("nom"):
            if lx > L and lx + text_w(x.get("nom", ""), FS_MIN) + 24 > W - 4:  # légende trop longue : à la ligne
                lx, legend_y = L, legend_y + 20
            s.add(f'<line x1="{lx}" y1="{legend_y}" x2="{lx + 18}" y2="{legend_y}" {paint(None, c, 2.4, None, "stroke-linecap:round;")}/>')
            s.add(txt(lx + 24, legend_y, x.get("nom", ""), FS_MIN, nv("note"), 600, anchor="start"))
            lx += text_w(x.get("nom", ""), FS_MIN) + 44
    ends.sort()
    for i in range(1, len(ends)):  # valeurs finales : écart vertical minimal de 16 px
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 16)
    for yv, xv, lab, k in ends:
        s.add(txt(xv, yv, lab, 13, cv(k, "d"), 700, anchor="start", halo=True))
    if sp.get("unite"):
        s.add(txt(4, 12, sp["unite"], FS_MIN, nv("note"), 600, anchor="start", italic=True))
    y = legende(s, legend_y + 4, sp.get("legende"))
    return s.out(y + 10)


# ════════════════════════════════════════════════════════════════════
# 9. MATRICE 2×2 (positionnement d'acteurs)
# ════════════════════════════════════════════════════════════════════
def r_matrice(sp):
    need(sp, "points")
    s = Svg()
    L, T, S = 52, 16, W - 52 - 12
    R_, B = L + S, T + S * 0.74
    Hh = B - T
    s.add(f'<rect x="{L}" y="{T}" width="{S}" height="{Hh:.0f}" rx="6" {paint("none", nv("edge"), 1)}/>')
    s.add(f'<line x1="{L + S / 2}" y1="{T}" x2="{L + S / 2}" y2="{B}" {paint(None, nv("ghost"), 1, "4 4")}/>')
    s.add(f'<line x1="{L}" y1="{T + Hh / 2}" x2="{R_}" y2="{T + Hh / 2}" {paint(None, nv("ghost"), 1, "4 4")}/>')
    q = sp.get("quadrants", [])
    qpos = [(L + S * 0.25, T + 15), (L + S * 0.75, T + 15), (L + S * 0.25, B - 13), (L + S * 0.75, B - 13)]
    for lab, (x, y) in zip(q, qpos):
        if lab:
            s.add(txt(x, y, wrap(lab, S / 2 - 12, FS_MIN, 1), FS_MIN, nv("note"), 500, italic=True))
    xa, ya = sp.get("x", ["", ""]), sp.get("y", ["", ""])
    s.add(txt(L, B + 15, xa[0], FS_MIN, nv("note"), 500, anchor="start"))
    s.add(txt(R_, B + 15, xa[1], FS_MIN, nv("note"), 500, anchor="end"))
    if sp.get("titre_x"):
        s.add(txt(L + S / 2, B + 34, sp["titre_x"] + " →", 13, "currentColor", 700))
    s.add(f'<text transform="translate({L - 30},{T + Hh / 2}) rotate(-90)" text-anchor="middle" dominant-baseline="central" '
          f'font-size="13" font-weight="700" fill="currentColor">{esc((sp.get("titre_y") or "") + " →")}</text>')
    s.add(f'<text transform="translate({L - 12},{B - 4}) rotate(-90)" text-anchor="start" dominant-baseline="central" '
          f'font-size="{FS_MIN}" font-weight="500" {paint(nv("note"))}>{esc(ya[0])}</text>')
    s.add(f'<text transform="translate({L - 12},{T + 4}) rotate(-90)" text-anchor="end" dominant-baseline="central" '
          f'font-size="{FS_MIN}" font-weight="500" {paint(nv("note"))}>{esc(ya[1])}</text>')
    for p in sp["points"]:
        x, y = L + S * float(p["x"]), B - Hh * float(p["y"])
        k = ck(p.get("cat"), "act")
        s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" {paint(cv(k, "p"), cv(k, "b"), 2)}/>')
        right = x < L + S * 0.66
        s.add(txt(x + (12 if right else -12), y, p["label"], 13, cv(k, "d"), 650, anchor="start" if right else "end", halo=True))
        if p.get("note"):
            note_txt(s, x + (12 if right else -12), y + 16, p["note"], 130, anchor="start" if right else "end", maxlines=1)
    y = legende(s, B + (44 if sp.get("titre_x") else 26), sp.get("legende"))
    return s.out(y + 4)


# ════════════════════════════════════════════════════════════════════
# 10. RÉSEAU D'ACTEURS (alliances, rivalités, dépendances)
# ════════════════════════════════════════════════════════════════════
LIEN_STYLES = {  # type : (catégorie de couleur, pointillé, épaisseur, légende, flèche)
    "alliance":    ("pol", False, 2.6, "Alliance", False),
    "cooperation": ("env", False, 1.6, "Coopération", False),
    "dependance":  ("res", False, 1.5, "Dépendance", True),
    "rivalite":    ("instr", True, 1.6, "Rivalité", False),
    "conflit":     ("risk", True, 2.6, "Conflit", False),
    "soutien":     ("act", False, 1.6, "Soutien", True),
}


def r_reseau(sp):
    need(sp, "acteurs")
    ac = sp["acteurs"]
    if not 3 <= len(ac) <= 7:
        raise SpecError("reseau : 3 à 7 acteurs")
    s = Svg()
    cx, cy, R = W / 2, 156, 112
    pos = {}
    centre = sp.get("centre")
    ring = [a for a in ac if a.get("id") != centre]
    if centre:
        pos[centre] = (cx, cy)
    for i, a in enumerate(ring):
        ang = -math.pi / 2 + 2 * math.pi * i / len(ring)
        pos[a["id"]] = (cx + R * 1.32 * math.cos(ang), cy + R * math.sin(ang))
    sizes = {}
    for a in ac:
        lab = wrap(a["label"], 96, 13, 2)
        w_ = max(84, min(120, max(text_w(t, 13) for t in lab) + 26))
        sizes[a["id"]] = (lab, w_, 14 + len(lab) * 16.2)

    def trim(x1, y1, x2, y2, nid, pad=6):
        _, w_, h = sizes[nid]
        dx, dy = x2 - x1, y2 - y1
        t = min((w_ / 2 + pad) / abs(dx) if dx else 9e9, (h / 2 + pad) / abs(dy) if dy else 9e9)
        return x1 + dx * t, y1 + dy * t

    used = []
    for l in sp.get("liens", []):
        st = LIEN_STYLES.get(l.get("type"))
        if not st:
            raise SpecError(f'reseau : type de lien inconnu « {l.get("type")} » ({", ".join(LIEN_STYLES)})')
        if l["de"] not in pos or l["a"] not in pos:
            raise SpecError(f'reseau : lien vers un id inconnu ({l["de"]} → {l["a"]})')
        (x1, y1), (x2, y2) = pos[l["de"]], pos[l["a"]]
        ax1, ay1 = trim(x1, y1, x2, y2, l["de"])
        ax2, ay2 = trim(x2, y2, x1, y1, l["a"])
        k, dash, w_, _, arrow = st
        link(s, ax1, ay1, ax2, ay2, cv(k, "b"), dashed=dash, width=w_, arrow=arrow)
        if l.get("label"):
            mx, my = (ax1 + ax2) / 2, (ay1 + ay2) / 2
            ln = math.hypot(ax2 - ax1, ay2 - ay1) or 1
            if ln < text_w(l["label"], FS_MIN) + 20:  # lien court : étiquette décalée perpendiculairement
                nx_, ny_ = -(ay2 - ay1) / ln, (ax2 - ax1) / ln
                if ny_ > 0:
                    nx_, ny_ = -nx_, -ny_
                mx, my = mx + nx_ * 14, my + ny_ * 14
            ann(s, mx, my, l["label"], k)
        if l["type"] not in used:
            used.append(l["type"])
    for a in ac:
        x, y = pos[a["id"]]
        k = ck(a.get("cat"), "act")
        lab, w_, h = sizes[a["id"]]
        big = a.get("id") == centre
        s.add(f'<rect x="{x - w_ / 2:.1f}" y="{y - h / 2:.1f}" width="{w_:.1f}" height="{h:.1f}" rx="{min(h / 2, 14):.1f}" '
              f'{paint(cv(k, "p"), cv(k, "b"), 2.4 if big else 1.3)}/>')
        s.add(txt(x, y, lab, 13, cv(k, "d"), 700))
        if a.get("note"):
            note_txt(s, x, y + h / 2 + 11, a["note"], 130, anchor="middle", maxlines=1)
    ly, lx = cy + R + 46, 12
    for t in used:
        k, dash, w_, lab, arrow = LIEN_STYLES[t]
        lab = lab + (" →" if arrow else "")
        wl = text_w(lab, FS_MIN) + 52
        if lx + wl > W:
            lx, ly = 12, ly + 20
        s.add(f'<line x1="{lx}" y1="{ly}" x2="{lx + 24}" y2="{ly}" {paint(None, cv(k, "b"), min(w_, 2.2), "5 3" if dash else None)}/>')
        s.add(txt(lx + 30, ly, lab, FS_MIN, nv("note"), 500, anchor="start"))
        lx += wl
    y = legende(s, ly + 4, sp.get("legende"))
    return s.out(y + 8)


# ════════════════════════════════════════════════════════════════════
# 11. BALANCE (rapport de force, arguments pour / contre)
# ════════════════════════════════════════════════════════════════════
def r_balance(sp):
    need(sp, "gauche", "droite")
    s = Svg()
    tilt = {"gauche": 1, "droite": -1}.get(sp.get("penche"), 0) * 7
    cx = W / 2
    top = 12
    if sp.get("pivot"):
        pl = wrap(sp["pivot"], W - 20, 14, 2)
        s.add(txt(cx, top + len(pl) * 8.75, pl, 14, "currentColor", 700))
        top += len(pl) * 17.5 + 8
    py_ = top + 30
    ang = math.radians(tilt)
    L = 108
    lx, ly = cx - L * math.cos(ang), py_ + L * math.sin(ang)
    rx, ry = cx + L * math.cos(ang), py_ - L * math.sin(ang)
    s.add(f'<path d="M{cx - 24},{py_ + 150} L{cx + 24},{py_ + 150} L{cx},{py_ + 5} z" {paint("var(--line,#d9d9d9)")}/>')
    s.add(f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{rx:.1f}" y2="{ry:.1f}" {paint(None, nv("edge"), 3, None, "stroke-linecap:round;")}/>')
    s.add(f'<circle cx="{cx}" cy="{py_}" r="5.5" {paint(BG, nv("edge"), 2)}/>')
    ymax = 0
    for side, (x, y) in (("gauche", (lx, ly)), ("droite", (rx, ry))):
        d = sp[side]
        k = ck(d.get("cat"), "act")
        items = d.get("items", [])[:4]
        lines = [wrap("• " + it, 178, 12.5, 3) for it in items]
        title = wrap(d.get("titre", ""), 178, 13.5, 2)
        h = 12 + len(title) * 17 + 8 + sum(len(l) * 15.6 for l in lines) + 8
        s.add(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y + 22:.1f}" {paint(None, nv("edge"), 1)}/>')
        top_b = y + 22
        s.add(f'<rect x="{x - 97:.1f}" y="{top_b:.1f}" width="194" height="{h:.1f}" rx="8" {paint(cv(k, "p"), cv(k, "b"), 1.3)}/>')
        s.add(txt(x, top_b + 10 + len(title) * 8.5, title, 13.5, cv(k, "d"), 750))
        s.add(f'<line x1="{x - 80:.1f}" y1="{top_b + 14 + len(title) * 17:.1f}" x2="{x + 80:.1f}" y2="{top_b + 14 + len(title) * 17:.1f}" '
              f'{paint(None, cv(k, "b"), 0.8)} opacity="0.5"/>')
        yy = top_b + 12 + len(title) * 17 + 8
        for l in lines:
            s.add(txt(x - 88, yy + len(l) * 7.8, l, 12.5, cv(k, "d"), 500, anchor="start"))
            yy += len(l) * 15.6
        ymax = max(ymax, top_b + h)
    y = legende(s, ymax + 4, sp.get("legende"))
    return s.out(y + 10)


# ════════════════════════════════════════════════════════════════════
# 15. ARBRE (décomposition hiérarchique descendante)
# ════════════════════════════════════════════════════════════════════
def r_arbre(sp):
    need(sp, "racine")
    niv = sp.get("niveaux") or []
    gut = min(96, max(text_w(t, FS_MIN) for t in niv) + 18) if niv else 6
    root = json.loads(json.dumps(sp["racine"]))  # copie : on annote les nœuds sans toucher à la spec

    def walk(n, d, parent_cat):
        n["_d"], n["_k"] = d, ck(n.get("cat") or parent_cat, "pol")
        kids = n.get("enfants") or []
        if d > 3 or (d == 3 and kids):
            raise SpecError("arbre : 4 niveaux au plus (racine + 3)")
        for c in kids:
            walk(c, d + 1, n["_k"])
    walk(root, 0, None)

    leaves = []
    def collect(n):
        kids = n.get("enfants") or []
        if not kids:
            leaves.append(n)
        for c in kids:
            collect(c)
    collect(root)
    nl, gap = len(leaves), 8
    avail = W - gut - 6
    lw = min(170, (avail - (nl - 1) * gap) / nl)
    sens = sp.get("sens", "auto")
    if sens not in ("auto", "bas", "droite"):
        raise SpecError("arbre : sens = auto, bas ou droite")
    if sens == "droite" or (sens == "auto" and lw < 88):
        return _arbre_droite(sp, root, niv, leaves)
    if lw < 62:
        raise SpecError(f"arbre : {nl} feuilles, trop pour un arbre vers le bas (utilise \"sens\": \"droite\")")
    for i, lf in enumerate(leaves):
        lf["_x"] = gut + lw / 2 + i * (lw + gap)
        lf["_w"] = lw

    def place(n):
        kids = n.get("enfants") or []
        if kids:
            for c in kids:
                place(c)
            n["_x"] = (kids[0]["_x"] + kids[-1]["_x"]) / 2
            span = kids[-1]["_x"] - kids[0]["_x"] + lw
            n["_w"] = max(lw, min(230, span))
    place(root)

    levels = {}
    def bylevel(n):
        levels.setdefault(n["_d"], []).append(n)
        for c in n.get("enfants") or []:
            bylevel(c)
    bylevel(root)
    fs = 13 if lw >= 90 else FS_MIN
    rowh, noteh = {}, {}
    for d, ns in levels.items():
        for n in ns:
            n["_h"] = node_h(n.get("label"), n.get("sous"), n["_w"], fs if d else 13.5)[2]
            n["_nl"] = len(wrap(n["note"], n["_w"] - 4, FS_MIN, 2)) if n.get("note") else 0
        rowh[d] = max(n["_h"] for n in ns)
        for n in ns:  # toutes les boîtes d'une rangée ont la même hauteur
            n["_h"] = rowh[d]
        noteh[d] = max(n["_nl"] for n in ns) * 15.6 + (4 if any(n["_nl"] for n in ns) else 0)
    y, ytop = 14, {}
    for d in sorted(levels):
        ytop[d] = y
        y += rowh[d] + noteh[d] + (46 if d + 1 in levels and any(c.get("verbe") for c in levels[d + 1]) else 34)
    s = Svg()
    # annotations de niveau à gauche (« Divide », « Merge »…)
    for d in sorted(levels):
        if d < len(niv) and niv[d]:
            cy = ytop[d] + rowh[d] / 2
            s.add(f'<line x1="{gut - 8}" y1="{cy - 10:.1f}" x2="{gut - 8}" y2="{cy + 10:.1f}" {paint(None, nv("ghost"), 1)}/>')
            note_txt(s, gut - 14, cy, niv[d], gut - 12, anchor="end", maxlines=2)
    # liaisons (sous les boîtes)
    def edges(n):
        for c in n.get("enfants") or []:
            y1 = ytop[n["_d"]] + (rowh[n["_d"]] + n["_h"]) / 2
            y2 = ytop[c["_d"]] + (rowh[c["_d"]] - c["_h"]) / 2
            if n["_nl"]:
                y1 = ytop[n["_d"]] + rowh[n["_d"]] + noteh[n["_d"]] - 2
            x1 = n["_x"] + (c["_x"] - n["_x"]) * 0.18
            s.add(f'<path d="M{x1:.1f},{y1 + 1:.1f} L{c["_x"]:.1f},{y2 - 1:.1f}" {paint("none", cv(c["_k"], "b"), 1.3)} opacity="0.75"/>')
            if c.get("verbe"):
                mx, my = (x1 + c["_x"]) / 2, (y1 + y2) / 2
                right = c["_x"] >= n["_x"]
                ann(s, mx + (6 if right else -6), my, c["verbe"], c["_k"], anchor="start" if right else "end")
            edges(c)
    edges(root)
    for d, ns in levels.items():
        for n in ns:
            cy = ytop[d] + rowh[d] / 2
            node(s, n["_x"], cy, n["_w"], n.get("label"), n.get("sous"), n["_k"], fs=fs if d else 13.5,
                 strong=d == 0, badge_=n.get("num"), hmin=rowh[d])
            if n.get("note"):
                note_txt(s, n["_x"], ytop[d] + rowh[d] + 10 + (n["_nl"] - 1) * 7.8, n["note"], n["_w"] - 4, anchor="middle", maxlines=2)
    y = legende(s, y - 24, sp.get("legende"))
    return s.out(y + 10)


def _arbre_droite(sp, root, niv, leaves):
    """Arbre couché (racine à gauche, feuilles empilées à droite) : pour les arbres larges."""
    if len(leaves) > 9:
        raise SpecError(f"arbre : {len(leaves)} feuilles (9 au plus)")
    depth = 1 + max(lf["_d"] for lf in leaves)
    gx = 22
    cw = (W - 8 - (depth - 1) * gx) / depth
    fs = 13 if cw >= 110 else FS_MIN
    colx = [4 + cw / 2 + d * (cw + gx) for d in range(depth)]
    top = 34 if niv else 10
    s = Svg()
    for d in range(min(depth, len(niv))):
        if niv[d]:
            s.add(txt(colx[d], 14, wrap(niv[d], cw, FS_MIN, 1), FS_MIN, nv("note"), 500, italic=True))
            s.add(f'<line x1="{colx[d] - cw / 2 + 8:.1f}" y1="24" x2="{colx[d] + cw / 2 - 8:.1f}" y2="24" {paint(None, nv("ghost"), 1)}/>')

    def size(n):
        n["_w"] = cw
        n["_h"] = node_h(n.get("label"), n.get("sous"), cw, fs if n["_d"] else 13.5)[2]
        n["_vb"] = 16 if n.get("verbe") else 0
        n["_nh"] = len(wrap(n["note"], cw - 4, FS_MIN, 2)) * 15.6 + 2 if n.get("note") else 0
        for c in n.get("enfants") or []:
            size(c)
    size(root)
    y = [top]

    def place(n):
        kids = n.get("enfants") or []
        if not kids:
            y[0] += n["_vb"]
            n["_y"] = y[0] + n["_h"] / 2
            y[0] += n["_h"] + n["_nh"] + 10
            return
        for c in kids:
            place(c)
        n["_y"] = (kids[0]["_y"] + kids[-1]["_y"]) / 2
    place(root)

    def edges(n):
        for c in n.get("enfants") or []:
            x1, x2 = colx[n["_d"]] + cw / 2, colx[c["_d"]] - cw / 2
            dx = (x2 - x1) * 0.55
            s.add(f'<path d="M{x1:.1f},{n["_y"]:.1f} C{x1 + dx:.1f},{n["_y"]:.1f} {x2 - dx:.1f},{c["_y"]:.1f} {x2:.1f},{c["_y"]:.1f}" '
                  f'{paint("none", cv(c["_k"], "b"), 1.3)} opacity="0.8"/>')
            edges(c)
    edges(root)

    def boxes(n):
        x = colx[n["_d"]]
        node(s, x, n["_y"], cw, n.get("label"), n.get("sous"), n["_k"], fs=fs if n["_d"] else 13.5,
             strong=n["_d"] == 0, badge_=n.get("num"))
        if n.get("verbe"):
            ann(s, x - cw / 2 + 4, n["_y"] - n["_h"] / 2 - 9, n["verbe"], n["_k"], anchor="start")
        if n.get("note"):
            nl_ = len(wrap(n["note"], cw - 4, FS_MIN, 2))
            note_txt(s, x, n["_y"] + n["_h"] / 2 + 10 + (nl_ - 1) * 7.8, n["note"], cw - 4, anchor="middle", maxlines=2)
        for c in n.get("enfants") or []:
            boxes(c)
    boxes(root)
    yy = max(y[0], root["_y"] + root["_h"] / 2 + root["_nh"] + 10)
    yy = legende(s, yy - 6, sp.get("legende"))
    return s.out(yy + 8)


# ════════════════════════════════════════════════════════════════════
# 16. AVANT / APRÈS (deux états côte à côte, changements mis en évidence)
# ════════════════════════════════════════════════════════════════════
ETATS = {  # état : (catégorie de couleur, signe de la pastille, libellé de légende)
    "nouveau": ("env", "+", "apparaît"),
    "retire": ("risk", "−", "disparaît"),
    "modifie": ("instr", "Δ", "change"),
}


def r_avant_apres(sp):
    need(sp, "avant", "apres")
    av, ap = sp["avant"], sp["apres"]
    ia, ib = av.get("items") or [], ap.get("items") or []
    if not ia and not ib:
        raise SpecError("avant_apres : au moins un élément")
    if max(len(ia), len(ib)) > 7:
        raise SpecError("avant_apres : 7 éléments au plus par colonne")
    key = lambda it: str(it.get("id") or it.get("label", "")).strip().lower()
    # lignes alignées : un même élément (même label ou même id) des deux côtés est sur la même ligne
    rows, seen = [], {}
    for it in ia:
        seen[key(it)] = len(rows)
        rows.append([it, None])
    for it in ib:
        if key(it) in seen and rows[seen[key(it)]][1] is None:
            rows[seen[key(it)]][1] = it
        else:
            rows.append([None, it])
    cw, gx = 176, 12
    xl, xr = gx + cw / 2, W - gx - cw / 2
    s = Svg()
    y = 12
    if sp.get("evenement"):
        el = wrap(sp["evenement"], W - 120, 13, 2)
        s.add(txt(W / 2, y + len(el) * 8.1, el, 13, cv("date", "d"), 650, italic=True))
        y += len(el) * 16.2 + 8
    hy = y + 10
    for x, t in ((xl, av.get("titre", "Avant")), (xr, ap.get("titre", "Après"))):
        s.add(txt(x, hy, t, 14, "currentColor", 750))
    s.add(f'<line x1="{gx}" y1="{hy + 14}" x2="{gx + cw}" y2="{hy + 14}" {paint(None, nv("edge"), 1)}/>')
    s.add(f'<line x1="{W - gx - cw}" y1="{hy + 14}" x2="{W - gx}" y2="{hy + 14}" {paint(None, nv("edge"), 1)}/>')
    link(s, W / 2 - 22, hy, W / 2 + 22, hy, nv("edge"), width=1.6)
    y = hy + 28
    used = set()

    def val_of(it):
        return str(it.get("valeur", "")) if it else ""

    def draw(it, x, etat, ghost=False):
        if ghost:
            s.add(f'<rect x="{x - cw / 2 + 10:.1f}" y="{y + 3:.1f}" width="{cw - 20}" height="{rh - 6:.1f}" rx="7" {paint("none", nv("ghost"), 1, "3 4")}/>')
            return
        k = ck(it.get("cat"), "act")
        v = val_of(it)
        vw = text_w(v, 13) + 12 if v else 0
        lab = wrap(it.get("label"), cw - 24 - vw, 13, 2)
        strong = etat in ("nouveau", "modifie")
        faded = etat == "retire"
        bk = ETATS[etat][0] if etat else k
        s.add(f'<rect x="{x - cw / 2:.1f}" y="{y:.1f}" width="{cw}" height="{rh:.1f}" rx="8" '
              f'{paint(cv(k, "p"), cv(bk if etat else k, "b"), 2.2 if strong else 1.3, "5 3" if faded else None)}'
              + (' opacity="0.72"' if faded else "") + "/>")
        tx = x - cw / 2 + 12
        s.add(txt(tx, y + rh / 2, lab, 13, cv(k, "d"), 650, anchor="start", opacity=0.75 if faded else None))
        if faded:
            for i, l in enumerate(lab):
                ly = y + rh / 2 + (i - (len(lab) - 1) / 2) * 16.25
                s.add(f'<line x1="{tx:.1f}" y1="{ly:.1f}" x2="{tx + text_w(l, 13):.1f}" y2="{ly:.1f}" {paint(None, cv("risk", "b"), 1.4)}/>')
        if v:
            s.add(txt(x + cw / 2 - 10, y + rh / 2, v, 13, cv(bk if etat == "modifie" else k, "d"), 800, anchor="end"))
        if etat:
            ek = ETATS[etat][0]
            s.add(f'<circle cx="{x + cw / 2 - 1:.1f}" cy="{y + 1:.1f}" r="9" {paint(cv(ek, "b"), BG, 1.6)}/>')
            s.add(txt(x + cw / 2 - 1, y + 1.5, ETATS[etat][1], 13, BG, 800))
            used.add(etat)

    for a, b in rows:
        la = [len(wrap(t.get("label"), cw - 24 - (text_w(val_of(t), 13) + 12 if val_of(t) else 0), 13, 2)) for t in (a, b) if t]
        rh = 12 + max(la) * 16.25
        ea = (a.get("etat") if a else None) or ("retire" if a and not b else None)
        eb = (b.get("etat") if b else None) or ("nouveau" if b and not a else None)
        if a and b and not eb and val_of(a) != val_of(b):
            eb = "modifie"
        for e in (ea, eb):
            if e and e not in ETATS:
                raise SpecError(f'avant_apres : état inconnu « {e} » ({", ".join(ETATS)})')
        draw(a, xl, ea, ghost=a is None)
        draw(b, xr, eb, ghost=b is None)
        if a and b:
            s.add(f'<line x1="{xl + cw / 2 + 4}" y1="{y + rh / 2:.1f}" x2="{xr - cw / 2 - 4}" y2="{y + rh / 2:.1f}" '
                  f'{paint(None, nv("ghost"), 1, "2 3")}/>')
        y += rh
        nts = [(t, x) for t, x in ((a, xl), (b, xr)) if t and t.get("note")]
        nh = 0
        for t, x in nts:
            nh = max(nh, note_txt(s, x - cw / 2 + 12, y + 10, t["note"], cw - 16, maxlines=2)[1])
        y += nh + (6 if nh else 0) + 8
    for x, side in ((xl, av), (xr, ap)):
        if side.get("note"):
            note_txt(s, x, y + 8, side["note"], cw, anchor="middle", maxlines=2)
    if av.get("note") or ap.get("note"):
        y += 36
    leg = [{"badge": ETATS[e][1], "cat": ETATS[e][0], "label": ETATS[e][2]} for e in ETATS if e in used]
    y = legende(s, y, leg + list(sp.get("legende") or []))
    return s.out(y + 8)


# ════════════════════════════════════════════════════════════════════
# 12. CARTE (fond Natural Earth réel + marqueurs lon/lat)
# ════════════════════════════════════════════════════════════════════
def r_carte(sp):
    need(sp, "fond")
    rid = sp["fond"]
    if rid not in REGIONS:
        raise SpecError(f'carte : fond inconnu « {rid} » (disponibles : {", ".join(REGIONS)})')
    lon0, lon1, lat0, lat1, Wm, Hm = REGIONS[rid]

    def P(lon, lat):
        if not (lon0 <= lon <= lon1 and lat0 <= lat <= lat1):
            raise SpecError(f"carte « {rid} » : point hors cadre ({lon}, {lat}) — bbox lon {lon0}→{lon1}, lat {lat0}→{lat1}")
        return (lon - lon0) / (lon1 - lon0) * Wm, (lat1 - lat) / (lat1 - lat0) * Hm

    s = Svg(Wm, arrow=round(11 * max(1.0, Wm / 370), 1))
    # Les fonds font 312→680 unités de large mais s'affichent sur ~370 px (mobile) à ~520 px (ordinateur) :
    # on grossit marqueurs et étiquettes en proportion pour garder des textes lisibles (≈ 10,5-11 px réels sur un téléphone de 390-400 px).
    k = max(1.0, Wm / 370)
    legend = []
    for z in sp.get("zones", []):
        x, y = P(z["lon"], z["lat"])
        c = col(z.get("cat") or "risk")[1]
        r = z.get("rayon", 26)
        s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}" fill-opacity="0.22" stroke="{c}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    for f in sp.get("fleches", []):
        c = shade(col(f.get("cat") or "res")[1], 0.05)
        if f.get("trajet"):  # itinéraire par points de passage (ex. contourner une péninsule)
            pts = [P(*q) for q in f["trajet"]]
            if len(pts) < 2:
                raise SpecError("carte : un trajet demande au moins 2 points")
            ext = [pts[0]] + pts + [pts[-1]]
            d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
            for i in range(1, len(ext) - 2):
                p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
                c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
                c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
                d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
            mid = s.arrow_id(c)
            dash = ' stroke-dasharray="7 5"' if f.get("style") == "menace" else ""
            s.add(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round"{dash} marker-end="url(#{mid})"/>')
            if f.get("label"):
                m = pts[max(1, len(pts) // 3)] if len(pts) > 2 else ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
                pill(s, m[0], m[1] - 14 * k, f["label"], f.get("cat") or "res", fs=11 * k)
            continue
        (x1, y1), (x2, y2) = P(*f["de"]), P(*f["a"])
        link(s, x1, y1, x2, y2, c, dashed=f.get("style") == "menace", width=3, curve=f.get("courbe", 0.15))
        if f.get("label"):
            mx, my = (x1 + x2) / 2 - (y2 - y1) * f.get("courbe", 0.15) / 2, (y1 + y2) / 2 + (x2 - x1) * f.get("courbe", 0.15) / 2
            pill(s, mx, my - 12 * k, f["label"], f.get("cat") or "res", fs=11 * k)
    for i, p in enumerate(sp.get("points", [])):
        x, y = P(p["lon"], p["lat"])
        _, bg, fg, _, _ = col(p.get("cat") or "risk")
        num = BADGES[i] if i < len(BADGES) else str(i + 1)
        s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{11 * k:.1f}" fill="{bg}" stroke="#fff" stroke-width="2"/>')
        s.add(txt(x, y + 0.5, num, round(12 * k, 1), fg, 800))
        if p.get("label"):
            legend.append((num, bg, p["label"]))
    overlay = s.out(Hm)
    leg = "".join(
        f'<div style="margin:3px 0;font-size:14px;"><span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:{c};color:#fff;'
        f'text-align:center;line-height:20px;font-size:12px;font-weight:700;margin-right:6px;">{n}</span>{esc(l)}</div>'
        for n, c, l in legend
    )
    return (f'<div class="geo" style="position:relative;--ar:{W / Hm:.3f};">'
            f'<img src="_geo_{rid}{"_muet" if sp.get("muette") else ""}.svg" style="width:100%;display:block;border-radius:6px;">'
            f'<div style="position:absolute;inset:0;">{overlay}</div></div>'
            + (f'<div class="geo-leg" style="margin-top:6px;">{leg}</div>' if leg and not sp.get("muette") else ""))


# ════════════════════════════════════════════════════════════════════
# 13. CHIFFRE-CHOC (1 à 3 grands nombres)
# ════════════════════════════════════════════════════════════════════
def r_chiffre(sp):
    items = sp.get("chiffres") or [sp]
    need(items[0], "valeur")
    cells = []
    for it in items[:3]:
        c = col(it.get("cat") or "act")[3]
        cells.append(
            f'<div style="flex:1;min-width:120px;text-align:center;padding:8px 6px;">'
            f'<div class="k {it.get("cat") or "act"}" style="font-size:38px;font-weight:800;line-height:1.1;letter-spacing:-.02em;">{esc(it["valeur"])}</div>'
            f'<div style="font-size:14px;margin-top:4px;line-height:1.35;">{esc(it.get("legende", ""))}</div>'
            + (f'<div style="font-size:12px;opacity:.7;margin-top:2px;">{esc(it["comparaison"])}</div>' if it.get("comparaison") else "")
            + "</div>")
    return f'<div class="stat" style="display:flex;flex-wrap:wrap;gap:6px;justify-content:center;">{"".join(cells)}</div>'


# ════════════════════════════════════════════════════════════════════
# 14. TABLEAU COMPARATIF (2-3 acteurs × 2-5 critères)
# ════════════════════════════════════════════════════════════════════
def r_tableau(sp):
    need(sp, "colonnes", "lignes")
    cols = sp["colonnes"]
    cats = sp.get("cats", [None] * len(cols))
    th = "".join(
        f'<th style="padding:6px 8px;text-align:left;font-size:14px;'
        + (f'background:{col(c)[1]};color:{col(c)[2]};' if c else "")
        + f'">{esc(h)}</th>'
        for h, c in zip(cols, cats + [None] * (len(cols) - len(cats)))
    )
    rows = "".join(
        "<tr>" + "".join(
            f'<td style="padding:6px 8px;font-size:14.5px;border-top:1px solid var(--line,#ccc);'
            + ("font-weight:700;" if i == 0 else "") + f'">{esc(v)}</td>'
            for i, v in enumerate(r)) + "</tr>"
        for r in sp["lignes"]
    )
    return f'<table class="cmp" style="border-collapse:collapse;width:100%;"><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table>'


RENDERERS = {
    "chaine": r_chaine, "bifurcation": r_bifurcation, "boucle": r_boucle, "frise": r_frise,
    "periodes": r_periodes, "barres": r_barres, "jauge": r_jauge, "courbe": r_courbe,
    "matrice": r_matrice, "reseau": r_reseau, "balance": r_balance, "carte": r_carte,
    "chiffre": r_chiffre, "tableau": r_tableau, "arbre": r_arbre, "avant_apres": r_avant_apres,
}

# Format des specs (les champs entre crochets sont optionnels). Partout : "cat" = code de catégorie de PALETTE ;
# "[note]" = petite annotation en italique ; "[legende]" = liste de {"cat","label"} ou de textes, affichée
# discrètement sous le schéma.
SPEC_DOC = {
    "chaine": '{"type":"chaine","noeuds":[{"label","[sous]","cat","[note]"} ×2-5],'
              '"liens":[{"verbe","cat","[paradoxal]","[note]"}],"[legende]"} — dernier nœud = enjeu terminal ⚑ ; '
              'la note d\'un nœud s\'affiche à sa droite, celle d\'un lien sous le verbe',
    "bifurcation": '{"type":"bifurcation","source":{"label","[sous]","cat","[note]"},'
                   '"branches":[{"label","cat","verbe","[paradoxal]","[note]"} ×2],"terminal":{"label","[sous]","[note]"},"[legende]"}',
    "boucle": '{"type":"boucle","[centre]":"Dilemme de sécurité","noeuds":[{"label","[sous]","cat"} ×3-5],'
              '"liens":[{"verbe","cat"} × autant],"[legende]"}',
    "frise": '{"type":"frise","jalons":[{"date","label","cat"} ×2-7],"[legende]"} — dernier jalon = aboutissement ⚑',
    "periodes": '{"type":"periodes","debut","fin","bandes":[{"de","a","label","cat","[ligne]"}],"[reperes]":[{"annee","label"}],"[legende]"}',
    "barres": '{"type":"barres","unite","barres":[{"label","valeur","cat","[affiche]"} ×2-6],"[note]":"source, année","[legende]"}',
    "jauge": '{"type":"jauge","jauges":[{"pct","label","cat","[note]"} ×1-3],"[legende]"}',
    "courbe": '{"type":"courbe","unite","series":[{"nom","cat","points":[[x,y],…]} ×1-3],"[annotations]":[{"x","label"}],"[zero]":true,"[schema]":true,"[axe_x]","[legende]"} — "schema" : courbe théorique sans valeurs chiffrées (U inversé, offre/demande…) ; "axe_x" nomme l’axe horizontal',
    "matrice": '{"type":"matrice","titre_x","titre_y","x":["faible","fort"],"y":[…],"[quadrants]":[HG,HD,BG,BD],'
               '"points":[{"label","x":0-1,"y":0-1,"cat","[note]"}],"[legende]"}',
    "reseau": '{"type":"reseau","[centre]":"id","acteurs":[{"id","label","cat","[note]"} ×3-7],'
              '"liens":[{"de","a","type":"alliance|cooperation|rivalite|conflit|dependance|soutien","[label]"}],"[legende]"}',
    "balance": '{"type":"balance","pivot","penche":"gauche|droite|equilibre","gauche":{"titre","cat","items":[≤4]},"droite":{…},"[legende]"}',
    "carte": '{"type":"carte","fond":"ID","points":[{"lon","lat","label","cat"}],"[fleches]":[{"trajet":[[lon,lat],…] ou "de"/"a",'
             '"cat","label","[style]":"menace"}],"[zones]":[{"lon","lat","cat","[rayon]"}],"[muette]":true}',
    "chiffre": '{"type":"chiffre","chiffres":[{"valeur","legende","cat","[comparaison]"} ×1-3]}',
    "tableau": '{"type":"tableau","colonnes":[…],"cats":[null,"act",…],"lignes":[[…],…]}',
    "arbre": '{"type":"arbre","racine":{"label","[sous]","[cat]","[note]","[num]","[enfants]":[{"label","[cat]","[verbe]",'
             '"[note]","[enfants]":[…]}]},"[niveaux]":["Conflit","Causes","Facteurs"],"[sens]":"auto|bas|droite","[legende]"} '
             '— 4 niveaux et 9 feuilles au plus ; en « auto », l\'arbre descend (≤ 3-4 feuilles) ou se couche vers la '
             'droite (plus de feuilles) ; "cat" est hérité du parent ; "verbe" s\'écrit sur la branche qui mène au nœud ; "niveaux" = '
             'annotations en italique à gauche de chaque rangée',
    "avant_apres": '{"type":"avant_apres","[evenement]":"Traité…","avant":{"titre","items":[{"label","[cat]","[valeur]",'
                   '"[etat]","[note]","[id]"} ≤7],"[note]"},"apres":{…},"[legende]"} — un élément présent des deux côtés '
                   '(même label ou même id) est aligné sur la même ligne ; absent après → « disparaît » (barré), '
                   'absent avant → « apparaît » (+), valeur différente → « change » (Δ) ; "etat" '
                   '(nouveau|retire|modifie) force le marquage',
}


def render(spec):
    """Spec (dict ou chaîne JSON) → HTML/SVG. Une chaîne commençant par '<' est renvoyée telle quelle."""
    if not spec:
        return ""
    if isinstance(spec, str):
        if spec.lstrip().startswith("<"):
            return spec
        spec = json.loads(spec)
    t = spec.get("type")
    if t not in RENDERERS:
        raise SpecError(f'type de visuel inconnu « {t} » (disponibles : {", ".join(RENDERERS)})')
    out = RENDERERS[t](spec)
    style = ""
    if t == "carte":  # largeur d'affichage selon le format du fond : hauteur ≈ 400 px max, entre 380 et 620 px de large
        _, _, _, _, Wm, Hm = REGIONS[spec["fond"]]
        style = f' style="--vz-max:{round(min(620, max(380, Wm * 400 / Hm)))}px"'
    return f'<div class="vz vz-{FAMILLES.get(t, "diagramme")} vz-{t}"{style}>{out}</div>'


# Famille de chaque visuel → largeur maximale d'affichage (règles .vz-<famille> dans build_css() du builder).
FAMILLES = {
    "chaine": "diagramme", "bifurcation": "diagramme", "boucle": "diagramme", "reseau": "diagramme",
    "balance": "diagramme", "matrice": "diagramme",
    "frise": "graphique", "periodes": "graphique", "barres": "graphique", "jauge": "graphique", "courbe": "graphique",
    "carte": "carte", "chiffre": "bloc", "tableau": "bloc", "arbre": "diagramme", "avant_apres": "diagramme",
}


def uses_geo(spec):
    return isinstance(spec, dict) and spec.get("type") == "carte"

#!/usr/bin/env python3
"""
mindmap.py — type de note « carte mentale à rappel actif » pour Ficher.

Conception (pourquoi) :
  Une carte mentale affichée au verso ne teste presque rien : on la regarde, on la reconnaît,
  on clique « Bien ». Ici une même note génère plusieurs cartes qui obligent à RAPPELER :
    • « Structure »      recto : titre central + N branches MASQUÉES (couleur de catégorie visible)
                         → retrouver les grands axes.  Verso : carte complète + synthèse (Reponse).
    • « Branche 1…6 »    recto : la carte, les autres branches repliées (contexte spatial),
                         la branche k montrée avec TOUS ses nœuds masqués (on voit combien il y en a
                         et à quel niveau) → retrouver le contenu ; on peut révéler nœud par nœud.
                         Verso : branche k dévoilée et mise en avant, les autres atténuées.
  Une carte par branche n'existe que si le champ B<k> est rempli : le builder le remplit
  automatiquement (branch_flags) avec le libellé de la branche quand elle a au moins un enfant.

Disposition : HTML (pas de SVG mis à l'échelle) → le texte garde sa taille réelle (13–17 px).
  • largeur ≥ 700 px : carte bilatérale (branches à droite puis à gauche du titre, liens courbes) ;
  • en dessous : arbre vertical (titre en haut, branches empilées, colonne vertébrale) :
    aucun défilement horizontal sur téléphone.
Couleurs : la couleur d'une branche = sa catégorie (emoji 🔴🟣🔵🌸🌿📅👤🟡📘🔘🟠🟤🔮),
  mêmes teintes que le code couleur des cartes (PALETTE de visuels) ; clair et sombre.
Robustesse : tout inline, aucun réseau ; le script traite chaque conteneur .mm non initialisé
  (data-mm) : Anki peut le réexécuter sans dupliquer ; aucune variable globale sauf un
  écouteur de redimensionnement unique.

Exports : MINDMAP_FIELDS, MINDMAP_TEMPLATES, MINDMAP_CSS, MINDMAP_JS, MAX_BRANCHES,
          MINDMAP_EMOJI, parse(md), branch_flags(md), validate(md) -> list[str].
Usage CLI : python3 mindmap.py fichier.md   → affiche les avertissements et les champs B1…B6.
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from visuels import PALETTE  # noqa: E402  (lecture seule : source unique des couleurs)

MAX_BRANCHES = 6
MINDMAP_EMOJI = {
    "🔴": "risk", "🟣": "eco", "🔵": "pol", "🌸": "soc", "🌿": "env", "📅": "date", "👤": "act",
    "🟡": "enj", "📘": "conc", "🔘": "inst", "🟠": "instr", "🟤": "res", "🔮": "prosp",
}
MINDMAP_FIELDS = ["Question", "Mindmap", "Reponse", "SourceURL", "SourceTitre"] + \
                 [f"B{k}" for k in range(1, MAX_BRANCHES + 1)] + ["Medias"]
# V11 « Medias » : images des nœuds (portraits) et des branches (image importée ou schéma SVG), au format
# <img hidden> (pour qu'Anki voie les fichiers utilisés) + <span class="mm-json">JSON échappé</span> :
#   {"noeuds": {"Kissinger": "fichier.jpg"}, "branches": {"Ressources": {"img": "f.png"} | {"svg": "<svg…>"}}}


# ════════════════════════════════════════════════════════════════════
# PARSEUR PYTHON (miroir du parseur JS) — sert à validate() et branch_flags()
# ════════════════════════════════════════════════════════════════════
def _clean(raw: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", raw or "", flags=re.I)
    s = re.sub(r"</?(div|p)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).replace("\r", "").replace("\u00a0", " ")


def _split_emoji(label: str):
    t = label.strip()
    for e, cat in MINDMAP_EMOJI.items():
        if t.startswith(e):
            return cat, t[len(e):].lstrip("\ufe0f").strip()
    return None, t


def parse(md: str) -> dict:
    """Arbre {label, cat, depth, children, line}. Profondeur : # = 0, ## = 1, - = 2, -- = 3, --- = 4."""
    root = {"label": "", "cat": None, "depth": 0, "children": [], "line": ""}
    stack = [root]
    for line in _clean(md).split("\n"):
        t = line.strip()
        if not t:
            continue
        if re.match(r"^#\s", t):
            root["label"] = t[1:].strip()
            continue
        if re.match(r"^##\s", t):
            depth, label = 1, t[2:].strip()
        else:
            m = re.match(r"^(-+)\s+(.*)$", t)
            if not m:
                continue
            depth, label = len(m.group(1)) + 1, m.group(2)
        cat, label = _split_emoji(label)
        while len(stack) < depth:
            stack.append(stack[-1])
        parent = stack[depth - 1] if depth - 1 < len(stack) else root
        node = {"label": label, "cat": cat, "depth": depth, "children": [], "line": t}
        parent["children"].append(node)
        del stack[depth:]
        stack.append(node)
    return root


def _count(n):
    return sum(1 + _count(c) for c in n["children"])


def branch_flags(md: str) -> list:
    """Valeurs des champs B1…B6 : libellé de la branche si elle a au moins un enfant, sinon ''."""
    br = parse(md)["children"]
    out = []
    for k in range(MAX_BRANCHES):
        b = br[k] if k < len(br) else None
        out.append(html.escape(b["label"], quote=False) if b and b["children"] else "")
    return out


def validate(md: str) -> list:
    """Avertissements (chaînes) sur une MindMap ; liste vide = rien à signaler."""
    w = []
    raw_lines = [l for l in _clean(md).split("\n") if l.strip()]
    if not raw_lines:
        return ["MindMap vide"]
    if not raw_lines[0].strip().startswith("# "):
        w.append("la MindMap doit commencer par « # Titre »")
    if sum(1 for l in raw_lines if re.match(r"^\s*#\s", l)) > 1:
        w.append("plusieurs titres « # » : un seul titre central (seul le dernier est gardé)")
    prev_depth = 0
    for l in raw_lines:
        t = l.strip()
        if l != l.lstrip():
            w.append(f"indentation ignorée (la profondeur vient des tirets) : « {t[:50]} »")
        if re.match(r"^#\s", t):
            prev_depth = 0
            continue
        if re.match(r"^##\s", t):
            d = 1
        else:
            m = re.match(r"^(-+)\s+", t)
            if not m:
                w.append(f"ligne ignorée (ni #, ni ##, ni -) : « {t[:50]} »")
                continue
            d = len(m.group(1)) + 1
            if d > 4:
                w.append(f"profondeur > --- : « {t[:50]} » (garde 3 niveaux sous la branche)")
        if d > prev_depth + 1:
            w.append(f"saut de niveau (manque un niveau parent) : « {t[:50]} »")
        prev_depth = d
        label = re.sub(r"^(##|-+)\s+", "", t)
        first = label[:1]
        if first and ord(first) >= 0x2190 and not any(label.startswith(e) for e in MINDMAP_EMOJI) \
                and not (0x1F1E6 <= ord(first) <= 0x1F1FF):
            w.append(f"symbole « {first} » hors légende en début de ligne : « {label[:40]} »")
        if len(_split_emoji(label)[1]) > 90:
            w.append(f"nœud trop long (> 90 caractères) : « {label[:40]}… »")
    root = parse(md)
    br = root["children"]
    if len(br) < 3:
        w.append(f"{len(br)} branche(s) « ## » : une MindMap se justifie à partir de 3 dimensions")
    if len(br) > MAX_BRANCHES:
        w.append(f"{len(br)} branches : au-delà de {MAX_BRANCHES}, pas de carte « Branche » dédiée → scinder")
    for b in br:
        name = b["label"][:40]
        if b["depth"] != 1:
            w.append(f"« {name} » est rattaché au titre sans « ## » : il est traité comme une branche")
        if not b["cat"]:
            w.append(f"branche « {name} » sans emoji de catégorie → couleur neutre")
        n = _count(b)
        if n == 0:
            w.append(f"branche « {name} » vide : aucune carte de rappel ne sera créée pour elle")
        elif n > 10:
            w.append(f"branche « {name} » : {n} nœuds à retrouver (> 10) → alléger ou scinder")
    if _count(root) > 40:
        w.append(f"{_count(root)} nœuds au total (> 40) : scinder en deux MindMaps")
    return w


# ════════════════════════════════════════════════════════════════════
# CSS (en plus du CSS commun build_css()) — style « manuel de cours soigné »
#   pastels clairs + bordure fine de la catégorie + texte foncé (clair) ;
#   fonds sombres teintés + bordure colorée (sombre) ; hiérarchie par taille et graisse.
# ════════════════════════════════════════════════════════════════════
_BG_LIGHT, _BG_DARK = "#ffffff", "#16181d"


def _hx(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _mix(a, b, t):
    """Mélange a → b (t = part de b), résultat hex opaque (net sur tout fond)."""
    return "#" + "".join(f"{round(x * (1 - t) + y * t):02x}" for x, y in zip(_hx(a), _hx(b)))


def _cat_css():
    out = []
    for k, v in PALETTE.items():
        base, key_l, key_d = v[1], v[3], v[4]
        lt = dict(c=_mix(key_l, "#000000", .18), bd=key_l, f=_mix(base, _BG_LIGHT, .84), f2=_mix(base, _BG_LIGHT, .93),
                  b2=_mix(key_l, _BG_LIGHT, .50), l=_mix(key_l, _BG_LIGHT, .42), d=base if k not in ("prosp",) else "#E6D34A")
        dk = dict(c=key_d, bd=_mix(key_d, _BG_DARK, .22), f=_mix(base, _BG_DARK, .80), f2=_mix(base, _BG_DARK, .88),
                  b2=_mix(key_d, _BG_DARK, .52), l=_mix(key_d, _BG_DARK, .48), d=key_d)
        decl = lambda d: ";".join(f"--m{n}:{val}" for n, val in d.items())  # noqa: E731
        out.append(f".mm-card .cat-{k}{{{decl(lt)}}}")
        out.append(f".nightMode .mm-card .cat-{k},.night_mode .mm-card .cat-{k}{{{decl(dk)}}}")
    out.append(".mm-card .cat-none{--mc:#37474F;--mbd:#78909C;--mf:#EEF1F3;--mf2:#F6F8F9;--mb2:#C4CDD2;--ml:#B7C2C8;--md:#90A4AE}")
    out.append(".nightMode .mm-card .cat-none,.night_mode .mm-card .cat-none{--mc:#CFD8DC;--mbd:#8A9AA3;--mf:#252a30;--mf2:#1f2328;"
               "--mb2:#4d5961;--ml:#4a555c;--md:#B0BEC5}")
    return "\n".join(out)


MINDMAP_CSS = """/* ═══ Carte mentale V10 — rappel actif, style manuel ═══ */
.mm-card { --mm-ink:#23252b; --mm-soft:#5f6570; --mm-paper:rgba(255,255,255,.88); --mm-edge:rgba(20,24,35,.08);
  --mm-dot:rgba(20,24,35,.055); --mm-trunk:#c9ced6; --mm-serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif; }
.nightMode .mm-card, .night_mode .mm-card { --mm-ink:#e6e8ec; --mm-soft:#a2a8b3; --mm-paper:rgba(20,22,28,.86);
  --mm-edge:rgba(255,255,255,.08); --mm-dot:rgba(255,255,255,.045); --mm-trunk:#3d434d; }
.mm-card .ancre { font-size:19px; }
.mm-ctx { font-size:13px; color:var(--muted); margin:2px 0 4px; }
.mm-q { font-size:17px; line-height:1.5; }
.mm-q .mm-chip { display:inline-block; padding:1px 9px; border-radius:8px; font-weight:650; color:var(--mc);
  background:var(--mf); border:1px solid var(--mbd); }
.mm { margin-top:12px; }
/* barre d'outils : discrète */
.mm-tools { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:0 0 10px; }
.mm-tools button { font:500 12.5px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; padding:5px 12px; border-radius:999px;
  border:1px solid var(--line); background:var(--mm-paper); color:var(--fg); cursor:pointer; }
.mm-tools button:hover { border-color:var(--muted); }
.mm-prog { margin-left:auto; display:flex; align-items:center; gap:4px; font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; }
.mm-prog i { width:6px; height:6px; border-radius:50%; background:var(--line); display:inline-block; transition:background .3s; }
.mm-prog i.on { background:var(--muted); }
.mm-prog span { margin-left:6px; }
/* feuille : fond légèrement opaque (lisible sur un fond d'image d'add-on), trame de points très légère */
.mm-paper { position:relative; background-color:var(--mm-paper); background-image:radial-gradient(var(--mm-dot) 1px, transparent 1.2px);
  background-size:18px 18px; border:1px solid var(--mm-edge); border-radius:16px; padding:22px 20px 16px;
  box-shadow:0 1px 2px rgba(0,0,0,.04), 0 10px 30px -12px rgba(0,0,0,.12); -webkit-backdrop-filter:blur(8px); backdrop-filter:blur(8px); }
.mm-map { position:relative; }
.mm-links { position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; overflow:visible; }
.mm-links path { fill:none; stroke:var(--ml); stroke-width:1.6; stroke-linecap:round; }
.mm-links circle { fill:var(--mbd); }
/* nœud central : sobre, filet double */
.mm-center { position:relative; z-index:1; text-align:center; padding:12px 16px 13px; border-radius:12px; background:var(--bg);
  border:1.25px solid var(--mm-ink); box-shadow:0 0 0 4px var(--bg), 0 0 0 5px rgba(128,128,128,.28);
  box-shadow:0 0 0 4px var(--bg), 0 0 0 5px color-mix(in srgb, var(--mm-ink) 22%, transparent); }
.mm-kick { font-size:10px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--mm-soft); margin-bottom:3px; }
.mm-title { font-size:17px; font-weight:720; line-height:1.3; color:var(--mm-ink); letter-spacing:-.005em; }
/* étroit : arbre vertical, tronc à gauche */
.mm-map.narrow .mm-center { margin:4px 4px 6px; }
.mm-trunk { position:relative; margin-left:14px; padding-top:6px; }
.mm-trunk > .mm-br { position:relative; padding-left:22px; padding-top:12px; }
.mm-trunk > .mm-br::before { content:""; position:absolute; left:0; top:0; width:16px; height:30px; border:solid var(--mm-trunk);
  border-width:0 0 1.5px 1.5px; border-bottom-left-radius:9px; }
.mm-trunk > .mm-br::after { content:""; position:absolute; left:0; top:30px; bottom:0; border-left:1.5px solid var(--mm-trunk); }
.mm-trunk > .mm-br:last-child::after { display:none; }
/* large : bilatéral */
.mm-map.wide { display:grid; grid-template-columns:minmax(0,1fr) minmax(140px,200px) minmax(0,1fr); column-gap:52px; align-items:center; }
.mm-map.wide .mm-center { grid-column:2; grid-row:1; }
.mm-map.wide .mm-right { grid-column:3; grid-row:1; }
.mm-map.wide .mm-left { grid-column:1; grid-row:1; }
.mm-side { display:flex; flex-direction:column; gap:22px; min-width:0; }
.mm-left .mm-br { display:flex; flex-direction:column; align-items:flex-end; text-align:right; }
/* tête de branche : pastel + bordure fine */
.mm-br { position:relative; z-index:1; min-width:0; transition:opacity .25s; }
.mm-bh { display:inline-flex; align-items:baseline; gap:8px; max-width:100%; box-sizing:border-box; padding:7px 13px 8px; border-radius:10px;
  background:var(--mf); border:1.25px solid var(--mbd); color:var(--mc); font-size:15.5px; font-weight:680; line-height:1.3; cursor:pointer; }
.mm-br.cat-prosp > .mm-bh, .mm-q .mm-chip.cat-prosp { border-style:dashed; }
.mm-n { font:italic 500 12px/1 var(--mm-serif); color:var(--mm-soft); white-space:nowrap; }
.mm-br.focus > .mm-bh { box-shadow:0 0 0 4px var(--mf2), 0 0 0 5px var(--mb2); }
.mm-br.dim { opacity:.42; }
.mm-br.dim:hover { opacity:.75; }
.mm-br.shut > .mm-tree { display:none; }
/* arbre : liaisons fines à coude arrondi */
.mm-tree { list-style:none; margin:0 0 0 13px; padding:0; }
.mm-tree li { position:relative; margin:0; padding:6px 0 0 20px; --mid:19px; }
.mm-tree li.d3 { --mid:16px; } .mm-tree li.d4 { --mid:15px; }
.mm-tree li::before { content:""; position:absolute; left:0; top:0; width:13px; height:var(--mid); border:solid var(--ml);
  border-width:0 0 1.25px 1.25px; border-bottom-left-radius:7px; }
.mm-tree li::after { content:""; position:absolute; left:0; top:var(--mid); bottom:0; border-left:1.25px solid var(--ml); }
.mm-tree li:last-child::after { display:none; }
.mm-tree .mm-tree { margin-left:10px; }
.mm-tree li.shut > .mm-tree { display:none; }
/* miroir (branches de gauche en disposition large) */
.mm-left .mm-tree { margin:0 13px 0 0; }
.mm-left .mm-tree .mm-tree { margin:0 10px 0 0; }
.mm-left .mm-tree li { padding:6px 20px 0 0; }
.mm-left .mm-tree li::before { left:auto; right:0; border-width:0 1.25px 1.25px 0; border-bottom-left-radius:0; border-bottom-right-radius:7px; }
.mm-left .mm-tree li::after { left:auto; right:0; border-left:0; border-right:1.25px solid var(--ml); }
/* nœuds : taille et graisse portent la hiérarchie */
.mm-node { display:inline-block; max-width:100%; box-sizing:border-box; padding:4px 11px 5px; border-radius:8px; background:var(--mf2);
  border:1px solid var(--mb2); color:var(--mm-ink); font-size:14.5px; font-weight:600; line-height:1.4; text-align:left; }
.mm-leaf { display:inline-block; max-width:100%; color:var(--mm-ink); font-size:14px; font-weight:400; line-height:1.45; text-align:left; }
li.d4 > .mm-leaf { font-size:13px; color:var(--mm-soft); }
.mm-left .mm-node, .mm-left .mm-leaf { text-align:right; }
.mm-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--md); box-shadow:0 0 0 1.5px var(--mf2), 0 0 0 2.5px var(--mb2);
  margin:0 7px 0 1px; vertical-align:1.5px; }
.mm-ann { font:italic 400 12.5px/1.3 var(--mm-serif); color:var(--mm-soft); margin-left:6px; white-space:nowrap; }
.mm-bh .mm-ann { font-weight:400; }
.mm-has { cursor:pointer; }
.mm-more { font:italic 500 11.5px/1 var(--mm-serif); color:var(--mm-soft); margin-left:6px; padding:1px 6px; border-radius:7px;
  border:1px solid var(--line); vertical-align:1px; cursor:pointer; white-space:nowrap; }
/* état masqué : hachures légères + point d'interrogation typographique ; feuilles = « blanc » à compléter */
.mm-mask { cursor:pointer; user-select:none; -webkit-user-select:none; }
.mm-mask .mm-t, .mm-mask .mm-ann, .mm-mask .mm-dot, .mm-mask .mm-img { display:none; }
/* V11 : portrait dans un nœud, image ou schéma sous une tête de branche */
.mm-img { width:30px; height:30px; border-radius:50%; object-fit:cover; object-position:50% 22%; vertical-align:middle;
  margin:-4px 7px -4px -3px; border:1.5px solid var(--mbd,#999); background:#fff; }
.mm-bimg { margin:8px 0 2px 13px; max-width:300px; }
.mm-bimg:has(svg) { max-width:380px; }
.mm-left .mm-bimg { margin-left:auto; margin-right:13px; }
.mm-bimg img { width:100%; border-radius:8px; background:#fff; display:block; }
.mm-bimg svg { width:100%; height:auto; display:block; }
.mm-br.shut > .mm-bimg { display:none; }
.mm-mask::after { content:"?"; font:italic 600 14px/1 var(--mm-serif); color:var(--mbd); opacity:.9; }
.mm-bh.mm-mask, .mm-node.mm-mask { min-width:7.5em; text-align:center; border-style:dashed;
  background-image:repeating-linear-gradient(135deg, color-mix(in srgb, var(--mbd) 13%, transparent) 0 1px, transparent 1px 7px); }
.mm-bh.mm-mask { min-width:9.5em; justify-content:center; }
.mm-leaf.mm-mask { min-width:8.5em; height:1.15em; border-bottom:1.5px dotted var(--mbd); text-align:right; }
.mm-leaf.mm-mask::after { font-size:12px; opacity:.7; }
.mm-mask:hover { filter:brightness(.97); }
/* révélation : sobre, du flou au net */
.mm-rev { animation:mmrev .38s cubic-bezier(.2,.7,.2,1); }
@keyframes mmrev { from { opacity:0; filter:blur(3px); transform:translateY(2px); } to { opacity:1; filter:none; transform:none; } }
@media (prefers-reduced-motion: reduce) { .mm-rev { animation:none; } }
/* légende discrète */
.mm-legend { display:flex; flex-wrap:wrap; gap:4px 14px; margin-top:16px; padding-top:9px; border-top:1px solid var(--mm-edge);
  font:italic 12px/1.3 var(--mm-serif); color:var(--mm-soft); }
.mm-legend b { font:600 10px/1.3 -apple-system,sans-serif; letter-spacing:.12em; text-transform:uppercase; font-style:normal; }
.mm-legend span { display:inline-flex; align-items:center; gap:5px; }
.mm-legend i { width:9px; height:9px; border-radius:3px; background:var(--mf); border:1px solid var(--mbd); display:inline-block; }
.mm-rep { font-size:17px; font-weight:600; margin-top:16px; }
@media (max-width:600px) { .mm-paper { padding:16px 12px 12px; border-radius:14px; } .mm-trunk { margin-left:10px; } }
""" + _cat_css() + "\n"


# ════════════════════════════════════════════════════════════════════
# JAVASCRIPT (inline, ES5, sans dépendance)
# ════════════════════════════════════════════════════════════════════
_emo_js = ",".join(f"['{e}','{c}']" for e, c in MINDMAP_EMOJI.items())
MINDMAP_JS = r"""<script>
(function(){
var EMO=[""" + _emo_js + r"""];
var CATN={risk:'conflit, risque',eco:'économie',pol:'politique',soc:'social',env:'environnement',date:'date',act:'acteur',enj:'enjeu',conc:'concept',inst:'institution',instr:'instrument',res:'ressource',prosp:'prospective'};
function clean(r){return (r||'').replace(/<br\s*\/?>/gi,'\n').replace(/<\/?(div|p)[^>]*>/gi,'\n').replace(/<[^>]+>/g,'')
 .replace(/&nbsp;/gi,' ').replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&#39;/gi,"'").replace(/&quot;/gi,'"').replace(/&amp;/gi,'&').replace(/ /g,' ');}
function emo(l){l=l.replace(/^\s+/,'');for(var i=0;i<EMO.length;i++){if(l.indexOf(EMO[i][0])===0)return [EMO[i][1],l.slice(EMO[i][0].length).replace(/^️/,'').replace(/^\s+/,'')];}return [null,l];}
function ann(l){var m=l.match(/^(.*\S)\s*\(([^()]{1,40})\)\s*$/);return m?[m[1],m[2]]:[l,''];}
function parse(raw){var root={label:'',cat:null,d:0,children:[]},stack=[root];
 clean(raw).replace(/\r/g,'').split('\n').forEach(function(line){var t=line.trim(),d=null,lab='';if(!t)return;
  if(/^#\s/.test(t)){root.label=t.replace(/^#\s*/,'');return;}
  if(/^##\s/.test(t)){d=1;lab=t.replace(/^##\s*/,'');}else{var m=t.match(/^(-+)\s+(.*)$/);if(m){d=m[1].length+1;lab=m[2];}}
  if(d===null)return;var e=emo(lab),a=ann(e[1]);while(stack.length<d)stack.push(stack[stack.length-1]);
  var p=stack[d-1]||root,n={label:a[0],ann:a[1],cat:e[0],d:d,children:[]};p.children.push(n);stack.length=d;stack.push(n);});
 return root;}
function mk(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
function count(n){var s=0;n.children.forEach(function(c){s+=1+count(c);});return s;}

function build(box){
 var src=box.querySelector('.mm-src');if(!src)return;
 var MED={noeuds:{},branches:{}};try{var mj=box.querySelector('.mm-med .mm-json');if(mj&&mj.textContent.trim())MED=JSON.parse(mj.textContent);}catch(e){}
 function low(s){return (s||'').toLowerCase();}
 var MEDVU={};/* un portrait par personne : sur sa première mention seulement */
 function medN(l){var k=Object.keys(MED.noeuds||{});for(var i=0;i<k.length;i++){if(!MEDVU[k[i]]&&low(l).indexOf(low(k[i]))>=0){MEDVU[k[i]]=1;return MED.noeuds[k[i]];}}return null;}
 function medB(l){var k=Object.keys(MED.branches||{});for(var i=0;i<k.length;i++){if(low(l).indexOf(low(k[i]))>=0)return MED.branches[k[i]];}return null;}
 var root=parse(src.innerHTML),mode=box.getAttribute('data-mode')||'structure',face=box.getAttribute('data-face')||'back',
     K=parseInt(box.getAttribute('data-k')||'0',10)-1,front=face==='front',br=root.children;
 if(!br.length&&!root.label)return;
 var card=box.closest?box.closest('.mm-card'):null,masks=[],shown=0,used={};
 if(mode==='branche'&&card&&br[K]){var q=card.querySelector('.mm-q');if(q){q.innerHTML='';
   q.appendChild(document.createTextNode(front?'Que contient la branche ':'Branche '));
   q.appendChild(mk('span','mm-chip cat-'+(br[K].cat||'none'),br[K].label));
   q.appendChild(document.createTextNode(front?' ? ('+count(br[K])+')':''));}
  var cx=card.querySelector('.mm-ctx');if(cx)cx.innerHTML=cx.innerHTML.replace(/\s*\(\d+\)\s*$/,'');}
 var tools=mk('div','mm-tools'),paper=mk('div','mm-paper'),map=mk('div','mm-map narrow'),NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');
 svg.setAttribute('class','mm-links');map.appendChild(svg);paper.appendChild(map);
 var center=mk('div','mm-center');center.appendChild(mk('div','mm-kick','Sujet'));center.appendChild(mk('div','mm-title',root.label||''));map.appendChild(center);
 var R=mk('div','mm-side mm-right'),L=mk('div','mm-side mm-left'),T=mk('div','mm-trunk'),half=Math.ceil(br.length/2),layout='';
 /* contenu d'un nœud (texte + annotation italique), masqué ou non */
 function fill(el,n,masked,withDot){if(withDot&&n.cat){var dt=mk('i','mm-dot cat-'+n.cat);dt.title=CATN[n.cat]||'';el.appendChild(dt);}
  var pim=medN(n.label);if(pim){var pi=document.createElement('img');pi.className='mm-img';pi.src=pim;pi.alt='';el.appendChild(pi);}
  el.appendChild(mk('span','mm-t',n.label));if(n.ann)el.appendChild(mk('span','mm-ann',n.ann));
  if(n.cat)used[n.cat]=1;
  if(masked){el.classList.add('mm-mask');el.title='Toucher pour révéler';masks.push({el:el,n:n});
   el.addEventListener('click',function(ev){ev.stopPropagation();reveal(el);});}}
 function reveal(el){if(!el.classList.contains('mm-mask'))return;el.classList.remove('mm-mask');el.removeAttribute('title');
  el.classList.remove('mm-rev');void el.offsetWidth;el.classList.add('mm-rev');
  setTimeout(function(){el.classList.remove('mm-rev');},450);shown++;upd();}
 function node(n,maskAll,depthOpen){var li=mk('li','d'+Math.min(n.d,4)),box2=mk('div',n.d===2?'mm-node':'mm-leaf');
  if(n.d===2&&n.cat)box2.className+=' cat-'+n.cat;fill(box2,n,maskAll,true);li.appendChild(box2);
  if(n.children.length){var ul=mk('ul','mm-tree');n.children.forEach(function(c){ul.appendChild(node(c,maskAll,depthOpen));});li.appendChild(ul);
   if(!maskAll){var more=mk('span','mm-more','+'+count(n));box2.appendChild(more);box2.classList.add('mm-has');
    var set=function(s){li.classList.toggle('shut',s);more.style.display=s?'':'none';};li._set=set;
    box2.addEventListener('click',function(ev){ev.stopPropagation();set(!li.classList.contains('shut'));draw();});set(n.d>=depthOpen);}}
  return li;}
 var sections=[];
 br.forEach(function(b,i){var cat=b.cat||'none',sec=mk('section','mm-br cat-'+cat),h=mk('div','mm-bh');sec.appendChild(h);
  var isK=(mode==='branche'&&i===K),maskHead=(mode==='structure'&&front),maskKids=(mode==='branche'&&front&&isK);
  fill(h,b,maskHead,false);var n=count(b);
  var bm=medB(b.label);if(bm&&!maskHead&&!(front&&isK)){var fg=mk('div','mm-bimg');
   if(bm.img){var bi=document.createElement('img');bi.src=bm.img;bi.alt='';fg.appendChild(bi);}else if(bm.svg){fg.innerHTML=bm.svg;}
   sec._bimg=fg;}
  if(b.children.length&&!maskHead){var ul=mk('ul','mm-tree'),depthOpen=(mode==='structure')?3:(isK?9:0);
   b.children.forEach(function(c){ul.appendChild(node(c,maskKids,depthOpen));});sec.appendChild(ul);
   if(!maskKids){var cnt=mk('span','mm-n');h.appendChild(cnt);
    var shutB=function(s){sec.classList.toggle('shut',s);cnt.textContent=s?n+' ›':'';cnt.style.display=s?'':'none';};
    shutB(mode==='branche'&&!isK);sec._shut=shutB;h.addEventListener('click',function(){shutB(!sec.classList.contains('shut'));draw();});}}
  if(sec._bimg)sec.appendChild(sec._bimg);
  if(mode==='branche')sec.classList.add(isK?'focus':'dim');sections.push(sec);});
 /* légende (verso) */
 if(!front){var cats=Object.keys(used);if(cats.length){var lg=mk('div','mm-legend');lg.appendChild(mk('b',null,'Légende'));
  cats.forEach(function(c){var s=mk('span','cat-'+c);s.appendChild(mk('i'));s.appendChild(document.createTextNode(CATN[c]||c));lg.appendChild(s);});paper.appendChild(lg);}}
 /* outils + progression */
 var prog=mk('div','mm-prog'),dots=[];
 function upd(){for(var i=0;i<dots.length;i++)dots[i].className=i<shown?'on':'';if(prog._t)prog._t.textContent=shown+' / '+masks.length;draw();}
 function btn(txt,fn){var b=mk('button',null,txt);b.type='button';b.addEventListener('click',fn);tools.appendChild(b);}
 if(masks.length){btn('Révéler le suivant',function(){for(var i=0;i<masks.length;i++){if(masks[i].el.classList.contains('mm-mask')){reveal(masks[i].el);return;}}});
  btn('Tout révéler',function(){masks.forEach(function(m){reveal(m.el);});});
  if(masks.length<=14)masks.forEach(function(){var d=mk('i');dots.push(d);prog.appendChild(d);});prog._t=mk('span');prog.appendChild(prog._t);tools.appendChild(prog);}
 else{btn('Tout déplier',function(){all(false);});btn('Replier',function(){all(true);});}
 function all(s){sections.forEach(function(sec){if(sec._shut)sec._shut(s&&!sec.classList.contains('focus'));});
  var lis=map.querySelectorAll('li');for(var i=0;i<lis.length;i++){if(lis[i]._set)lis[i]._set(s);}draw();}
 /* disposition : large = bilatéral (sens horaire), étroit = arbre vertical ; liaisons courbes du centre aux têtes */
 function place(wide){if(layout===(wide?'w':'n'))return;layout=wide?'w':'n';[R,L,T].forEach(function(c){if(c.parentNode)c.parentNode.removeChild(c);});
  if(wide){sections.forEach(function(sec,i){if(i<half)R.appendChild(sec);else L.insertBefore(sec,L.firstChild);});map.appendChild(R);map.appendChild(L);}
  else{sections.forEach(function(sec){T.appendChild(sec);});map.appendChild(T);}map.className='mm-map '+(wide?'wide':'narrow');}
 function draw(){var w=box.clientWidth||0,wide=w>=700&&br.length>1;place(wide);while(svg.firstChild)svg.removeChild(svg.firstChild);if(!wide)return;
  var m=map.getBoundingClientRect(),c=center.getBoundingClientRect();svg.setAttribute('viewBox','0 0 '+m.width+' '+m.height);
  sections.forEach(function(sec){var h=sec.querySelector('.mm-bh').getBoundingClientRect(),right=sec.parentNode===R,
   x0=(right?c.right:c.left)-m.left,y0=c.top+c.height/2-m.top,x1=(right?h.left:h.right)-m.left,y1=h.top+h.height/2-m.top,dx=(x1-x0)*0.55,
   g=document.createElementNS(NS,'g'),p=document.createElementNS(NS,'path'),o=document.createElementNS(NS,'circle');
   g.setAttribute('class',sec.className.replace(/.*(cat-\w+).*/,'$1'));
   p.setAttribute('d','M'+x0+','+y0+' C'+(x0+dx)+','+y0+' '+(x1-dx)+','+y1+' '+x1+','+y1);
   o.setAttribute('cx',x1);o.setAttribute('cy',y1);o.setAttribute('r',2.6);g.appendChild(p);g.appendChild(o);svg.appendChild(g);});}
 box.appendChild(tools);box.appendChild(paper);box._draw=draw;draw();upd();
 if(window.ResizeObserver){try{new ResizeObserver(function(){draw();}).observe(box);}catch(e){}}
}
var boxes=document.querySelectorAll('.mm:not([data-mm])');
for(var i=0;i<boxes.length;i++){boxes[i].setAttribute('data-mm','1');try{build(boxes[i]);}catch(e){boxes[i].appendChild(mk('div','mm-err','Carte mentale : erreur de rendu ('+e.message+')'));}}
if(!window.__mmResize){window.__mmResize=1;window.addEventListener('resize',function(){var b=document.querySelectorAll('.mm[data-mm]');
 for(var i=0;i<b.length;i++)if(b[i]._draw)b[i]._draw();});}
})();
</script>"""

# ════════════════════════════════════════════════════════════════════
# TEMPLATES
# ════════════════════════════════════════════════════════════════════
_SOURCE = ('{{#SourceURL}}<div class="src">📚 <a href="{{SourceURL}}">{{#SourceTitre}}{{SourceTitre}}{{/SourceTitre}}'
           '{{^SourceTitre}}Source{{/SourceTitre}}</a></div>{{/SourceURL}}')


def _box(mode, face, k=0):
    return (f'<div class="mm" data-mode="{mode}" data-face="{face}" data-k="{k}">'
            '<div class="mm-src" hidden style="display:none">{{Mindmap}}</div>'
            '<div class="mm-med" hidden style="display:none">{{Medias}}</div></div>')


STRUCTURE_FRONT = """{{#Mindmap}}<div class="v10 mm-card">
<div class="ancre">🗺️ Carte mentale · structure</div>
<div class="mm-q">{{Question}}</div>
""" + _box("structure", "front") + "\n</div>{{/Mindmap}}\n" + MINDMAP_JS

STRUCTURE_BACK = """<div class="v10 mm-card">
<div class="ancre">🗺️ Carte mentale · structure</div>
<div class="mm-q">{{Question}}</div>
<hr id="answer">
""" + _box("structure", "back") + """
{{#Reponse}}<div class="mm-rep">{{Reponse}}</div>{{/Reponse}}
""" + _SOURCE + "\n</div>\n" + MINDMAP_JS


def _branch_front(k):
    return ("{{#B%d}}<div class=\"v10 mm-card\">\n<div class=\"ancre\">🗺️ Carte mentale · branche %d</div>\n"
            "<div class=\"mm-ctx\">{{Question}}</div>\n<div class=\"mm-q\">{{B%d}}</div>\n" % (k, k, k)
            + _box("branche", "front", k) + "\n</div>{{/B%d}}\n" % k + MINDMAP_JS)


def _branch_back(k):
    return ("<div class=\"v10 mm-card\">\n<div class=\"ancre\">🗺️ Carte mentale · branche %d</div>\n"
            "<div class=\"mm-ctx\">{{Question}}</div>\n<div class=\"mm-q\">{{B%d}}</div>\n<hr id=\"answer\">\n" % (k, k)
            + _box("branche", "back", k) + "\n" + _SOURCE + "\n</div>\n" + MINDMAP_JS)


MINDMAP_TEMPLATES = [{"name": "Structure", "qfmt": STRUCTURE_FRONT, "afmt": STRUCTURE_BACK}] + [
    {"name": f"Branche {k}", "qfmt": _branch_front(k), "afmt": _branch_back(k)} for k in range(1, MAX_BRANCHES + 1)]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage : python3 mindmap.py fichier.md")
    md = Path(sys.argv[1]).read_text(encoding="utf-8")
    for m in validate(md):
        print("⚠", m)
    for k, v in enumerate(branch_flags(md), 1):
        print(f"B{k} = {v!r}")

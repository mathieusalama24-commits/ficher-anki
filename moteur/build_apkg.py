#!/usr/bin/env python3
"""
build_apkg.py — Ficher : JSON → paquet Anki (.apkg) ou charge utile MCP.

Usage :
    pip install genanki                                   (une seule fois)
    python build_apkg.py cartes.json -o sortie.apkg   → fichier à importer dans Anki
    python build_apkg.py cartes.json --mcp notes.json → notes prêtes pour addNotes (connecteur)
    ... --preview apercu/                                 → aperçu HTML clair + sombre de chaque carte

Nécessite dans le même dossier : features.py, portraits.py, mindmap.py, visuels.py,
occlusion.py, langues.py. Photos et images : cache portraits/ rempli par « python3 portraits.py cartes.json »
(machine avec accès à Wikipédia). Import : double-clic sur le .apkg.

Types de note embarqués (IDs fixes, identiques à chaque génération) :
  • « Ficher »            — carte principale + carte « Saisie » (réponse à taper) si le champ Saisie est rempli
  • « Ficher — Trous »    — texte à trous
  • « Ficher — Carte mentale » — carte mentale à rappel actif (# / ## / - / -- / ---) :
      1 carte Structure + 1 carte par branche (champs B1…B6 remplis automatiquement) — voir mindmap.py

Anti-doublon automatique : le GUID d'une note dérive de son ancre (ou de son texte / sa question).
Réimporter une carte à l'ancre identique MET À JOUR la note existante, révisions conservées.

FORMAT JSON
{
  "deck": "Ficher::Démarrage",   "tags": ["ficher"],
  "cartes": [
    { "modele": "basique", "type": "B", "ancre": "…", "question": "…", "reponse": "…",
      "titre": "", "meta": "", "indice": "", "puces": ["<li class=\\"eco\\"><b>Mot</b> → …</li>"],
      "visuel": {spec} ou "<svg…>", "visuel_recto": {spec}, "memo": "", "anecdote": "",
      "piege": "", "lien": "", "saisie": "", "saisie_consigne": "",
      "source_url": "https://…", "source_titre": "…", "tags": ["region::Asie"], "deck": "optionnel" },
    { "modele": "trous", "ancre": "…", "texte": "… {{c1::…}} …", "extra": "", "source_url": "…", "source_titre": "…",
      "icone": "📐", "contexte": "Chapitre · matière", "italique": true },
      → icone : remplace 🔢 dans le titre ; contexte : sous-titre du recto ; italique : texte en italique
        (articles de loi ; automatique pour les citations). Format « par cœur » : tout l'énoncé en blocs
        {{c1::…}} du même numéro → une seule carte, blocs révélés « Une par une » au verso.
    { "modele": "mindmap", "question": "…", "mindmap": "# …\\n## 🔵 …\\n- …\\n-- …", "reponse": "…", "source_url": "…" }
  ]
}
"""
import argparse
import html
import json
import re
import shutil
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from visuels import PALETTE, SpecError, render as render_visual, schema_css  # noqa: E402
from langues import (NOM_CHINOIS, MODEL_ID_CHINOIS, CHINOIS_FIELDS, CHINOIS_TEMPLATES,  # noqa: E402
                         CHINOIS_CSS, LANGUES, LANGUE_FIELDS, LANGUE_CSS, nom_modele_langue, templates_langue)
import occlusion  # noqa: E402
import features as v11  # noqa: E402
import portraits  # noqa: E402
from mindmap import (MINDMAP_FIELDS, MINDMAP_TEMPLATES, MINDMAP_CSS,  # noqa: E402
                         branch_flags, validate as mm_validate)

try:
    import genanki
except ImportError:
    genanki = None

from mindmap import MINDMAP_EMOJI  # noqa: E402,F401  (emoji → catégorie, source unique)
ICONES = {"A": "📖", "B": "⚡", "C": "🧠"}
MODEL_ID_BASIQUE, MODEL_ID_TROUS, MODEL_ID_MINDMAP = 1790500001, 1790500002, 1790500013  # IDs fixes : réimporter met à jour les types sans doublon
NOM_BASIQUE, NOM_TROUS, NOM_MINDMAP = "Ficher", "Ficher — Trous", "Ficher — Carte mentale"


# ════════════════════════════════════════════════════════════════════
# CSS COMMUN — modifier ici change l'apparence de TOUTES les cartes
# ════════════════════════════════════════════════════════════════════
def build_css() -> str:
    light = "\n".join(f"  --{k}:{v[1]};--{k}-t:{v[2]};--{k}-k:{v[3]};" for k, v in PALETTE.items())
    night = "\n".join(f"  --{k}-k:{v[4]};" for k, v in PALETTE.items())
    cats = "\n".join(
        f".hl.{k}{{background:var(--{k});color:var(--{k}-t);}}\n"
        f".k.{k},ul.puces li.{k}>b:first-child{{color:var(--{k}-k);}}\n"
        f"ul.puces li.{k}{{border-left-color:var(--{k});}}"
        for k in PALETTE)
    return f"""/* ═══ Ficher ═══ */
.card {{
{light}
  --fg:#1d1d1f; --bg:#fbfbfa; --muted:#6b6b6b; --line:#d9d9d9; --link:#1565C0; --v10-link:#1565C0; --chip:rgba(0,0,0,.05);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  font-size:16px; line-height:1.55; color:var(--fg); background:var(--bg);
  text-align:left; padding:18px clamp(12px, 4vw, 48px); margin:0;
}}
.nightMode, .night_mode, .nightMode .card, .night_mode .card, .card.nightMode, .card.night_mode {{
{night}
  --fg:#e8e8e8; --bg:#16181d; --muted:#9a9a9a; --line:#3a3d44; --link:#64B5F6; --v10-link:#64B5F6; --chip:rgba(255,255,255,.08);
}}
/* Mise en page : une seule colonne large (≤ 980 px), centrée dans la fenêtre, tout aligné sur le même bord gauche
   (recto, trait, verso, visuels). Sur téléphone : pleine largeur avec 12 px de marge. */
.v10 {{ max-width:980px; margin:0 auto; }}
.ancre {{ font-size:21px; font-weight:700; line-height:1.3; margin-bottom:6px; }}
.ancre .ico {{ margin-right:4px; }}
.titre {{ font-weight:700; font-style:italic; text-decoration:underline; text-underline-offset:3px; margin-bottom:6px; color:var(--pol-k); }}
.question {{ font-size:16px; line-height:1.45; }}
/* Formules (autres matières) : en violet, comme sur les fiches de l'utilisateur */
.formule {{ color:var(--eco-k); font-size:19px; text-align:center; margin:6px 0 12px; overflow-x:auto; }}
.fx {{ color:var(--eco-k); font-weight:600; }}
.etape {{ font-variant-numeric:tabular-nums; }}
/* Recto centré (habitude de l'utilisateur) ; le verso reste aligné à gauche pour la lecture */
.v10.recto {{ text-align:center; }}
.v10.recto .visuel .vz, .v10.recto .visuel .geo, .v10.recto .visuel > svg {{ margin-left:auto !important; margin-right:auto !important; }}
.v10.recto div.hint {{ display:inline-block; text-align:left; }}
.v10.recto #typeans {{ max-width:520px; margin-left:auto; margin-right:auto; display:block; text-align:center; }}
.attendu {{ font-size:26px; font-weight:700; margin:4px 0 8px; }}
.contexte {{ font-size:16px; color:var(--muted); line-height:1.5; }}
.v10 a.hint {{ display:inline-block; margin-top:10px; font-size:14px; }}
.v10 div.hint, .v10 a.hint + div {{ margin-top:10px; font-size:15px; padding:6px 10px; border-left:3px solid var(--v10-link); color:var(--fg); }}
/* Liens : Anki ou un add-on (fond d'écran…) peuvent imposer leur couleur à « a » / « .hint » → sélecteurs forts + !important */
.card .v10 a, .card .v10 a:link, .card .v10 a:visited, .card .v10 a.hint, .card .v10 .src a,
.nightMode .v10 a, .night_mode .v10 a, .nightMode .v10 a.hint, .night_mode .v10 a.hint {{ color:var(--v10-link) !important; text-decoration:none; }}
hr#answer {{ border:0; border-top:1px solid var(--line); margin:10px auto; max-width:980px; }}
.meta {{ font-size:13px; color:var(--muted); margin-bottom:8px; }}
.rep {{ font-size:18px; font-weight:600; line-height:1.45; margin-bottom:8px; }}
ul.puces {{ list-style:none; margin:0; padding-left:2px; font-size:15px; line-height:1.5; }}
ul.puces li {{ border-left:3px solid var(--line); padding-left:10px; margin-bottom:4px; }}
/* Mode test : tout le verso (sauf recto répété et source) est flouté ; chaque bloc se révèle au toucher */
.mt-bar {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:0 0 12px; }}
.mt-btn {{ font:600 13px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; padding:6px 12px; border-radius:999px;
  border:1px solid var(--line); background:var(--chip); color:var(--fg); cursor:pointer; }}
.mt-btn.on {{ background:var(--v10-link); border-color:var(--v10-link); color:#fff; }}
.mt-aide {{ font-size:12.5px; color:var(--muted); }}
.v10.mt-on .mt-bloc:not(.mt-vu) {{ filter:blur(8px); cursor:pointer; user-select:none; -webkit-user-select:none; transition:filter .15s; }}
.v10.mt-on .mt-bloc:not(.mt-vu):hover {{ filter:blur(6px); }}
.v10.mt-on .mt-bloc:not(.mt-vu) * {{ pointer-events:none; }}
/* Visuels : largeur maximale par famille (classe .vz-* posée par visuels.render) ; pleine largeur sur téléphone */
.visuel {{ margin:8px 0 4px; }}
/* la carte entière doit tenir à l'écran sans défiler : visuels plafonnés en hauteur */
.visuel > .vz:not(.vz-carte) svg, .visuel > svg {{ max-height:36vh; }}
.formule mjx-container[display="true"] {{ margin:.25em 0 !important; }}
.visuel .geo {{ max-width:min(500px, calc(44vh * var(--ar, 1.3))) !important; margin-left:auto !important; margin-right:auto !important; }}
.visuel svg {{ width:100%; max-width:100%; height:auto; display:block; }}
.visuel .vz, .visuel > svg {{ max-width:500px; margin-left:auto; margin-right:auto; }}
.visuel .geo-leg {{ display:inline-block; text-align:left; }}
.visuel .vz-carte {{ text-align:center; }}
.visuel .vz-carte .geo {{ text-align:left; }}
.visuel > .geo {{ max-width:500px !important; margin:0 auto !important; }}
.visuel .vz-graphique {{ max-width:600px; }}
.visuel .vz-carte {{ max-width:var(--vz-max, 500px); }}
.visuel .vz-bloc {{ max-width:760px; }}
@media (max-width:600px) {{
  .card {{ padding-left:12px; padding-right:12px; }}
  .visuel .vz, .visuel > svg, .visuel > .geo {{ max-width:none !important; }}
}}
.memo {{ margin-top:10px; padding:6px 10px; font-size:15px; border-left:4px solid #FBC02D; background:rgba(251,192,45,.12); border-radius:0 4px 4px 0; }}
.piege {{ margin-top:10px; padding:6px 10px; font-size:15px; border-left:4px solid #C62828; background:rgba(198,40,40,.09); border-radius:0 4px 4px 0; }}
.lien {{ margin-top:10px; padding:6px 10px; font-size:15px; border-left:4px solid #0277BD; background:rgba(2,119,189,.09); border-radius:0 4px 4px 0; }}
.anecdote {{ margin-top:8px; font-size:13px; color:var(--muted); font-style:italic; }}
.src {{ margin-top:12px; padding-top:6px; border-top:1px solid var(--line); font-size:12px; color:var(--muted); }}
.hl {{ padding:0 .25em; border-radius:3px; -webkit-box-decoration-break:clone; box-decoration-break:clone; }}
.hl.prosp {{ outline:1px dashed #8D7B00; }}
{cats}
/* Saisie (réponse tapée) */
#typeans {{ width:100%; box-sizing:border-box; font-size:18px; padding:8px 10px; margin-top:12px; border-radius:8px; border:1px solid var(--line); background:transparent; color:inherit; }}
code#typeans {{ display:block; font-family:inherit; }}
.typeGood {{ background:#2E7D32; color:#fff; }} .typeBad {{ background:#C62828; color:#fff; }} .typeMissed {{ background:#9E9E9E; color:#fff; }}
/* Trous */
.cloze-txt {{ font-size:19px; line-height:1.55; }}
.cloze {{ font-weight:700; color:var(--act-k); }}
.extra {{ margin-top:10px; font-size:15px; color:var(--muted); }}
/* Grand écran : texte un cran plus grand (la colonne est plus large) */
@media (min-width:900px) {{
  .card {{ font-size:17px; }}
  .question {{ font-size:17px; }}
  .rep {{ font-size:19px; }}
  ul.puces {{ font-size:16px; }}
}}
/* MindMap : voir MINDMAP_CSS (mindmap.py), ajouté au seul type « Carte mentale » */
"""


CSS = build_css() + "\n" + schema_css() + """
.v10 pre.code { display:inline-block; text-align:left; margin:10px auto; padding:12px 16px; border-radius:10px;
  background:rgba(127,127,127,.10); border:1px solid rgba(127,127,127,.25); font:15px/1.55 "SF Mono",Menlo,Consolas,monospace; white-space:pre; overflow-x:auto; max-width:100%; }
.v10 pre.code .cloze { font-family:inherit; }
/* au verso, le visuel du recto (carte muette, image masquée) laisse place à sa version corrigée */
.card:has(.v10.verso .visuel) .v10.recto .visuel { display:none; }
.v10.verso:has(.vz-occ-verso) { display:flex; flex-direction:column; }
.v10.verso .visuel:has(.vz-occ-verso) { order:-1; margin-top:4px; }
.v10 .tts { display:inline-block; font-size:28px; padding:6px 16px; border-radius:30px; border:1px solid rgba(127,127,127,.35); }
""" + v11.css() + portraits.CSS

SOURCE_BLOCK = ('{{#SourceURL}}<div class="src">📚 <a href="{{SourceURL}}">{{#SourceTitre}}{{SourceTitre}}{{/SourceTitre}}'
                '{{^SourceTitre}}Source{{/SourceTitre}}</a></div>{{/SourceURL}}')

# Mode test (verso de la carte principale) : floute réponse, puces, visuel et encarts ; chaque bloc se révèle
# au toucher, « Tout afficher » révèle le reste. Recto répété et source restent lisibles. Choix mémorisé par appareil.
# Idempotent : Anki peut rejouer le script, la barre n'est créée qu'une fois.
MODE_TEST_JS = r"""<script>(function(){var v=document.querySelector('.v10.verso');if(!v||v.querySelector('.mt-bar'))return;
var blocs=[].slice.call(v.querySelectorAll('.rep,ul.puces>li,.visuel,.piege,.lien,.memo,.anecdote'));if(!blocs.length)return;
blocs.forEach(function(b){b.classList.add('mt-bloc');});
var on=false;try{on=localStorage.getItem('v10-test')==='1';}catch(e){}
function mk(t,c){var e=document.createElement(t);e.className=c;if(t==='button')e.type='button';return e;}
var bar=mk('div','mt-bar'),tg=mk('button','mt-btn mt-toggle'),all=mk('button','mt-btn mt-all'),aide=mk('span','mt-aide');
all.textContent='👁 Tout afficher';bar.appendChild(tg);bar.appendChild(all);bar.appendChild(aide);v.insertBefore(bar,v.firstChild);
function reste(){return blocs.filter(function(b){return !b.classList.contains('mt-vu');}).length;}
function maj(){var r=reste();v.classList.toggle('mt-on',on);tg.classList.toggle('on',on);tg.setAttribute('aria-pressed',on?'true':'false');
tg.textContent=on?'🙈 Mode test : activé':'🙈 Mode test';all.style.display=on&&r?'':'none';
aide.textContent=on?(r?'Touche un bloc flou pour le révéler ('+r+' masqué'+(r>1?'s':'')+')':'Tout est révélé'):'';}
function set(x){on=x;try{localStorage.setItem('v10-test',x?'1':'0');}catch(e){}blocs.forEach(function(b){b.classList.remove('mt-vu');});maj();}
tg.addEventListener('click',function(e){e.stopPropagation();set(!on);});
all.addEventListener('click',function(e){e.stopPropagation();blocs.forEach(function(b){b.classList.add('mt-vu');});maj();});
v.addEventListener('click',function(e){if(!on||!e.target.closest)return;var b=e.target.closest('.mt-bloc');
if(b&&!b.classList.contains('mt-vu')){e.preventDefault();e.stopPropagation();b.classList.add('mt-vu');maj();}},true);
maj();})();</script>"""

CARTE_FRONT = """<div class="v10 recto">
<div class="ancre"><span class="ico">{{Icone}}</span> {{Ancre}}</div>
{{#Titre}}<div class="titre">{{Titre}}</div>{{/Titre}}
<div class="question">{{Question}}</div>
{{#Date}}<div class="q-pill">{{#Auteurs}}Auteur et date à retrouver{{/Auteurs}}{{^Auteurs}}Date à retrouver{{/Auteurs}}</div>{{/Date}}
{{#Estimation}}{{Estimation}}{{/Estimation}}
{{#PortraitsRecto}}<div class="portraits-r">{{PortraitsRecto}}</div>{{/PortraitsRecto}}
{{#ImagesRecto}}<div class="images-r">{{ImagesRecto}}</div>{{/ImagesRecto}}
{{#VisuelRecto}}<div class="visuel">{{VisuelRecto}}</div>{{/VisuelRecto}}
{{#Indice}}{{hint:Indice}}{{/Indice}}
</div>
{{#Estimation}}""" + v11.ESTIMATION_JS + "{{/Estimation}}"

CARTE_BACK = """{{FrontSide}}
<hr id="answer">
<div class="v10 verso">
{{#Date}}<div class="quand"><span class="q-date">{{Date}}</span>{{#Auteurs}}<span class="q-aut">{{Auteurs}}</span>{{/Auteurs}}</div>{{/Date}}
{{#Prononciation}}<div class="pron">{{Prononciation}}</div>{{/Prononciation}}
{{#Meta}}<div class="meta">{{Meta}}</div>{{/Meta}}
<div class="rep">{{Reponse}}</div>
{{#Decomposition}}<div class="decomp">{{Decomposition}}</div>{{/Decomposition}}
{{#Puces}}<ul class="puces">{{Puces}}</ul>{{/Puces}}
{{#Portraits}}<div class="portraits">{{Portraits}}</div>{{/Portraits}}
{{#Images}}<div class="visuel images">{{Images}}</div>{{/Images}}
{{#Visuel}}<div class="visuel">{{Visuel}}</div>{{/Visuel}}
{{#Piege}}<div class="piege">⚠️ <b>Ne pas confondre :</b> {{Piege}}</div>{{/Piege}}
{{#Lien}}<div class="lien">🔗 <b>Relie à :</b> {{Lien}}</div>{{/Lien}}
{{#Memo}}<div class="memo">💡 <b>Mnémo :</b> {{Memo}}</div>{{/Memo}}
{{#Anecdote}}<div class="anecdote">🕵️ {{Anecdote}}</div>{{/Anecdote}}
""" + SOURCE_BLOCK + "\n</div>\n" + v11.MODES_JS

SAISIE_FRONT = """{{#Saisie}}<div class="v10 recto">
<div class="ancre"><span class="ico">⌨️</span> À écrire de mémoire</div>
<div class="question">{{#SaisieConsigne}}{{SaisieConsigne}}{{/SaisieConsigne}}{{^SaisieConsigne}}Tape la réponse exacte.{{/SaisieConsigne}}</div>
{{#VisuelRecto}}<div class="visuel">{{VisuelRecto}}</div>{{/VisuelRecto}}
{{type:Saisie}}
<div class="sx-zone"></div><span class="sx-k" hidden style="display:none">{{Saisie}}</span>
</div>""" + v11.SAISIE_FRONT_JS + "{{/Saisie}}"

SAISIE_BACK = """<div class="v10 recto">
<div class="ancre"><span class="ico">⌨️</span> À écrire de mémoire</div>
<div class="question">{{#SaisieConsigne}}{{SaisieConsigne}}{{/SaisieConsigne}}{{^SaisieConsigne}}Tape la réponse exacte.{{/SaisieConsigne}}</div>
{{type:Saisie}}
</div>
<hr id="answer">
<div class="v10">
<div class="attendu">✅ {{Saisie}}</div>
<div class="sx-verdict"></div><span class="sx-var" hidden style="display:none">{{SaisieVariantes}}</span>
<div class="contexte">{{Reponse}}</div>
""" + SOURCE_BLOCK + "\n</div>" + v11.SAISIE_BACK_JS

VISAGE_RECTO = """<div class="v10 recto">
<div class="ancre"><span class="ico">👤</span> Qui est-ce ?</div>
{{PortraitVisage}}
<div class="question">{{PortraitCarte}}</div>
</div>"""
VISAGE_FRONT = "{{#PortraitCarte}}" + VISAGE_RECTO + "{{/PortraitCarte}}"
VISAGE_BACK = VISAGE_RECTO + """
<hr id="answer">
<div class="v10">{{PortraitNom}}</div>"""

BASIQUE_FIELDS = ["Ancre", "Icone", "Titre", "Question", "VisuelRecto", "Indice", "Meta", "Reponse", "Puces",
                  "Visuel", "Piege", "Lien", "Memo", "Anecdote", "SourceURL", "SourceTitre", "Saisie", "SaisieConsigne",
                  "Estimation", "Decomposition", "SaisieVariantes", "Portraits", "PortraitVisage", "PortraitNom", "PortraitCarte", "Date", "Auteurs", "PortraitsRecto", "Images", "ImagesRecto", "Prononciation"]  # V11 : champs ajoutés en fin de liste (fusion sans perte)

TROUS_TETE = """<div class="ancre" style="font-size:18px;">{{#Icone}}{{Icone}}{{/Icone}}{{^Icone}}🔢{{/Icone}} {{Ancre}}</div>
{{#Image}}<div class="portraits-r">{{Image}}</div>{{/Image}}
{{#Contexte}}<div class="cit-ctx">{{Contexte}}</div>{{/Contexte}}"""
TROUS_FRONT = """<div class="v10 recto">
""" + TROUS_TETE + """
<div class="cloze-txt">{{cloze:Texte}}</div>
</div>"""
TROUS_BACK = """<div class="v10 recto trous-v">
""" + TROUS_TETE + """
<div class="cloze-txt">{{cloze:Texte}}</div>
{{#Prononciation}}<div class="pron">{{Prononciation}}</div>{{/Prononciation}}
{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}
""" + SOURCE_BLOCK + "\n</div>" + v11.MODES_JS
TROUS_FIELDS = ["Texte", "Ancre", "Extra", "SourceURL", "SourceTitre", "Icone", "Image", "Contexte", "Prononciation"]  # V11 : 4 champs

# MindMap à rappel actif (cartes « Structure » + « Branche 1…6 ») : templates, CSS et JS dans mindmap.py


def make_models():
    basique = genanki.Model(
        MODEL_ID_BASIQUE, NOM_BASIQUE, fields=[{"name": f} for f in BASIQUE_FIELDS],
        templates=[{"name": "Carte", "qfmt": CARTE_FRONT, "afmt": CARTE_BACK},
                   {"name": "Saisie", "qfmt": SAISIE_FRONT, "afmt": SAISIE_BACK},
                   {"name": "Visage", "qfmt": VISAGE_FRONT, "afmt": VISAGE_BACK}],
        css=CSS, sort_field_index=0)
    trous = genanki.Model(
        MODEL_ID_TROUS, NOM_TROUS, fields=[{"name": f} for f in TROUS_FIELDS],
        templates=[{"name": "Trous", "qfmt": TROUS_FRONT, "afmt": TROUS_BACK}],
        css=CSS, model_type=genanki.Model.CLOZE, sort_field_index=1)
    mindmap = genanki.Model(
        MODEL_ID_MINDMAP, NOM_MINDMAP, fields=[{"name": f} for f in MINDMAP_FIELDS],
        templates=MINDMAP_TEMPLATES, css=CSS + MINDMAP_CSS, sort_field_index=0)
    chinois = genanki.Model(
        MODEL_ID_CHINOIS, NOM_CHINOIS, fields=[{"name": f} for f in CHINOIS_FIELDS],
        templates=CHINOIS_TEMPLATES, css=CSS + CHINOIS_CSS, sort_field_index=0)
    out = {"basique": basique, "trous": trous, "mindmap": mindmap, "chinois": chinois}
    for cle, (_, _, _, mid) in LANGUES.items():
        out[cle] = genanki.Model(mid, nom_modele_langue(cle), fields=[{"name": f} for f in LANGUE_FIELDS],
                                 templates=templates_langue(cle), css=CSS + LANGUE_CSS, sort_field_index=0)
    return out


# ════════════════════════════════════════════════════════════════════
# VALIDATIONS
# ════════════════════════════════════════════════════════════════════
HL_RE = re.compile(r'class="hl ([a-z]+)"')
CLS_RE = re.compile(r'<(?:span|b|li)[^>]*class="(?:hl |k )?([a-z]+)"')
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
BAD_EMOJI_RE = re.compile("[\U0001FB00-\U0001FBFF]")


JSON_DIR = ["."]          # dossier du JSON (portraits/ y est cherché)
PORTRAIT_MEDIA = set()    # photos à embarquer dans le .apkg


def _plain(t):
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def norm_txt(t):
    t = unicodedata.normalize("NFKD", html.unescape(re.sub(r"<[^>]+>", "", t or "")))
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in t if not unicodedata.combining(ch)).lower())


def guid(prefix, text):
    s = re.sub(r"<[^>]+>", "", text or "")
    s = unicodedata.normalize("NFKD", html.unescape(s))
    s = re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip().lower()
    return genanki.guid_for(prefix, s) if genanki else f"{prefix}:{s}"


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, w, m):
        self.errors.append(f"✗ [{w}] {m}")

    def warn(self, w, m):
        self.warnings.append(f"⚠ [{w}] {m}")


def check_classes(where, text, rep):
    for c in CLS_RE.findall(text or ""):
        if c not in PALETTE and c not in ("puces", "rest", "fx", "formule", "etape"):
            rep.err(where, f'classe de couleur inconnue « {c} » (autorisées : {", ".join(PALETTE)})')


def visual(where, v, rep, used_geo):
    if not v:
        return ""
    try:
        out = render_visual(v)
    except SpecError as e:
        rep.err(where, f"visuel : {e}")
        return ""
    except (KeyError, TypeError, ValueError) as e:
        rep.err(where, f"visuel : spec mal formée ({e!r})")
        return ""
    if isinstance(v, dict) and v.get("type") == "carte":
        used_geo.add(v["fond"] + ("_muet" if v.get("muette") else ""))
    if isinstance(v, str) and out.lstrip().startswith("<svg"):
        try:
            root = ET.fromstring(out)
            for t in root.iter("{http://www.w3.org/2000/svg}text"):
                if EMOJI_RE.search("".join(t.itertext())):
                    rep.err(where, "emoji dans un <text> SVG")
        except ET.ParseError as e:
            rep.err(where, f"SVG invalide : {e}")
    return out


def mathjax(t):
    """Convertit la notation de l'éditeur Anki <anki-mathjax> en MathJax stocké (\\( \\) / \\[ \\])."""
    if not t or "anki-mathjax" not in t:
        return t
    t = re.sub(r'<anki-mathjax[^>]*block="true"[^>]*>(.*?)</anki-mathjax>', r'\\[\1\\]', t, flags=re.S)
    return re.sub(r'<anki-mathjax[^>]*>(.*?)</anki-mathjax>', r'\\(\1\\)', t, flags=re.S)


def prep_basique(c, i, rep, used_geo):
    where = f"carte {i} « {c.get('ancre', '?')[:40]} »"
    for k in ("ancre", "question", "reponse"):
        if not (c.get(k) or "").strip():
            rep.err(where, f"champ obligatoire vide : {k}")
    typ = (c.get("type") or "").upper()
    if not c.get("icone") and typ not in ICONES:
        rep.err(where, f"type inconnu « {typ} » (A, B ou C) — ou fournir \"icone\" (modules d'autres matières)")
    for k in ("question", "reponse", "meta", "memo", "piege", "lien", "indice", "titre"):
        if c.get(k):
            c[k] = mathjax(c[k])
    if isinstance(c.get("puces"), list):
        c["puces"] = [mathjax(x) for x in c["puces"]]
    puces = c.get("puces") or []
    puces_html = "".join(puces) if isinstance(puces, list) else str(puces)
    n_li = len(re.findall(r"<li\b", puces_html))
    q = c.get("question", "")
    m = re.search(r"\((\d+)\)\s*$", re.sub(r"<[^>]+>", "", q).strip())
    if m and int(m.group(1)) != n_li:
        rep.warn(where, f"(N) corrigé : {m.group(1)} → {n_li}")
        q = re.sub(r"\(\d+\)(\s*(?:</[^>]+>\s*)*)$", f"({n_li})\\1", q.strip())
    elif not m and n_li >= 2 and not c.get("_sans_n") and not c.get("estimation"):  # estimation : on cherche un chiffre, pas N idées
        q = q.rstrip() + f" ({n_li})"   # plusieurs puces à retrouver → le recto annonce combien
    if n_li > 4:
        rep.warn(where, f"{n_li} puces : diviser la carte ?")
    recto_hl = len(HL_RE.findall(q))
    total = recto_hl + len(HL_RE.findall(c.get("reponse", "") + puces_html))
    if recto_hl > 3:
        rep.warn(where, f"{recto_hl} surlignages au recto (max 3)")
    if total > 6:
        rep.warn(where, f"{total} surlignages sur la carte (max conseillé 6)")
    for k in ("question", "reponse", "meta", "memo", "piege", "lien", "indice"):
        check_classes(where, c.get(k, ""), rep)
    check_classes(where, puces_html, rep)
    if c.get("memo") and c.get("anecdote"):
        rep.warn(where, "mnémo ET anecdote : n'en garder qu'une")
    sa_brut = c.get("saisie", "")
    if sa_brut and "<" in sa_brut:
        rep.err(where, "saisie : texte brut uniquement (pas de HTML)")
    sa, variantes = v11.saisie_variantes(sa_brut) if sa_brut else ("", [])
    for x in variantes[1:]:
        if norm_txt(x) and norm_txt(x) in norm_txt(c.get("saisie_consigne", "")):
            rep.err(where, f"saisie_consigne contient une variante de la réponse (« {x} »)")
    if sa and len(re.sub(r"<[^>]+>", "", sa)) > 40:
        rep.warn(where, "saisie > 40 caractères : la comparaison lettre à lettre devient pénible")
    if sa and norm_txt(sa) in norm_txt(c.get("saisie_consigne", "")):
        rep.err(where, "saisie_consigne contient la réponse à taper : reformule-la sans la donner")
    url = c.get("source_url", "")
    if not url.startswith("http"):
        rep.err(where, "source_url manquante ou invalide")
    est, dec = "", ""
    if c.get("estimation"):
        try:
            est = v11.estimation_html(c["estimation"], c.get("ancre", ""))
        except v11.FeatureError as e:
            rep.err(where, str(e))
    if c.get("decomposition"):
        try:
            dec, w = v11.decomposition_html(c["decomposition"])
            if w:
                rep.warn(where, w)
        except v11.FeatureError as e:
            rep.err(where, str(e))
    pts_html, pt_vis, pt_nom, pt_carte, pts_recto = "", "", "", "", ""
    if c.get("portraits"):
        pdir, credits = portraits.charger(JSON_DIR[0])
        ok = []
        for pt in c["portraits"]:
            if not pt.get("wiki") and not pt.get("fichier"):
                rep.err(where, "portrait : \"wiki\" (titre de l'article) ou \"fichier\" obligatoire")
                continue
            pt.setdefault("wiki", pt.get("nom", ""))
            f = pdir / portraits.nom_fichier(pt)
            if not f.exists():
                rep.warn(where, f"portrait « {pt['wiki']} » absent de portraits/ : lance « python3 portraits.py <json> » (réseau requis) — ignoré")
                continue
            PORTRAIT_MEDIA.add(str(f.resolve()))
            ok.append(pt)
        if ok:
            # nom déjà au recto → photo au recto (associer le visage au nom) ; nom à retrouver → photo au verso
            recto_txt = _plain(" ".join(c.get(k, "") for k in ("ancre", "titre", "question")))
            def au_recto(x):
                if "recto" in x:
                    return bool(x["recto"])
                mots = [w for w in re.findall(r"\w+", _plain(x.get("nom") or x["wiki"])) if len(w) > 3]
                return bool(mots) and mots[-1] in recto_txt
            r_ok = [x for x in ok if au_recto(x)]
            ok = [x for x in ok if not au_recto(x)]
            pts_recto = portraits.html_recto(r_ok, credits) if r_ok else ""
        if ok:
            pts_html = portraits.html_verso(ok, credits)
            vis_p = next((x for x in ok if x.get("carte")), None)
            if vis_p:
                pt_vis = portraits.html_visage(vis_p)
                pt_carte = html.escape(vis_p["carte"])
                pt_nom = portraits.html_nom(vis_p, credits)
                if any(len(w) > 3 and w in norm_txt(vis_p["carte"]) for w in re.findall(r"\w+", _plain(vis_p.get("nom") or vis_p["wiki"]))):
                    rep.err(where, "portrait « carte » : l'indice contient le nom de la personne")
    if c.get("date"):  # la date se retrouve au verso : elle ne doit pas apparaître au recto
        recto = norm_txt(" ".join(c.get(k, "") for k in ("ancre", "titre", "question", "indice")))
        for bout in re.findall(r"\d{4}|\w{4,}", _plain(c["date"])):
            if bout.isdigit() and bout in recto:
                rep.err(where, f"la date « {c['date']} » est au recto (ancre, titre ou question) : retire-la, elle est révélée au verso")
                break
        for a_ in re.findall(r"\w{4,}", _plain(c.get("auteurs", ""))):
            if norm_txt(a_) in recto:
                rep.err(where, f"l'auteur « {a_} » est au recto : retire-le, il est révélé au verso")
                break
    imgs_v, imgs_r = "", ""
    if c.get("images"):
        pdir, credits = portraits.charger(JSON_DIR[0])
        ok = []
        for im in c["images"]:
            if not (im.get("commons") or im.get("url") or im.get("fichier")):
                rep.err(where, "image : \"commons\", \"url\" ou \"fichier\" obligatoire")
                continue
            f = pdir / portraits.nom_image(im)
            if not f.exists():
                rep.warn(where, f"image « {im.get('commons') or im.get('url')} » absente de portraits/ : lance portraits.py (réseau requis) — ignorée")
                continue
            PORTRAIT_MEDIA.add(str(f.resolve()))
            ok.append(im)
        imgs_v = portraits.html_images([x for x in ok if x.get("face", "verso") == "verso"], credits)
        imgs_r = portraits.html_images([x for x in ok if x.get("face") == "recto"], credits)
        if imgs_v and c.get("visuel"):
            rep.warn(where, "image importée ET visuel au verso : jamais deux visuels, garde le plus parlant")
    vis = visual(where, c.get("visuel"), rep, used_geo)
    vis_r = visual(where + " recto", c.get("visuel_recto"), rep, used_geo)
    if isinstance(c.get("visuel_recto"), dict) and c["visuel_recto"].get("type") == "carte" and not c["visuel_recto"].get("muette"):
        rep.warn(where, "visuel_recto de type carte sans \"muette\": true → la légende dévoile la réponse au recto")
    fields = {
        "Ancre": c.get("ancre", "").strip(), "Icone": c.get("icone") or ICONES.get(typ, ""), "Titre": c.get("titre", ""),
        "Question": q, "VisuelRecto": vis_r, "Indice": c.get("indice", ""), "Meta": c.get("meta", ""),
        "Reponse": c.get("reponse", ""), "Puces": puces_html, "Visuel": vis, "Piege": c.get("piege", ""),
        "Lien": c.get("lien", ""), "Memo": c.get("memo", ""), "Anecdote": c.get("anecdote", ""),
        "SourceURL": url, "SourceTitre": c.get("source_titre", ""), "Saisie": sa,
        "SaisieConsigne": c.get("saisie_consigne", ""),
        "Estimation": est, "Decomposition": dec, "SaisieVariantes": "|".join(variantes) if len(variantes) > 1 else "",
        "Date": c.get("date", ""), "Auteurs": c.get("auteurs", ""), "Portraits": pts_html, "PortraitsRecto": pts_recto, "Prononciation": prononciation(c, rep, where), "Images": imgs_v, "ImagesRecto": imgs_r, "PortraitVisage": pt_vis, "PortraitNom": pt_nom, "PortraitCarte": pt_carte,
    }
    return NOM_BASIQUE, [fields[f] for f in BASIQUE_FIELDS], guid("geo-v10", c.get("_guid") or c.get("ancre", ""))


TTS_LANGUES = {"fr": "fr_FR", "en": "en_US", "pl": "pl_PL", "zh": "zh_CN", "ru": "ru_RU", "de": "de_DE", "es": "es_ES",
               "it": "it_IT", "ar": "ar_SA", "tr": "tr_TR", "uk": "uk_UA", "ja": "ja_JP", "ko": "ko_KR", "pt": "pt_BR", "fa": "fa_IR", "he": "he_IL"}


def prononciation(c, rep, where):
    """« prononcer » : [{"texte": "Zbigniew Brzeziński", "langue": "pl"}] → boutons audio (voix de synthèse d'Anki)."""
    out = []
    for p in c.get("prononcer", []) or []:
        lg = TTS_LANGUES.get(p.get("langue", ""), p.get("langue", ""))
        if not re.fullmatch(r"[a-z]{2}_[A-Z]{2}", lg or ""):
            rep.err(where, f"prononcer : langue inconnue « {p.get('langue')} » ({', '.join(TTS_LANGUES)})")
            continue
        t = html.escape(p.get("texte", ""))
        out.append(f'<span class="pron-it"><span class="pron-t">{t}</span> [anki:tts lang={lg}]{t}[/anki:tts]</span>')
    return "".join(out)


def media(item, rep, where):
    """Portrait (« wiki » sans « commons »/« url ») ou image : nom du fichier en cache portraits/, ajouté au paquet."""
    pdir, _ = portraits.charger(JSON_DIR[0])
    portrait = item.get("wiki") and not (item.get("commons") or item.get("url"))
    f = pdir / (portraits.nom_fichier(item) if portrait else portraits.nom_image(item))
    if not f.exists():
        rep.warn(where, f"média « {item.get('wiki') or item.get('commons') or item.get('url')} » absent de portraits/ : "
                        "lance « python3 portraits.py <json> » (réseau requis) — ignoré")
        return None
    PORTRAIT_MEDIA.add(str(f.resolve()))
    return f.name


def prep_citation(c, i, rep, used_geo):
    """Citation à trous : l'auteur (et son portrait) au recto, les mots porteurs de la citation à retrouver."""
    where = f"carte {i} (citation) « {c.get('auteur', '?')[:40]} »"
    cit = c.get("citation", "")
    if not re.search(r"\{\{c\d+::", cit):
        rep.err(where, "citation : mets les mots porteurs entre {{c1::…}}")
    img = ""
    if c.get("portrait"):
        f = media(c["portrait"], rep, where)
        if f:
            img = f'<img class="pt-r" src="{html.escape(f)}" alt="">'
    t = dict(c, modele="trous", italique=True, ancre=c.get("auteur", ""), texte=f"« {cit.strip(' «»')} »")
    mname, vals, g = prep_trous(t, i, rep, used_geo)
    f = dict(zip(TROUS_FIELDS, vals))
    f.update(Icone="💬", Image=img, Contexte=html.escape(c.get("contexte", "")), Prononciation=prononciation(c, rep, where))
    return mname, [f[k] for k in TROUS_FIELDS], g


def prep_trous(c, i, rep, used_geo):
    where = f"carte {i} (trous) « {c.get('ancre', '?')[:40]} »"
    texte = mathjax(c.get("texte", ""))
    cle_guid = c.get("_guid") or texte  # calculée AVANT l'italique : réimporter une ancienne carte la met à jour
    if c.get("italique"):  # citations, articles de loi : texte en italique
        texte = f"<i>{texte}</i>"
    if c.get("extra"):
        c["extra"] = mathjax(c["extra"])
    if re.search(r"\{\{c\d+::[^}]*\\\(", texte) and "}}}" in texte:
        rep.warn(where, "formule dans un trou : sépare les accolades (« } } ») pour ne pas fermer le trou trop tôt")
    if not re.search(r"\{\{c\d+::", texte):
        rep.err(where, "aucun trou {{c1::…}}")
    if not c.get("source_url", "").startswith("http"):
        rep.err(where, "source_url manquante ou invalide")
    check_classes(where, texte + c.get("extra", ""), rep)
    return NOM_TROUS, [texte, c.get("ancre", ""), c.get("extra", ""), c.get("source_url", ""),
                       c.get("source_titre", ""), c.get("icone", ""), "", html.escape(c.get("contexte", "")),
                       prononciation(c, rep, where)], guid("geo-v10-trous", cle_guid)


def prep_mindmap(c, i, rep, used_geo):
    where = f"carte {i} (mindmap) « {c.get('question', '?')[:40]} »"
    md = c.get("mindmap", "")
    lines = [l.strip() for l in md.replace("\r", "").split("\n") if l.strip()]
    if not lines or not lines[0].startswith("# "):
        rep.err(where, "la MindMap doit commencer par '# Titre'")
    for w in mm_validate(md):
        if "commencer par" not in w:
            rep.warn(where, w)
    if BAD_EMOJI_RE.search(md):
        rep.err(where, "pseudo-emoji cassé détecté (ex. 🯤) — utiliser un emoji de la légende")
    check_classes(where, c.get("reponse", ""), rep)
    md_html = html.escape(md, quote=False).replace("\n", "<br>")
    med, imgs = {"noeuds": {}, "branches": {}}, []
    for it in c.get("images_noeuds", []):          # portrait à côté du nœud dont le texte contient « cle »
        f = media(it, rep, where)
        if f:
            med["noeuds"][it["cle"]] = f
            imgs.append(f)
    for it in c.get("images_branches", []):        # image importée ou schéma (spec visuel) sous la branche
        if it.get("visuel"):
            svg = visual(where, it["visuel"], rep, used_geo)
            if svg:
                med["branches"][it["branche"]] = {"svg": svg}
        else:
            f = media(it, rep, where)
            if f:
                med["branches"][it["branche"]] = {"img": f}
                imgs.append(f)
    labels = [l for l in re.findall(r"^\s*(?:##|-+)\s+(.*)$", md, flags=re.M)]
    for k in list(med["noeuds"]) + list(med["branches"]):
        if not any(k.lower() in l.lower() for l in labels):
            rep.warn(where, f"image : aucun nœud ne contient « {k} »")
    medias = ("".join(f'<img src="{html.escape(x)}" alt="">' for x in imgs)
              + f'<span class="mm-json">{html.escape(json.dumps(med, ensure_ascii=False), quote=False)}</span>'
              if imgs or med["branches"] else "")
    vals = [c.get("question", ""), md_html, c.get("reponse", ""), c.get("source_url", ""),
            c.get("source_titre", "")] + branch_flags(md) + [medias]  # B1…B6 : une carte « Branche » par branche non vide
    return NOM_MINDMAP, vals, guid("geo-v10-mm", c.get("question", ""))


def prep_chinois(c, i, rep, used_geo):
    where = f"carte {i} (chinois) « {c.get('hanzi', '?')} »"
    for k in ("hanzi", "pinyin", "sens"):
        if not (c.get(k) or "").strip():
            rep.err(where, f"champ obligatoire vide : {k}")
    for k in ("pinyin", "exemple_pinyin"):
        v = c.get(k, "")
        if v and " " not in v.strip() and len([ch for ch in c.get("hanzi" if k == "pinyin" else "exemple", "") if "\u3400" <= ch <= "\u9fff"]) > 1:
            rep.warn(where, f"{k} : sépare les syllabes par des espaces (« xué xí ») pour colorer les tons")
    vals = [c.get("hanzi", ""), c.get("pinyin", ""), c.get("sens", ""), c.get("exemple", ""),
            c.get("exemple_pinyin", ""), c.get("exemple_sens", ""), c.get("audio", ""),
            c.get("audio_exemple", ""), c.get("note", ""), "1" if c.get("ecriture") else ""]
    return NOM_CHINOIS, vals, guid("langues-v10-zh", c.get("hanzi", ""))


def prep_langue(c, i, rep, used_geo):
    cle = c.get("langue", "")
    where = f"carte {i} (langue) « {c.get('mot', '?')} »"
    if cle not in LANGUES:
        rep.err(where, f"langue inconnue « {cle} » ({', '.join(LANGUES)})")
        cle = next(iter(LANGUES))
    for k in ("mot", "sens"):
        if not (c.get(k) or "").strip():
            rep.err(where, f"champ obligatoire vide : {k}")
    vals = [c.get("mot", ""), c.get("transcription", ""), c.get("sens", ""), c.get("exemple", ""),
            c.get("exemple_transcription", ""), c.get("exemple_sens", ""), c.get("audio", ""),
            c.get("audio_exemple", ""), c.get("note", ""), "1" if c.get("production") else ""]
    return nom_modele_langue(cle), vals, guid(f"langues-v10-{cle}", c.get("mot", ""))


PREPS = {"basique": prep_basique, "trous": prep_trous, "citation": prep_citation, "mindmap": prep_mindmap, "chinois": prep_chinois,
         "langue": prep_langue}
FIELDS_BY_MODEL = {NOM_BASIQUE: BASIQUE_FIELDS, NOM_TROUS: TROUS_FIELDS, NOM_MINDMAP: MINDMAP_FIELDS,
                   NOM_CHINOIS: CHINOIS_FIELDS, **{nom_modele_langue(k): LANGUE_FIELDS for k in LANGUES}}
TEMPLATES = {
    NOM_BASIQUE: [("Carte", CARTE_FRONT, CARTE_BACK), ("Saisie", SAISIE_FRONT, SAISIE_BACK), ("Visage", VISAGE_FRONT, VISAGE_BACK)],
    NOM_TROUS: [("Trous", TROUS_FRONT, TROUS_BACK)],
    NOM_MINDMAP: [(t["name"], t["qfmt"], t["afmt"]) for t in MINDMAP_TEMPLATES],
    NOM_CHINOIS: [(t["name"], t["qfmt"], t["afmt"]) for t in CHINOIS_TEMPLATES],
    **{nom_modele_langue(k): [(t["name"], t["qfmt"], t["afmt"]) for t in templates_langue(k)] for k in LANGUES},
}


# ════════════════════════════════════════════════════════════════════
# APERÇU HTML (simule le rendu Anki)
# ════════════════════════════════════════════════════════════════════
def anki_compare(typed, expected):
    """Imite le rendu de la comparaison {{type:…}} d'Anki au verso (pour l'aperçu)."""
    e, t = html.escape(expected), html.escape(typed)
    if typed == expected:
        return f'<code id="typeans"><span class="typeGood">{e}</span></code>'
    return (f'<code id="typeans"><span class="typeBad">{t}</span><br><span id="typearrow">&darr;</span><br>'
            f'<span class="typeMissed">{e}</span></code>')


def render_tpl(tpl, f, front="", typed=None):
    out = tpl.replace("{{FrontSide}}", front)
    if typed is not None:
        out = re.sub(r"\{\{type:(\w+)\}\}", lambda m: anki_compare(typed, f.get(m.group(1), "")), out)
    for _ in range(3):
        out = re.sub(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", lambda m: m.group(2) if f.get(m.group(1), "").strip() else "", out, flags=re.S)
        out = re.sub(r"\{\{\^(\w+)\}\}(.*?)\{\{/\1\}\}", lambda m: "" if f.get(m.group(1), "").strip() else m.group(2), out, flags=re.S)
    out = re.sub(r"\{\{cloze:(\w+)\}\}", lambda m: f.get(m.group(1), ""), out)
    out = re.sub(r"\{\{hint:(\w+)\}\}", lambda m: f'<a class="hint" href="#" onclick="this.style.display=\'none\';this.nextSibling.style.display=\'block\';return false;">{m.group(1)}</a><div class="hint" style="display:none">{f.get(m.group(1), "")}</div>', out)
    out = re.sub(r"\{\{tts [^:}]+:(\w+)\}\}", '<span class="tts" title="voix de synthèse Anki">▶︎ 🔊</span>', out)
    out = re.sub(r"\{\{type:(\w+)\}\}", '<input id="typeans" placeholder="(zone de saisie Anki)">', out)
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: f.get(m.group(1), ""), out)
    out = re.sub(r"\[anki:tts[^\]]*\].*?\[/anki:tts\]", '<span class="tts" title="voix de synthèse Anki">▶︎ 🔊</span>', out)
    return re.sub(r"\[sound:[^\]]+\]", '<span class="tts" title="audio">▶︎ 🔊</span>', out)


def preview(items, outdir, used_geo):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for g in used_geo:
        src = HERE / "assets" / f"_geo_{g}.svg"
        if src.exists():
            shutil.copy(src, outdir / src.name)
    pages = []
    for idx, (mname, vals) in enumerate(items, 1):
        f = dict(zip(FIELDS_BY_MODEL[mname], vals))
        for tname, qf, af in TEMPLATES[mname]:
            if mname == NOM_TROUS:
                front = render_tpl(qf, dict(f, Texte=re.sub(r"\{\{c\d+::(.*?)(?:::(.*?))?\}\}", lambda m: '<span class="cloze">[' + (m.group(2) or '…') + ']</span>', f["Texte"])))
                back = render_tpl(af, dict(f, Texte=re.sub(r"\{\{c\d+::(.*?)(::.*?)?\}\}", r'<span class="cloze">\1</span>', f["Texte"])))
            else:
                front = render_tpl(qf, f)
                typed = None
                if tname == "Saisie" and f.get("SaisieVariantes"):  # aperçu : on simule la saisie d'une variante
                    typed = f["SaisieVariantes"].split("|")[-1].lower()
                back = render_tpl(af, f, front, typed=typed)
            if not re.sub(r"<script.*?</script>", "", front, flags=re.S).strip():
                continue  # carte non générée par Anki (Saisie vide, branche B<k> vide…)
            for mode in ("clair", "sombre"):
                cls = "card" + (" nightMode night_mode" if mode == "sombre" else "")
                name = f"{idx:02d}_{tname.replace(' ', '')}_{mode}.html"
                css = CSS + (MINDMAP_CSS if mname == NOM_MINDMAP else "") + (CHINOIS_CSS if mname == NOM_CHINOIS else "") + (LANGUE_CSS if mname.startswith("Ficher — ") and mname not in (NOM_TROUS, NOM_MINDMAP) and mname != NOM_CHINOIS else "")
                (outdir / name).write_text(
                    f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                    f'<style>{css}</style></head><body class="{cls}">{front}'
                    f'<div style="margin:28px 0 20px;border-top:3px dashed #888;text-align:center;font:11px sans-serif;opacity:.6">▼ verso</div>{back}</body></html>',
                    encoding="utf-8")
                pages.append(name)
    return pages


# ════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description="JSON de cartes Ficher → .apkg / charge MCP")
    ap.add_argument("json")
    ap.add_argument("-o", "--output", help="fichier .apkg à écrire")
    ap.add_argument("--mcp", help="écrit un JSON prêt pour l'outil addNotes du connecteur Anki")
    ap.add_argument("--preview", help="dossier d'aperçu HTML (clair + sombre)")
    ap.add_argument("--tous-fonds", action="store_true", help="embarque les 22 fonds de carte (paquet de démarrage)")
    ap.add_argument("--force", action="store_true", help="générer malgré les erreurs")
    a = ap.parse_args()
    if not (a.output or a.mcp or a.preview):
        a.output = "cartes.apkg"

    data = json.loads(Path(a.json).read_text(encoding="utf-8"))
    JSON_DIR[0] = str(Path(a.json).resolve().parent)
    default_deck = data.get("deck", "Ficher::Démarrage")
    gtags = data.get("tags", [])
    rep, used_geo, seen, items = Report(), set(), {}, []
    extra_media = set()
    for m in data.get("medias", []):  # fichiers joints (audio [sound:…], images) posés à côté du JSON
        mp = (Path(a.json).parent / m)
        if mp.exists():
            extra_media.add(str(mp.resolve()))
        else:
            rep.err("medias", f"fichier introuvable : {mp}")
    cartes = []
    for i, c in enumerate(data.get("cartes", []), 1):  # occlusion : une note → une carte par zone
        if c.get("modele") == "occlusion":
            try:
                cartes += [(i, x) for x in occlusion.deplier(c, i, Path(a.json).parent, extra_media)]
            except (occlusion.OcclusionError, KeyError, StopIteration) as e:
                rep.err(f"carte {i} (occlusion) « {c.get('ancre', '?')[:40]} »", str(e) or "cible inconnue")
        else:
            cartes.append((i, c))
    for i, c in cartes:
        kind = c.get("modele", "basique")
        if kind not in PREPS:
            rep.err(f"carte {i}", f"modele inconnu « {kind} » (basique, trous, mindmap, chinois, langue, occlusion)")
            continue
        mname, vals, g = PREPS[kind](c, i, rep, used_geo)
        if g in seen:
            rep.err(f"carte {i}", f"même ancre que la carte {seen[g]} (doublon)")
        seen[g] = i
        tags = [t.replace(" ", "_") for t in gtags + c.get("tags", [])]
        items.append((mname, vals, g, tags, c.get("deck") or default_deck))

    extra_media |= PORTRAIT_MEDIA
    for w in rep.warnings:
        print(w)
    for e in rep.errors:
        print(e)
    if rep.errors and not a.force:
        sys.exit(f"\n{len(rep.errors)} erreur(s) — corrige le JSON (ou --force). Rien n'a été généré.")

    if a.output:
        if genanki is None:
            sys.exit("genanki manquant : pip install genanki (--break-system-packages si besoin)")
        models = make_models()
        by_name = {m.name: m for m in models.values()}
        decks = {}
        for mname, vals, g, tags, dname in items:
            d = decks.setdefault(dname, genanki.Deck(int(guid("deck", dname).encode().hex()[:12], 16) % (1 << 30) + (1 << 30), dname))
            d.add_note(genanki.Note(model=by_name[mname], fields=vals, guid=g, tags=tags))
        geo_dir = HERE / "assets"
        wanted = sorted(geo_dir.glob("_geo_*.svg")) if a.tous_fonds else [geo_dir / f"_geo_{x}.svg" for x in sorted(used_geo)]
        media = [str(p) for p in wanted if p.exists()] + sorted(extra_media)
        if used_geo and not media:
            print("ℹ fonds de carte absents ici : OK s'ils sont déjà dans ta collection (paquet de démarrage importé).")
        genanki.Package(list(decks.values()), media_files=media).write_to_file(a.output)
        print(f"\n✓ {a.output} — {len(items)} note(s), {len(media)} média(s) (fonds de carte, images), paquet(s) : {', '.join(decks)}")

    if a.mcp:
        batches = {}
        for m, v, g, t, d in items:  # addNotes : un appel par couple (paquet, type de note)
            batches.setdefault((d, m), []).append({"fields": dict(zip(FIELDS_BY_MODEL[m], v)), "tags": t})
        payload = [{"deckName": d, "modelName": m, "notes": n} for (d, m), n in batches.items()]
        Path(a.mcp).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ {a.mcp} — {len(items)} note(s) en {len(payload)} appel(s) addNotes "
              f"({len(json.dumps(payload, ensure_ascii=False)) // 1000} Ko ≈ tokens à transmettre)")

    if a.preview:
        pages = preview([(m, v) for m, v, *_ in items], a.preview, used_geo)
        for m in extra_media:
            shutil.copy(m, Path(a.preview) / Path(m).name)
        print(f"✓ aperçu : {len(pages)} page(s) dans {a.preview}/")


if __name__ == "__main__":
    main()

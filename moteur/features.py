"""
features.py — 4 nouveautés testées pour le moteur V10 → V11.

  🎯 Estimation       : curseur au recto (« Combien ? »), au verso écart en % (ou en facteur ×N), verdict.
  🧬 Décomposition    : sigle ou terme décomposé en segments colorés (AUKUS = A·UK·US, Real + Politik).
  ⌨️ Saisie tolérante : variantes acceptées (« ; » et parties optionnelles « ( ) ») + bouton
                        « Lettre suivante » qui corrige la saisie et ajoute une lettre (façon Memrise).
  👆 Une par une      : au verso, la réponse puis chaque puce se dévoilent dans l'ordre, sans indice
                        de longueur ; même chose pour les trous multiples d'une carte à trous.

Tout est en JavaScript ES5 inline, sans réseau, idempotent (Anki peut rejouer les scripts).
Le choix du mode (normal / test / une par une) est mémorisé par appareil (localStorage « v10-test »).
"""
import html
import re
import unicodedata

from visuels import PALETTE


class FeatureError(ValueError):
    pass


def _plain(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


# ════════════════════════════════════════════════════════════════════
# 🎯 ESTIMATION
# ════════════════════════════════════════════════════════════════════
def estimation_html(spec, cle):
    """spec : {"valeur", "min", "max", "[unite]", "[echelle]": "lin|log", "[tolerance]": %, "[decimales]"}"""
    if not isinstance(spec, dict):
        raise FeatureError("estimation : un objet {\"valeur\", \"min\", \"max\", …} est attendu")
    try:
        v, lo, hi = float(spec["valeur"]), float(spec["min"]), float(spec["max"])
    except (KeyError, TypeError, ValueError):
        raise FeatureError("estimation : \"valeur\", \"min\" et \"max\" numériques obligatoires")
    log = spec.get("echelle", "lin") == "log"
    if spec.get("echelle", "lin") not in ("lin", "log"):
        raise FeatureError("estimation : \"echelle\" = lin ou log")
    if not lo < v < hi:
        raise FeatureError(f"estimation : la valeur {v:g} doit être strictement entre min {lo:g} et max {hi:g}")
    if log and lo <= 0:
        raise FeatureError("estimation : en échelle log, min doit être > 0")
    if not log and hi / max(abs(lo), 1e-9) > 200 and lo > 0:
        raise FeatureError("estimation : plage très large en échelle linéaire → mets \"echelle\": \"log\"")
    tol = float(spec.get("tolerance", 15))
    dec = int(spec.get("decimales", 0 if abs(v) >= 10 else 1))
    attrs = dict(v=f"{v:g}", min=f"{lo:g}", max=f"{hi:g}", log="1" if log else "0", tol=f"{tol:g}", dec=str(dec),
                 unit=spec.get("unite", ""), key=_plain(re.sub(r"<[^>]+>", "", cle))[:60])
    return '<div class="est" ' + " ".join(f'data-{k}="{html.escape(str(x), quote=True)}"' for k, x in attrs.items()) + "></div>"


ESTIMATION_JS = r"""<script>(function(){function run(){
var back=!!(document.querySelector('.v10.verso')||document.getElementById('answer'));
function fmt(x,d){try{return x.toLocaleString('fr-FR',{maximumFractionDigits:d});}catch(e){return String(Math.round(x*Math.pow(10,d))/Math.pow(10,d));}}
function mk(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;}
var bs=document.querySelectorAll('.est:not([data-ok])');
for(var i=0;i<bs.length;i++)(function(b){b.setAttribute('data-ok','1');
 var v=+b.getAttribute('data-v'),lo=+b.getAttribute('data-min'),hi=+b.getAttribute('data-max'),lg=b.getAttribute('data-log')==='1',
  u=b.getAttribute('data-unit')||'',tol=+(b.getAttribute('data-tol')||15),dec=+(b.getAttribute('data-dec')||0),key='v11est:'+b.getAttribute('data-key');
 function X(t){return lg?Math.exp(Math.log(lo)+t*(Math.log(hi)-Math.log(lo))):lo+t*(hi-lo);}
 function T(x){var t=lg?(Math.log(x)-Math.log(lo))/(Math.log(hi)-Math.log(lo)):(x-lo)/(hi-lo);return Math.max(0,Math.min(1,t));}
 function rnd(x){if(lg){var m=Math.pow(10,Math.floor(Math.log(x)/Math.LN10)-1);return Math.round(x/m)*m;}var p=Math.pow(10,dec);return Math.round(x*p)/p;}
 function U(x){return fmt(x,dec)+(u?' '+u:'');}
 function put(g){window.__v11est=window.__v11est||{};window.__v11est[key]=g;try{sessionStorage.setItem(key,String(g));}catch(e){}try{localStorage.setItem(key,String(g));}catch(e){}}
 function get(){var g=window.__v11est&&window.__v11est[key];if(g!=null)return +g;
  try{var s=sessionStorage.getItem(key);if(s!=null&&s!=='')return +s;}catch(e){}try{var l=localStorage.getItem(key);if(l!=null&&l!=='')return +l;}catch(e){}return null;}
 function clear(){if(window.__v11est)delete window.__v11est[key];try{sessionStorage.removeItem(key);}catch(e){}try{localStorage.removeItem(key);}catch(e){}}
 b.appendChild(mk('div','est-lab','🎯 Ton estimation'));
 if(!back){clear();
  var out=mk('div','est-val','glisse le curseur'),r=mk('input','est-range');r.type='range';r.min=0;r.max=1000;r.step=1;r.value=500;
  var ends=mk('div','est-ends');ends.appendChild(mk('span',null,U(lo)));ends.appendChild(mk('span',null,lg?'échelle ×10':''));ends.appendChild(mk('span',null,U(hi)));
  b.appendChild(out);b.appendChild(r);b.appendChild(ends);
  var on=function(){var g=rnd(X(r.value/1000));out.textContent=U(g);out.className='est-val set';put(g);};
  ['input','change','pointerup','touchend','click'].forEach(function(ev){r.addEventListener(ev,on);});
  r.addEventListener('keydown',function(e){e.stopPropagation();});
  return;}
 /* verso : piste avec bande de tolérance, marqueurs « toi » et « réel », écart et verdict */
 var g=get(),trk=mk('div','est-trk'),band=mk('i','est-band'),mv=mk('i','est-m est-v'),lbv=mk('span','est-tag est-tv',U(v));
 var bl=lg?v/(1+tol/100):v*(1-tol/100),bh=lg?v*(1+tol/100):v*(1+tol/100);
 band.style.left=(T(bl)*100)+'%';band.style.width=((T(bh)-T(bl))*100)+'%';mv.style.left=(T(v)*100)+'%';lbv.style.left=(T(v)*100)+'%';
 trk.appendChild(band);trk.appendChild(mv);trk.appendChild(lbv);
 var res=mk('div','est-res');
 if(g!=null&&!isNaN(g)){var mg=mk('i','est-m est-g'),lbg=mk('span','est-tag est-tg','toi');mg.style.left=(T(g)*100)+'%';lbg.style.left=(T(g)*100)+'%';
  trk.appendChild(mg);trk.appendChild(lbg);
  var e=lg?Math.max(g,v)/Math.min(g,v)-1:Math.abs(g-v)/Math.abs(v),sens=g>v?'surestimé':'sous-estimé',ecart;
  if(lg&&e>=1)ecart='×'+fmt(e+1,1)+' ('+sens+')';else{var p=(g-v)/Math.abs(v)*100;ecart=(p>0?'+':p<0?'−':'')+fmt(Math.abs(p),0)+' % ('+(p===0?'exact':sens)+')';}
  var verd=e*100<=tol?['ok','🎯 Dans le mille']:(lg?e<=1:e*100<=3*tol)?['moy','👍 Bon ordre de grandeur']:['ko','❌ Loin du compte'];
  var l1=mk('div','est-line');l1.appendChild(mk('span','est-verd '+verd[0],verd[1]));
  var l2=mk('div','est-line2');l2.appendChild(document.createTextNode('Toi : '+U(g)+' · Réel : '));l2.appendChild(mk('b',null,U(v)));
  l2.appendChild(document.createTextNode(' · écart '+ecart));res.appendChild(l1);res.appendChild(l2);}
 else{var l0=mk('div','est-line2');l0.appendChild(document.createTextNode('Pas d’estimation cette fois · Réel : '));l0.appendChild(mk('b',null,U(v)));res.appendChild(l0);}
 var ends2=mk('div','est-ends');ends2.appendChild(mk('span',null,U(lo)));ends2.appendChild(mk('span'));ends2.appendChild(mk('span',null,U(hi)));
 b.appendChild(res);b.appendChild(trk);b.appendChild(ends2);
})(bs[i]);}
/* le verso doit être entièrement chargé pour savoir de quel côté on est */
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else setTimeout(run,0);})();</script>"""


# ════════════════════════════════════════════════════════════════════
# 🧬 DÉCOMPOSITION (sigles, termes composés, étymologie)
# ════════════════════════════════════════════════════════════════════
ROTATION = ["act", "eco", "env", "instr", "pol", "risk", "conc", "res"]


def _surligne_initiales(lettres, sens):
    """Met en gras dans « sens » les lettres du segment, prises en début de mots successifs (sigles)."""
    mots = list(re.finditer(r"[\wÀ-ÿ'’-]+", sens))
    cible, j, pos = [c for c in lettres if c.isalnum()], 0, []
    for m in mots:
        if j < len(cible) and _plain(m.group(0)[0]) == _plain(cible[j]):
            pos.append(m.start())
            j += 1
    if j != len(cible) or not cible:
        return html.escape(sens)
    out, last = [], 0
    for p in pos:
        out.append(html.escape(sens[last:p]) + f"<u>{html.escape(sens[p])}</u>")
        last = p + 1
    return "".join(out) + html.escape(sens[last:])


def decomposition_html(spec):
    """spec : {"terme": "AUKUS", "parties": [["A","Australia"], {"lettres":"UK","sens":"United Kingdom","cat":"act"}], "[note]"}
    Retourne (html, avertissement ou None)."""
    if not isinstance(spec, dict) or not spec.get("parties"):
        raise FeatureError("decomposition : {\"terme\", \"parties\": [[lettres, sens], …]} attendu")
    parts = []
    for k, p in enumerate(spec["parties"]):
        if isinstance(p, (list, tuple)):
            p = {"lettres": p[0], "sens": p[1] if len(p) > 1 else "", "cat": p[2] if len(p) > 2 else None}
        if not p.get("lettres"):
            raise FeatureError("decomposition : chaque partie a des \"lettres\"")
        cat = p.get("cat") or ROTATION[k % len(ROTATION)]
        if cat not in PALETTE:
            raise FeatureError(f"decomposition : catégorie inconnue « {cat} »")
        parts.append((p["lettres"], p.get("sens", ""), cat, p.get("langue", "")))
    if len(parts) < 2:
        raise FeatureError("decomposition : au moins 2 parties")
    terme = spec.get("terme", "")
    warn = None
    if terme and re.sub(r"[^0-9a-z]", "", _plain(terme)) != re.sub(r"[^0-9a-z]", "", _plain("".join(p[0] for p in parts))):
        warn = f"decomposition : les segments ne recomposent pas « {terme} »"
    sigle = all(p[0].isupper() and len(p[0]) <= 4 for p in parts)
    segs = []
    for lettres, sens, cat, langue in parts:
        s = _surligne_initiales(lettres, sens) if sigle else html.escape(sens)
        lg = f' <i class="dc-lang">({html.escape(langue)})</i>' if langue else ""
        segs.append(f'<span class="dc-seg {cat}"><b class="dc-l">{html.escape(lettres)}</b>'
                    f'<span class="dc-s">{s}{lg}</span></span>')
    sep = '<span class="dc-plus">+</span>' if not sigle else ""
    note = f'<div class="dc-note">{html.escape(spec["note"])}</div>' if spec.get("note") else ""
    return (f'<div class="dc-tag">🧬 {"Sigle" if sigle else "Décomposition"}</div>'
            f'<div class="dc-row">{sep.join(segs)}</div>{note}'), warn


# ════════════════════════════════════════════════════════════════════
# ⌨️ SAISIE TOLÉRANTE + INDICE LETTRE PAR LETTRE
# ════════════════════════════════════════════════════════════════════
def _expand(alt):
    """« (Recep Tayyip) Erdoğan » → {« Erdoğan », « Recep Tayyip Erdoğan »}."""
    m = re.search(r"\(([^()]*)\)", alt)
    if not m:
        return {re.sub(r"\s+", " ", alt).strip()}
    avec = alt[:m.start()] + m.group(1) + alt[m.end():]
    sans = alt[:m.start()] + alt[m.end():]
    return _expand(avec) | _expand(sans)


def saisie_variantes(saisie):
    """Retourne (forme canonique à taper, liste de toutes les variantes acceptées)."""
    alts = [a for a in (x.strip() for x in saisie.split(";")) if a]
    if not alts:
        return "", []
    canon = re.sub(r"\s+", " ", re.sub(r"\([^()]*\)", "", alts[0])).strip()
    var = [canon]
    for a in alts:
        for x in sorted(_expand(a), key=len):
            if x and x not in var:
                var.append(x)
    return canon, var


SAISIE_FRONT_JS = r"""<script>(function(){
var k=document.querySelector('.sx-k');if(!k||k.getAttribute('data-ok'))return;k.setAttribute('data-ok','1');
var canon=(k.textContent||'').replace(/\s+/g,' ').trim(),key='v11sx:'+canon.length+':'+canon.charCodeAt(0),n=0;if(!canon)return;
try{sessionStorage.setItem(key,'0');}catch(e){}window.__v11sx=0;
function low(s){return s.toLowerCase();}
var zone=document.querySelector('.sx-zone'),btn=document.createElement('button'),pat=document.createElement('span');
btn.type='button';btn.className='mt-btn sx-btn';btn.textContent='💡 Lettre suivante';pat.className='sx-pat';
zone.appendChild(btn);zone.appendChild(pat);
btn.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();
 var inp=document.getElementById('typeans'),cur=inp&&inp.value!=null?inp.value:canon.slice(0,n),i=0;
 while(i<cur.length&&i<canon.length&&low(cur[i])===low(canon[i]))i++;
 var j=Math.min(canon.length,i+1);while(j<canon.length&&canon[j-1]===' ')j++;
 n++;window.__v11sx=n;try{sessionStorage.setItem(key,String(n));}catch(e2){}
 if(inp&&inp.tagName==='INPUT'){inp.value=canon.slice(0,j);try{inp.focus();inp.setSelectionRange(j,j);}catch(e3){}}
 else pat.textContent=canon.slice(0,j)+(j<canon.length?'…':'');
 btn.textContent='💡 Lettre suivante ('+n+')';if(j>=canon.length)btn.disabled=true;});
})();</script>"""

SAISIE_BACK_JS = r"""<script>(function(){
var vs=document.querySelector('.sx-var');if(!vs||vs.getAttribute('data-ok'))return;vs.setAttribute('data-ok','1');
var vars=(vs.textContent||'').split('|').map(function(s){return s.replace(/\s+/g,' ').trim();}).filter(Boolean),canon=vars[0]||'';
var key='v11sx:'+canon.length+':'+canon.charCodeAt(0),n=window.__v11sx;if(n==null){try{n=+(sessionStorage.getItem(key)||0);}catch(e){n=0;}}
function norm(s){return s.replace(/\s+/g,' ').trim().toLowerCase();}
function flat(s){try{return norm(s).normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[’']/g,"'").replace(/ı/g,'i');}catch(e){return norm(s);}}
var code=document.getElementById('typeans'),typed='',exact=false;
if(code&&code.tagName!=='INPUT'){var kids=code.childNodes,seenBr=false,good=0,bad=0;
 for(var i=0;i<kids.length;i++){var c=kids[i];if(c.nodeName==='BR'){seenBr=true;break;}
  if(c.nodeType===1&&/type(Good|Bad|Pass)/.test(c.className)){typed+=c.textContent;if(/typeBad/.test(c.className))bad++;else good++;}
  else if(c.nodeType===3)typed+=c.textContent;}
 exact=!seenBr&&bad===0&&typed.length>0;}
var box=document.querySelector('.sx-verdict');if(!box)return;var msg='',cls='';
if(typed&&!exact){var nt=norm(typed),ft=flat(typed),hit=null,near=null;
 for(var j=0;j<vars.length;j++){if(norm(vars[j])===nt){hit=vars[j];break;}if(flat(vars[j])===ft&&!near)near=vars[j];}
 if(hit){cls='ok';msg='✓ Accepté'+(hit!==canon?' — variante admise de « '+canon+' »':' (majuscules ignorées)');code.classList.add('sx-dim');}
 else if(near){cls='moy';msg='≈ Presque : seuls les accents ou signes diffèrent (« '+near+' »)';}}
if(n>0){msg+=(msg?' · ':'')+'💡 '+n+' lettre'+(n>1?'s':'')+' d’indice → ne note pas « Facile »';if(!cls)cls='info';}
if(vars.length>1&&!msg){msg='Variantes admises : '+vars.slice(1).join(' · ');cls='info';}
if(msg){box.textContent=msg;box.className='sx-verdict '+cls;}
})();</script>"""


# ════════════════════════════════════════════════════════════════════
# 🙈 MODE TEST + 👆 UNE PAR UNE (remplace MODE_TEST_JS du V10)
# ════════════════════════════════════════════════════════════════════
# mode 0 = normal, 1 = test (tout flouté, toucher pour révéler), 2 = une par une (ordre imposé)
MODES_JS = r"""<script>(function(){
var v=document.querySelector('.v10.verso')||document.querySelector('.v10.trous-v');if(!v||v.querySelector('.mt-bar'))return;
var trous=v.classList.contains('trous-v');
var seq=[].slice.call(v.querySelectorAll(trous?'.cloze-txt .cloze':'.quand,.rep,.decomp,ul.puces>li'));
var reste=trous?[].slice.call(v.querySelectorAll('.extra')):[].slice.call(v.querySelectorAll('.portraits,.visuel,.piege,.lien,.memo,.anecdote'));
if(trous&&seq.length<2)return;if(!seq.length)return;
var tous=seq.concat(reste);tous.forEach(function(b){b.classList.add('mt-bloc');});
var ROND='①②③④⑤⑥⑦⑧⑨';var nIdee=0;
seq.forEach(function(b,i){b.classList.add('op-seq');var lab;
 if(b.classList.contains('quand'))lab=b.querySelector('.q-aut')?'Date et auteur':'Date';else if(b.classList.contains('rep'))lab='Réponse centrale';else if(b.classList.contains('decomp'))lab='Décomposition';
 else if(trous)lab=(ROND[i]||(i+1))+' Trou';else{nIdee++;lab=(ROND[nIdee-1]||nIdee)+' Idée '+nIdee;}
 b.setAttribute('data-op',lab);});
var mode=0;try{mode=+(localStorage.getItem('v10-test')||0);}catch(e){}if(trous&&mode===1)mode=2;
function mk(t,c,x){var e=document.createElement(t);e.className=c;if(t==='button')e.type='button';if(x)e.textContent=x;return e;}
var bar=mk('div','mt-bar'),bt=mk('button','mt-btn','Mode test'),bo=mk('button','mt-btn','Une par une'),nx=mk('button','mt-btn mt-next','Suivante'),
 all=mk('button','mt-btn mt-all','Tout afficher'),aide=mk('span','mt-aide');
if(!trous)bar.appendChild(bt);bar.appendChild(bo);bar.appendChild(nx);bar.appendChild(all);bar.appendChild(aide);var ct0=v.querySelector('.cloze-txt');if(trous&&ct0)ct0.parentNode.insertBefore(bar,ct0.nextSibling);else v.insertBefore(bar,v.firstChild);
function cachés(l){return l.filter(function(b){return !b.classList.contains('mt-vu');});}
function suivant(){var c=cachés(seq);if(c.length){vu(c[0]);}if(!cachés(seq).length)reste.forEach(function(b){b.classList.add('mt-vu');});maj();}
function vu(b){b.classList.add('mt-vu');b.classList.remove('op-anim');void b.offsetWidth;b.classList.add('op-anim');}
function maj(){v.classList.toggle('mt-on',mode===1);v.classList.toggle('op-on',mode===2);bt.classList.toggle('on',mode===1);bo.classList.toggle('on',mode===2);
 var cs=cachés(seq),ct=cachés(tous);seq.forEach(function(b){b.classList.remove('op-next');});if(mode===2&&cs.length)cs[0].classList.add('op-next');
 nx.style.display=mode===2&&cs.length?'':'none';all.style.display=mode&&ct.length?'':'none';
 aide.textContent=mode===1?(ct.length?'Touche un bloc flou pour le révéler ('+ct.length+')':'Tout est révélé'):
  mode===2?(cs.length?'Rappelle-toi le n° '+(seq.length-cs.length+1)+' / '+seq.length+', puis touche':'✓ Tout est révélé'):'';}
function set(m){mode=(mode===m)?0:m;try{localStorage.setItem('v10-test',String(mode));}catch(e){}tous.forEach(function(b){b.classList.remove('mt-vu');});maj();}
bt.addEventListener('click',function(e){e.stopPropagation();set(1);});bo.addEventListener('click',function(e){e.stopPropagation();set(2);});
nx.addEventListener('click',function(e){e.stopPropagation();suivant();});
all.addEventListener('click',function(e){e.stopPropagation();tous.forEach(function(b){b.classList.add('mt-vu');});maj();});
v.addEventListener('click',function(e){if(!mode||!e.target.closest)return;var b=e.target.closest('.mt-bloc');if(!b||b.classList.contains('mt-vu'))return;
 e.preventDefault();e.stopPropagation();if(mode===1){vu(b);maj();}else suivant();},true);
maj();})();</script>"""


def css():
    cats = "\n".join(f".dc-seg.{k} .dc-l,.dc-seg.{k} .dc-s u{{color:var(--{k}-k);}}" for k in PALETTE)
    return """
/* ═══ V11 : estimation ═══ */
.est { max-width:520px; margin:14px auto 4px; padding:12px 14px 10px; border:1px solid var(--line); border-radius:12px; background:var(--chip); text-align:center; }
.est-lab { font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.est-val { font-size:26px; font-weight:750; margin:2px 0 4px; color:var(--muted); font-variant-numeric:tabular-nums; }
.est-val.set { color:var(--act-k); }
.est-range { width:100%; margin:4px 0 0; accent-color:var(--act-k); height:28px; }
.est-ends { display:flex; justify-content:space-between; font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; }
.est-res { margin:4px 0 12px; }
.est-verd { display:inline-block; font-weight:750; font-size:17px; padding:3px 12px; border-radius:999px; }
.est-verd.ok { background:rgba(46,125,50,.14); color:var(--env-k); } .est-verd.moy { background:rgba(230,81,0,.13); color:var(--instr-k); }
.est-verd.ko { background:rgba(198,40,40,.12); color:var(--risk-k); }
.est-line2 { font-size:15px; margin-top:6px; font-variant-numeric:tabular-nums; }
.est-trk { position:relative; height:8px; margin:26px 6px 4px; border-radius:4px; background:var(--line); }
.est-band { position:absolute; top:-3px; height:14px; border-radius:7px; background:rgba(46,125,50,.28); }
.est-m { position:absolute; top:50%; width:14px; height:14px; margin:-7px 0 0 -7px; border-radius:50%; border:2px solid var(--bg); }
.est-v { background:var(--env-k); } .est-g { background:var(--act-k); }
.est-tag { position:absolute; top:-24px; transform:translateX(-50%); font-size:12px; font-weight:700; white-space:nowrap; }
.est-tv { color:var(--env-k); top:14px; } .est-tg { color:var(--act-k); }
/* ═══ V11 : décomposition ═══ */
.decomp { margin:10px 0 8px; padding:8px 12px 10px; border-radius:10px; border:1px solid var(--line); background:var(--chip); }
.dc-tag { font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin-bottom:4px; }
.dc-row { display:flex; flex-wrap:wrap; justify-content:center; align-items:flex-start; gap:6px 18px; }
.dc-seg { display:flex; flex-direction:column; align-items:center; text-align:center; min-width:44px; max-width:170px; }
.dc-l { font-size:30px; font-weight:800; letter-spacing:.03em; line-height:1.1; }
.dc-s { font-size:14px; line-height:1.3; margin-top:3px; }
.dc-s u { text-decoration:none; font-weight:800; }
.dc-lang { color:var(--muted); font-size:12.5px; }
.dc-plus { font-size:22px; color:var(--muted); margin-top:3px; }
.dc-note { text-align:center; font-size:13px; font-style:italic; color:var(--muted); margin-top:6px; }
""" + cats + """
/* ═══ V11 : date (et auteur) retrouvés au verso ═══ */
.q-pill { display:inline-block; margin-top:8px; padding:2px 10px; border-radius:999px; font-size:12.5px; color:var(--muted); border:1px dashed var(--line); }
.quand { display:flex; flex-direction:column; align-items:center; text-align:center; gap:2px; margin:0 0 10px; }
.q-date { font-size:22px; font-weight:800; color:var(--date-k); font-variant-numeric:tabular-nums; }
.q-aut { font-size:17px; font-weight:700; color:var(--act-k); }
/* puces : bloc centré dans la carte, texte aligné à gauche (lecture) */
.v10.verso > .rep { text-align:center; }
.v10.verso .portraits { justify-content:center; }
.v10.verso ul.puces { display:table; margin-left:auto; margin-right:auto; text-align:left; max-width:100%; }
/* ═══ V11 : prononciation, citation ═══ */
.pron { display:flex; flex-wrap:wrap; justify-content:center; gap:6px 16px; margin:0 0 10px; font-size:14px; color:var(--muted); }
.pron-it { display:inline-flex; align-items:center; gap:6px; }
.pron .replay-button svg, .pron .soundLink svg { width:26px; height:26px; }
.pron .tts { font-size:15px; padding:1px 10px; }
.cit-ctx { font-size:14px; font-style:italic; color:var(--muted); margin:2px 0 10px; }
/* ═══ V11 : saisie tolérante ═══ */
.sx-zone { margin-top:10px; display:flex; flex-wrap:wrap; justify-content:center; align-items:center; gap:10px; }
.sx-btn[disabled] { opacity:.5; }
.sx-pat { font:600 18px/1.2 "SF Mono",Menlo,Consolas,monospace; letter-spacing:.06em; }
.sx-verdict { margin:8px 0 0; padding:6px 10px; border-radius:8px; font-size:15px; font-weight:600; }
.sx-verdict:empty { display:none; }
.sx-verdict.ok { background:rgba(46,125,50,.14); color:var(--env-k); } .sx-verdict.moy { background:rgba(230,81,0,.13); color:var(--instr-k); }
.sx-verdict.info { background:var(--chip); color:var(--muted); font-weight:500; }
code#typeans.sx-dim { opacity:.45; }
/* ═══ V11 : une par une ═══ */
.v10.op-on .op-seq:not(.mt-vu) { position:relative; max-height:1.75em; overflow:hidden; border-radius:6px; background:var(--chip); cursor:pointer; }
.v10.op-on .op-seq:not(.mt-vu) { color:transparent !important; }
.v10.op-on .op-seq:not(.mt-vu) * { color:transparent !important; background-color:transparent !important; border-color:transparent !important; box-shadow:none !important; }
.v10.op-on .op-seq:not(.mt-vu) svg, .v10.op-on .op-seq:not(.mt-vu) img { visibility:hidden; }
.v10.op-on .op-seq:not(.mt-vu)::after { content:attr(data-op); position:absolute; left:12px; top:.15em; font-size:14px; font-style:italic; color:var(--muted); }
.v10.op-on .op-seq.op-next:not(.mt-vu) { outline:2px dashed var(--v10-link); outline-offset:1px; }
.v10.op-on .op-seq.op-next:not(.mt-vu)::after { color:var(--v10-link); }
.v10.op-on .cloze.op-seq:not(.mt-vu) { display:inline-block; min-width:6.5em; height:1.35em; max-height:none; vertical-align:-.25em; }
.v10.op-on .cloze.op-seq:not(.mt-vu)::after { left:8px; top:0; line-height:1.35em; font-size:13px; }
.v10.trous-v .mt-bar { justify-content:center; margin-top:12px; }
.v10.op-on .mt-bloc:not(.op-seq):not(.mt-vu) { filter:blur(8px); }
.op-anim { animation:opv .35s ease-out; }
@keyframes opv { from { opacity:0; transform:translateY(3px); } to { opacity:1; transform:none; } }
@media (prefers-reduced-motion: reduce) { .op-anim { animation:none; } }
.mt-next { background:var(--v10-link) !important; border-color:var(--v10-link) !important; color:#fff !important; }
"""

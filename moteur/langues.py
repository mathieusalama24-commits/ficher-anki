"""
langues.py — Type de note « Ficher — Chinois » (écoute + lecture, tons en couleur).

- Carte « Écoute » : on entend le mot (audio AwesomeTTS dans le champ Audio, sinon voix de synthèse
  intégrée d'Anki {{tts zh_CN:…}}) → on le dit et on donne son sens.
- Carte « Lecture » : on voit les caractères → on les lit et on donne leur sens.
Au verso, chaque syllabe du pinyin ET chaque caractère prend la couleur de son ton
(1 rouge, 2 vert, 3 bleu, 4 violet, neutre gris). Le pinyin doit séparer les syllabes par des
espaces : « xué xí », « Zhōng wén ».
"""

NOM_CHINOIS = "Ficher — Chinois"
MODEL_ID_CHINOIS = 1790500020
CHINOIS_FIELDS = ["Hanzi", "Pinyin", "Sens", "Exemple", "ExemplePinyin", "ExempleSens",
                  "Audio", "AudioExemple", "Note", "Ecriture"]

TONE_JS = r"""<script>(function(){
var T={1:'āēīōūǖĀĒĪŌŪ',2:'áéíóúǘÁÉÍÓÚ',3:'ǎěǐǒǔǚǍĚǏǑǓ',4:'àèìòùǜÀÈÌÒÙ'};
function tone(s){for(var t=1;t<=4;t++){for(var i=0;i<T[t].length;i++){if(s.indexOf(T[t][i])>=0)return t;}}return 5;}
function isHan(c){return /[㐀-鿿]/.test(c);}
document.querySelectorAll('.lg-bloc').forEach(function(b){
  if(b.dataset.done)return;b.dataset.done=1;
  var py=b.querySelector('.py'),hz=b.querySelector('.hz');if(!py)return;
  var syl=py.textContent.trim().split(/\s+/),tones=[];
  py.innerHTML=syl.map(function(s){var t=tone(s);if(/[a-zA-ZüÜ]/.test(s))tones.push(t);return '<span class="t'+t+'">'+s+'</span>';}).join(' ');
  if(hz){var k=0;hz.innerHTML=Array.from(hz.textContent).map(function(c){if(isHan(c)){var t=tones[k++]||5;return '<span class="t'+t+'">'+c+'</span>';}return c;}).join('');}
});})();</script>"""

AUDIO_MOT = "{{#Audio}}{{Audio}}{{/Audio}}{{^Audio}}{{tts zh_CN:Hanzi}}{{/Audio}}"
AUDIO_EX = "{{#AudioExemple}}{{AudioExemple}}{{/AudioExemple}}{{^AudioExemple}}{{tts zh_CN:Exemple}}{{/AudioExemple}}"

REVELE = """<div class="v10 lg">
<div class="lg-bloc"><div class="hz">{{Hanzi}}</div><div class="py">{{Pinyin}}</div></div>
<div class="sens">{{Sens}}</div>
{{#Exemple}}<div class="ex lg-bloc"><div class="hz hz-ex">{{Exemple}}</div><div class="py py-ex">{{ExemplePinyin}}</div>
<div class="sens-ex">{{ExempleSens}}</div><div class="audio">""" + AUDIO_EX + """</div></div>{{/Exemple}}
{{#Note}}<div class="lien">💡 {{Note}}</div>{{/Note}}
<div class="legende-tons"><span class="t1">ton 1</span> · <span class="t2">ton 2</span> · <span class="t3">ton 3</span> · <span class="t4">ton 4</span> · <span class="t5">neutre</span></div>
</div>"""

ECOUTE_FRONT = """<div class="v10 recto lg"><div class="lg-tag">🎧 Écoute</div>
<div class="audio big">""" + AUDIO_MOT + """</div>
<div class="question">Qu'entends-tu ? Répète le mot à voix haute et donne son sens.</div></div>"""
ECOUTE_BACK = ECOUTE_FRONT + '\n<hr id="answer">\n' + REVELE + "\n" + TONE_JS

LECTURE_FRONT = """<div class="v10 recto lg"><div class="lg-tag">👁️ Lecture</div>
<div class="hz hz-seul">{{Hanzi}}</div>
<div class="question">Lis ces caractères à voix haute et donne leur sens.</div></div>"""
LECTURE_BACK = """<div class="v10 recto lg"><div class="lg-tag">👁️ Lecture</div></div>
<hr id="answer">
""" + REVELE + """
<div class="v10 lg"><div class="audio">""" + AUDIO_MOT + "</div></div>\n" + TONE_JS

# Carte « Écriture » (calligraphie, à la main — jamais au clavier) : créée seulement si le champ Ecriture
# est rempli (ex. « 1 ») ; on voit le sens et le pinyin, on écrit les caractères sur papier.
ECRITURE_FRONT = """{{#Ecriture}}<div class="v10 recto lg"><div class="lg-tag">✍️ Écriture</div>
<div class="sens">{{Sens}}</div><div class="py-seul">{{Pinyin}}</div>
<div class="question">Écris ce mot à la main (ordre des traits), puis vérifie.</div></div>{{/Ecriture}}"""
ECRITURE_BACK = ECRITURE_FRONT + '\n<hr id="answer">\n' + REVELE + "\n" + TONE_JS

CHINOIS_TEMPLATES = [
    {"name": "Écoute", "qfmt": ECOUTE_FRONT, "afmt": ECOUTE_BACK},
    {"name": "Lecture", "qfmt": LECTURE_FRONT, "afmt": LECTURE_BACK},
    {"name": "Écriture", "qfmt": ECRITURE_FRONT, "afmt": ECRITURE_BACK},
]

CHINOIS_CSS = """
.lg-tag { font-size:13px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin-bottom:10px; }
.lg .hz { font-size:64px; line-height:1.15; font-weight:500; text-align:center; font-family:"PingFang SC","Hiragino Sans GB","Noto Sans CJK SC","Microsoft YaHei",sans-serif; }
.lg .hz-seul { margin:18px 0 8px; }
.lg .py-seul { font-size:22px; text-align:center; color:var(--muted); margin-bottom:6px; }
.lg .py { font-size:24px; text-align:center; margin-top:4px; letter-spacing:.02em; }
.lg .sens { font-size:21px; font-weight:600; text-align:center; margin:12px 0 4px; }
.lg .ex { margin-top:18px; padding:12px 14px; border-radius:10px; border:1px solid var(--line); }
.lg .hz-ex { font-size:30px; }
.lg .py-ex { font-size:17px; }
.lg .sens-ex { text-align:center; color:var(--muted); font-size:15px; margin-top:6px; }
.lg .audio { text-align:center; margin-top:8px; }
.lg .audio.big { font-size:40px; margin:22px 0 10px; }
.lg .legende-tons { text-align:center; font-size:12px; margin-top:14px; color:var(--muted); }
.t1 { color:#E53935; } .t2 { color:#2E9E4F; } .t3 { color:#1E88E5; } .t4 { color:#8E24AA; } .t5 { color:#8A8F98; }
.nightMode .t1, .night_mode .t1 { color:#FF6F6A; } .nightMode .t2, .night_mode .t2 { color:#5FD17F; }
.nightMode .t3, .night_mode .t3 { color:#64B5F6; } .nightMode .t4, .night_mode .t4 { color:#CE93D8; }
"""


# ════════════════════════════════════════════════════════════════════
# Langues à alphabet (espagnol, arabe égyptien, polonais…) : un type de note par langue,
# fabriqué par la même usine. Pas de carte à taper. Écoute + Lecture, et « Production »
# (sens → dire ou écrire le mot à la main) si le champ Production est rempli.
LANGUES = {  # clé JSON : (nom affiché, code TTS d'Anki, écriture de droite à gauche, id du modèle)
    "espagnol": ("Espagnol", "es_ES", False, 1790500021),
    "arabe_egyptien": ("Arabe égyptien", "ar_EG", True, 1790500022),
    "polonais": ("Polonais", "pl_PL", False, 1790500023),
}
LANGUE_FIELDS = ["Mot", "Transcription", "Sens", "Exemple", "ExempleTranscription", "ExempleSens",
                 "Audio", "AudioExemple", "Note", "Production"]


def nom_modele_langue(cle):
    return f"Ficher — {LANGUES[cle][0]}"


def templates_langue(cle):
    nom, tts, rtl, _ = LANGUES[cle]
    d = ' dir="rtl"' if rtl else ""
    mot_audio = "{{#Audio}}{{Audio}}{{/Audio}}{{^Audio}}{{tts " + tts + ":Mot}}{{/Audio}}"
    ex_audio = "{{#AudioExemple}}{{AudioExemple}}{{/AudioExemple}}{{^AudioExemple}}{{tts " + tts + ":Exemple}}{{/AudioExemple}}"
    revele = f"""<div class="v10 lg">
<div class="mot"{d}>{{{{Mot}}}}</div>{{{{#Transcription}}}}<div class="tr">{{{{Transcription}}}}</div>{{{{/Transcription}}}}
<div class="sens">{{{{Sens}}}}</div>
{{{{#Exemple}}}}<div class="ex"><div class="mot-ex"{d}>{{{{Exemple}}}}</div>{{{{#ExempleTranscription}}}}<div class="tr tr-ex">{{{{ExempleTranscription}}}}</div>{{{{/ExempleTranscription}}}}
<div class="sens-ex">{{{{ExempleSens}}}}</div><div class="audio">{ex_audio}</div></div>{{{{/Exemple}}}}
{{{{#Note}}}}<div class="lien">💡 {{{{Note}}}}</div>{{{{/Note}}}}
</div>"""
    ecoute_f = f"""<div class="v10 recto lg"><div class="lg-tag">🎧 Écoute · {nom}</div>
<div class="audio big">{mot_audio}</div>
<div class="question">Qu'entends-tu ? Répète le mot à voix haute et donne son sens.</div></div>"""
    lecture_f = f"""<div class="v10 recto lg"><div class="lg-tag">👁️ Lecture · {nom}</div>
<div class="mot mot-seul"{d}>{{{{Mot}}}}</div>
<div class="question">Lis ce mot à voix haute et donne son sens.</div></div>"""
    prod_f = f"""{{{{#Production}}}}<div class="v10 recto lg"><div class="lg-tag">🗣️ Production · {nom}</div>
<div class="sens">{{{{Sens}}}}</div>
<div class="question">Comment le dit-on ? Dis-le à voix haute{" et écris-le à la main" if rtl else ""}.</div></div>{{{{/Production}}}}"""
    return [
        {"name": "Écoute", "qfmt": ecoute_f, "afmt": ecoute_f + '\n<hr id="answer">\n' + revele},
        {"name": "Lecture", "qfmt": lecture_f,
         "afmt": lecture_f + '\n<hr id="answer">\n' + revele + f'\n<div class="v10 lg"><div class="audio">{mot_audio}</div></div>'},
        {"name": "Production", "qfmt": prod_f,
         "afmt": prod_f + '\n<hr id="answer">\n' + revele + f'\n<div class="v10 lg"><div class="audio">{mot_audio}</div></div>'},
    ]


LANGUE_CSS = """
.lg-tag { font-size:13px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin-bottom:10px; }
.lg .mot { font-size:46px; line-height:1.25; font-weight:600; text-align:center; }
.lg .mot-seul { margin:18px 0 8px; }
.lg [dir="rtl"] { font-family:"Geeza Pro","Noto Naskh Arabic","Traditional Arabic","Arial",sans-serif; font-size:52px; }
.lg .mot-ex { font-size:26px; text-align:center; font-weight:500; }
.lg .mot-ex[dir="rtl"] { font-size:32px; }
.lg .tr { font-size:20px; text-align:center; color:var(--muted); font-style:italic; margin-top:2px; }
.lg .tr-ex { font-size:16px; }
.lg .sens { font-size:21px; font-weight:600; text-align:center; margin:12px 0 4px; }
.lg .ex { margin-top:18px; padding:12px 14px; border-radius:10px; border:1px solid var(--line); }
.lg .sens-ex { text-align:center; color:var(--muted); font-size:15px; margin-top:6px; }
.lg .audio { text-align:center; margin-top:8px; }
.lg .audio.big { font-size:40px; margin:22px 0 10px; }
"""

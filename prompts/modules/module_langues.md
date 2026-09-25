# MODULE — Langues (chinois, espagnol, arabe égyptien, polonais…)

## CHINOIS
Type de note `chinois` (« Ficher — Chinois »). **Aucune carte à taper** : pour une langue, on
révise à l'oral et à la main, pas au clavier. Chaque note crée automatiquement :
- 🎧 **Écoute** : on entend le mot → on le répète et on donne son sens ;
- 👁️ **Lecture** : on voit les caractères → on les lit à voix haute et on donne le sens ;
- ✍️ **Écriture** (seulement avec `"ecriture": true`) : on voit le sens et le pinyin → on écrit les
  caractères À LA MAIN, puis on vérifie. À mettre sur les caractères nouveaux que le cours demande de
  savoir écrire.
Au verso, chaque caractère et chaque syllabe prend la couleur de son ton (1 rouge, 2 vert, 3 bleu,
4 violet, neutre gris) ; l'exemple est lu à son tour.

```json
{"modele": "chinois", "hanzi": "喜欢", "pinyin": "xǐ huan", "sens": "aimer (bien), apprécier",
 "exemple": "我喜欢喝茶。", "exemple_pinyin": "Wǒ xǐ huan hē chá.", "exemple_sens": "J'aime boire du thé.",
 "note": "…", "ecriture": true, "audio": "", "audio_exemple": "", "tags": ["langue::chinois", "lecon::3"]}
```
- `pinyin` et `exemple_pinyin` : accents de ton obligatoires, **une syllabe par caractère, séparées
  par des espaces** (« Zhōng guó », pas « Zhōngguó ») : c'est ce qui aligne les couleurs.
- Audio : comme pour les autres langues (plus bas), génère de vrais fichiers mp3 (voix `zh-CN-XiaoxiaoNeural`)
  quand l'ordinateur est relié ; sinon laisse `audio` vide (voix de synthèse d'Anki).
- `note` : une remarque utile au plus (ton neutre, spécificateur, faux ami, mot proche à ne pas
  confondre). L'`ancre` est le hanzi : une seule note par mot (anti-doublon).
- Exemple : de préférence la phrase du cours ; sinon une phrase courte, de niveau débutant, avec des
  mots déjà vus.
- **Grammaire** (forme interrogative avec 吗 et 呢, mots interrogatifs, 是…的…) : `trous` sur une phrase
  modèle, hanzi puis pinyin, avec la traduction et la règle en une phrase dans `extra` ; ou `basique`
  (icône 📐) avec un `tableau` qui compare deux structures.
- Vérifie le pinyin et le sens (dictionnaire MDBG : mdbg.net) ; le cours prime sur le dictionnaire.
- Paquet : `🇨🇳 Chinois::Leçon N` (vérifie avec `listDecks` si l'utilisateur a déjà un paquet de chinois).
  Tags : `langue::chinois`, `matiere::chinois`, `lecon::N`.

## AUTRES LANGUES (espagnol, arabe égyptien, polonais)
Type de note `langue`, avec `"langue": "espagnol" | "arabe_egyptien" | "polonais"` (un type de note
par langue, créé automatiquement). **Aucune carte à taper.** Chaque note crée :
- 🎧 **Écoute** : on entend le mot → on le répète et on donne son sens ;
- 👁️ **Lecture** : on lit le mot → on le prononce et on donne son sens ;
- 🗣️ **Production** (avec `"production": true`) : on voit le sens → on dit le mot (et, pour l'arabe,
  on l'écrit à la main). À mettre sur les mots que l'utilisateur doit savoir PRODUIRE, pas seulement
  reconnaître.

```json
{"modele": "langue", "langue": "arabe_egyptien", "mot": "عايز", "transcription": "ʿāyez",
 "sens": "vouloir (« je veux », au masculin)", "exemple": "أنا عايز قهوة",
 "exemple_transcription": "ana ʿāyez ʾahwa", "exemple_sens": "Je veux un café.",
 "note": "…", "production": true, "tags": ["langue::arabe-egyptien"]}
```
- `transcription` : utile pour l'arabe (translittération simple et constante dans tout le paquet) ;
  inutile pour l'espagnol et le polonais, sauf prononciation piégeuse.
- L'arabe s'affiche automatiquement de droite à gauche, en grand.
- **Arabe égyptien ≠ arabe standard** : donne la forme égyptienne (عايز, pas أريد) et signale la forme
  standard dans `note` seulement si elle aide.
- **Audio : génère de vrais fichiers**, ne compte pas sur la synthèse à la volée (AwesomeTTS bloque
  les langues qu'il n'a pas enregistrées, par exemple ar_EG). Quand l'ordinateur de l'utilisateur est
  relié, utilise edge-tts dans un environnement Python temporaire (`python3 -m venv /tmp/tts_venv &&
  /tmp/tts_venv/bin/pip install edge-tts`), une voix par langue : `ar-EG-ShakirNeural` (ou
  `SalmaNeural` pour une forme féminine), `es-ES-AlvaroNeural`, `pl-PL-MarekNeural`,
  `zh-CN-XiaoxiaoNeural`, avec un débit un peu ralenti pour le mot seul (`--rate=-15%`). Nomme les
  fichiers `ficher_<langue>_<mot-translittéré>.mp3` (et `_ex` pour l'exemple), pose-les dans `audio/` à côté
  de `cartes.json`, liste-les dans `"medias"` en tête du JSON et mets `[sound:fichier.mp3]` dans
  `audio` et `audio_exemple`. Sans ordinateur relié : laisse `audio` vide (voix de synthèse d'Anki) et
  signale-le en une ligne.
- `note` : un faux ami, une irrégularité, un genre, une prononciation (une remarque au plus).
- Paquet : le paquet existant de la langue (vérifie avec `listDecks`) ; sinon `🇪🇸 Espagnol`,
  `🇪🇬 Arabe égyptien`, `🇵🇱 Polonais`. Tags : `langue::<langue>`, `theme::<thème>`.

Autre langue : ajoute-la dans `LANGUES` de `langues.py` (nom affiché, code de la voix Anki, sens
d'écriture, identifiant unique du type de note), puis choisis une voix edge-tts de cette langue.

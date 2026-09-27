# Ficher — des flashcards Anki soignées, générées par Claude à partir de tes cours

Tu donnes un cours, un chapitre, un article ou une actualité à Claude. Il en tire des cartes Anki
**courtes, colorées et visuelles** et te rend un fichier `.apkg` : double-clic, c'est dans Anki.

<p align="center">
  <img src="docs/hero.png" width="100%" alt="Neuf cartes Ficher : carte géographique, carte mentale, formule, sigle décomposé, estimation, chinois, occlusion d'image, cercle vicieux, cinq forces de Porter">
</p>

Gratuit et open source (licence MIT). Géopolitique, finance, maths, médecine, droit, langues, code :
le même moteur sert pour toutes les matières. Pense à relire les cartes : Claude vérifie les faits
sur le web et cite ses sources au verso, mais il peut se tromper.

**Envie de voir en vrai ?** Importe [`paquets/Ficher_vitrine.apkg`](paquets/Ficher_vitrine.apkg) dans Anki :
40 cartes d'exemple, toutes celles de la galerie ci-dessous (source : [`exemples/cartes_vitrine.json`](exemples/cartes_vitrine.json)).

Deux paquets complets de prépa ECG, faits avec Ficher :

| Paquet | Contenu |
|---|---|
| [`Ficher_HGG_Asie_4.2.1.apkg`](paquets/Ficher_HGG_Asie_4.2.1.apkg) | HGG, « L'Asie : géopolitique d'une région plurielle » : 119 notes, 7 cartes muettes, frises, réseaux, étude de cas du Sri Lanka, chiffres revérifiés (ONU 2025, FMI 2026, PNUD 2025) |
| [`Ficher_Maths_Variables_a_densite.apkg`](paquets/Ficher_Maths_Variables_a_densite.apkg) | Maths, variables à densité : 28 notes « par cœur » (définitions, théorèmes, lois usuelles, méthodes), formules MathJax |

## Ce que font les cartes

- **Une idée par carte** : une question, une réponse centrale, 2 à 4 puces, au plus deux encarts
  (piège, lien, moyen mnémotechnique, anecdote).
- **Code couleur** en 13 catégories (risque, économie, politique, acteur, concept…), en mode clair
  comme en mode sombre.
- **16 familles de schémas** dessinés automatiquement : chaîne causale, frise, matrice, courbe,
  balance, cartes géographiques réelles (avec une version muette pour s'entraîner à localiser)…
- **Cartes mentales à rappel actif** : une carte pour retrouver les axes, puis une carte par branche.
- **Plusieurs façons de réviser** : texte à trous, réponse à taper (avec tolérance des variantes et
  bouton « Lettre suivante »), curseur d'estimation « Combien ? », citations à trous, occlusion
  d'image, mode test et révélation « une par une ».
- **Cartes « par cœur »** pour les définitions, théorèmes, articles de loi et citations : tout l'énoncé
  est masqué, on le récite, puis on le dévoile bloc par bloc.
- **Formules** (MathJax) et **blocs de code** à trous.
- **Portraits et images** tirés de Wikipédia et Wikimedia Commons, avec leur crédit.
- **Langues** : chinois (tons en couleur), espagnol, arabe égyptien, polonais, avec cartes d'écoute,
  de lecture et de production, et audio.
- **Anti-doublon** : si tu réimportes une carte corrigée, elle remplace l'ancienne sans effacer ta
  progression.

## Galerie

Captures des aperçus générés par le moteur (`--preview`). Chaque carte montre le verso, sauf mention « recto ».

### Schémas dessinés automatiquement

Claude écrit une spec JSON de quelques lignes, le moteur dessine le schéma, lisible en clair et en sombre.

| | |
|---|---|
| **Carte géographique réelle** — fond Natural Earth, points en longitude/latitude, itinéraire maritime.<br><img src="docs/galerie/carte-reelle.png" width="100%"> | **Carte muette (recto)** — le même fond sans aucun nom : localise ① avant de retourner la carte.<br><img src="docs/galerie/carte-muette.png" width="100%"> |
| **Chaîne causale** — des verbes précis sur chaque flèche, l'enjeu final marqué ⚑.<br><img src="docs/galerie/chaine-causale.png" width="100%"> | **Bifurcation** — une cause, deux effets, un enjeu.<br><img src="docs/galerie/bifurcation.png" width="100%"> |
| **Cercle vicieux** — pour les boucles qui s'auto-entretiennent.<br><img src="docs/galerie/boucle.png" width="100%"> | **Réseau d'acteurs** — alliances, coopérations et rivalités.<br><img src="docs/galerie/reseau.png" width="100%"> |
| **Frise** — les jalons datés, l'aboutissement en dernier.<br><img src="docs/galerie/frise.png" width="100%"> | **Périodes** — des durées qui se chevauchent.<br><img src="docs/galerie/periodes.png" width="100%"> |

<details>
<summary><b>Voir les 9 autres schémas</b> (courbe, matrice, barres, jauge, balance, tableau, arbre, avant/après, chiffre)</summary>

| | |
|---|---|
| **Courbe théorique** — sans graduations inventées (Laffer, Kuznets, Phillips…).<br><img src="docs/galerie/courbe-schema.png" width="100%"> | **Matrice** — positionner sur deux axes (BCG, Ansoff…).<br><img src="docs/galerie/matrice.png" width="100%"> |
| **Barres** — comparer des grandeurs vérifiées.<br><img src="docs/galerie/barres.png" width="100%"> | **Jauge + moyen mnémotechnique** — une proportion d'un coup d'œil.<br><img src="docs/galerie/jauge-memo.png" width="100%"> |
| **Balance** — le pour et le contre d'un débat.<br><img src="docs/galerie/balance.png" width="100%"> | **Tableau comparatif** — 2 ou 3 acteurs sur quelques critères.<br><img src="docs/galerie/tableau.png" width="100%"> |
| **Arbre** — une classification, avec annotations.<br><img src="docs/galerie/arbre.png" width="100%"> | **Avant / après** — ce qu'un événement a changé, marqué automatiquement.<br><img src="docs/galerie/avant-apres.png" width="100%"> |
| **Chiffre qui frappe + date + portrait** — la date se cache au recto (« Date à retrouver »).<br><img src="docs/galerie/chiffre-date-portrait.png" width="100%"> | |

</details>

### Plusieurs façons de réviser

| | |
|---|---|
| **Réponse à taper** — variantes acceptées (Hormuz / Ormuz), comparaison lettre à lettre.<br><img src="docs/galerie/saisie-tolerante.png" width="100%"> | **Date, anecdote et carte à taper** — ici un arrêt de droit administratif.<br><img src="docs/galerie/saisie-blanco-date-anecdote.png" width="100%"> |
| **Estimation (recto)** — « Combien ? » : on place un curseur…<br><img src="docs/galerie/estimation-recto.png" width="100%"> | **Estimation (verso)** — …puis on voit l'écart et un verdict.<br><img src="docs/galerie/estimation-verso.png" width="100%"> |
| **Mode test** — tout le verso flouté, on dévoile bloc par bloc.<br><img src="docs/galerie/mode-test.png" width="100%"> | **Une par une** — une démonstration dévoilée étape par étape.<br><img src="docs/galerie/une-par-une-demonstration.png" width="100%"> |
| **Occlusion d'image (recto)** — un schéma original, la zone visée en orange.<br><img src="docs/galerie/occlusion-recto.png" width="100%"> | **Occlusion d'image (verso)** — seule la zone cherchée se dévoile.<br><img src="docs/galerie/occlusion-verso.png" width="100%"> |
| **Par cœur : théorème** — tout l'énoncé est masqué, même « Soit », « Alors », « si et seulement si ».<br><img src="docs/galerie/par-coeur-theoreme.png" width="100%"> | **Par cœur : article de loi** — en italique, récité puis dévoilé bloc par bloc.<br><img src="docs/galerie/par-coeur-droit.png" width="100%"> |
| **Citation à trous** — on retrouve les mots porteurs, pas les mots de liaison.<br><img src="docs/galerie/citation.png" width="100%"> | **Image au recto** — « Quelle rencontre cette photo immortalise-t-elle ? »<br><img src="docs/galerie/image-recto.png" width="100%"> |

### Cartes mentales à rappel actif

| | |
|---|---|
| **Structure (recto)** — retrouver les grands axes, seules leurs couleurs sont visibles.<br><img src="docs/galerie/mindmap-structure-recto.png" width="100%"> | **Branche (recto)** — une carte par branche : combien de nœuds, lesquels ?<br><img src="docs/galerie/mindmap-branche-recto.png" width="100%"> |
| **Structure (verso)** — la carte complète, avec portrait et schéma sous une branche.<br><img src="docs/galerie/mindmap-structure-verso.png" width="100%"> | **Hors géopolitique** — les cinq forces de Porter.<br><img src="docs/galerie/mindmap-porter.png" width="100%"> |

### Formules, sigles et code

| | |
|---|---|
| **Formule MathJax** — variables expliquées et règle de décision.<br><img src="docs/galerie/formule-van.png" width="100%"> | **Sigle décomposé** — chaque lettre et son sens.<br><img src="docs/galerie/decomposition-sigle.png" width="100%"> |
| **Formule à trous (recto)**<br><img src="docs/galerie/trous-formule-recto.png" width="100%"> | **Formule à trous (verso)**<br><img src="docs/galerie/trous-formule-verso.png" width="100%"> |
| **Code à trous (recto)** — le trou porte sur l'instruction qui compte.<br><img src="docs/galerie/code-python-recto.png" width="100%"> | **Code à trous (verso)**<br><img src="docs/galerie/code-python-verso.png" width="100%"> |

### Portraits et prononciation

| | |
|---|---|
| **Portrait + prononciation** — la photo et le bouton audio (voix d'Anki).<br><img src="docs/galerie/portrait-prononciation.png" width="100%"> | **Carte Realpolitik** — décomposition du mot, deux portraits, date et auteur au verso.<br><img src="docs/carte_realpolitik.png" width="100%"> |

### Langues

| | |
|---|---|
| **Chinois** — chaque caractère prend la couleur de son ton.<br><img src="docs/galerie/chinois-lecture.png" width="100%"> | **Chinois, écriture (recto)** — écrire les caractères à la main.<br><img src="docs/galerie/chinois-ecriture-recto.png" width="100%"> |
| **Arabe égyptien** — de droite à gauche, avec transcription.<br><img src="docs/galerie/arabe.png" width="100%"> | **Espagnol, production** — du sens vers le mot.<br><img src="docs/galerie/espagnol-production.png" width="100%"> |

### Mode sombre

<details>
<summary><b>Voir les 7 captures en mode sombre</b></summary>

| | |
|---|---|
| <img src="docs/galerie/sombre-carte-reelle.png" width="100%"> | <img src="docs/galerie/sombre-mindmap.png" width="100%"> |
| <img src="docs/galerie/sombre-formule-van.png" width="100%"> | <img src="docs/galerie/sombre-decomposition.png" width="100%"> |
| <img src="docs/galerie/sombre-balance.png" width="100%"> | <img src="docs/galerie/sombre-chinois.png" width="100%"> |
| <img src="docs/galerie/sombre-occlusion.png" width="100%"> | |

</details>

### Sur téléphone

| | | |
|---|---|---|
| <img src="docs/galerie/telephone-reseau.png" width="100%"> | <img src="docs/galerie/telephone-mindmap.png" width="100%"> | <img src="docs/galerie/telephone-chinois.png" width="100%"> |

## Installation (10 minutes, une seule fois)

Il te faut [Anki](https://apps.ankiweb.net) et un compte [Claude](https://claude.ai) qui permet de
créer des **Projets** et d'exécuter du code (vérifie que « exécution de code et création de
fichiers » est activée dans les paramètres de Claude).

1. **Télécharge ce dépôt** : bouton vert « Code » → « Download ZIP », puis décompresse.
2. **Importe le paquet de démarrage** `paquets/Ficher_demarrage.apkg` dans Anki (double-clic).
   Il installe les types de note « Ficher » et te montre 11 cartes d'exemple.
   Pour tout voir, importe aussi `paquets/Ficher_vitrine.apkg`.
3. **Crée un Projet dans Claude** (par exemple « Flashcards ») et ajoute-lui ces fichiers :
   - les 7 scripts du dossier `moteur/` ;
   - `prompts/socle.md` ;
   - le ou les modules de ta filière, dans `prompts/modules/`.
   - Cartes géographiques : ajoute aussi les fonds dont tu as besoin (`moteur/assets/_geo_*.svg`)
     et demande à Claude de les ranger dans un dossier `assets/` à côté des scripts.
4. **Colle la consigne** de [`prompts/consigne_projet.md`](prompts/consigne_projet.md) dans les
   « Instructions » du projet.
5. **Teste** : ouvre une conversation dans le projet, joins un chapitre de cours (PDF, diapositives,
   texte) et écris « fais-moi des flashcards ». Claude annonce le nombre de cartes, construit le
   paquet et te le livre.

## Modules disponibles

| Module | Pour |
|---|---|
| `module_geopolitique.md` | HGG, ESH, Sciences Po, relations internationales, actualité |
| `module_ecole_de_commerce.md` | finance, stratégie, économie, marketing, RH, négociation |
| `module_langues.md` | chinois, espagnol, arabe égyptien, polonais (et d'autres à ajouter) |
| `module_concours_insp.md` | concours de l'INSP (droit public, finances publiques, QRC…) |

Ta matière n'y est pas ? Copie [`_modele_de_module.md`](prompts/modules/_modele_de_module.md) et
remplis-le : types de carte, sens des couleurs dans ta matière, schémas utiles, sources. Partage-le
ensuite sur le Discord ou propose-le ici (pull request) pour que d'autres en profitent.

## Portraits et images

Claude télécharge les photos depuis Wikipédia. Dans certains environnements, il n'a pas accès au
réseau. Si des portraits manquent, lance cette commande dans le dossier des cartes, puis demande à
Claude de reconstruire le paquet (s'il est relié à ton ordinateur, il peut la lancer lui-même) :

```bash
python3 portraits.py cartes.json
```

## Utiliser le moteur sans Claude

Le moteur est un simple script Python : il transforme un fichier `cartes.json` en paquet Anki.

```bash
pip install -r requirements.txt
cd exemples
python3 ../moteur/build_apkg.py cartes_vitrine.json -o vitrine.apkg --preview apercu
```

`--preview apercu` produit un aperçu HTML de chaque carte, en clair et en sombre. Le format du JSON
est décrit en tête de `moteur/build_apkg.py` et dans `prompts/socle.md` (§10). Les fonds de carte
viennent de [Natural Earth](https://www.naturalearthdata.com) (domaine public).

## Bonnes pratiques

- **Fais tes cartes à partir de tes propres fiches ou de ton cours**, pour toi. Ne partage pas des
  paquets qui reprennent tel quel le polycopié d'un professeur ou un manuel protégé.
- Garde la même ancre quand tu corriges une carte : Anki la met à jour au lieu d'en créer une autre.
- Commence sobre : on enrichit plus tard les cartes qu'on rate souvent.

## Communauté

Entraide à l'installation, idées et paquets partagés par filière : rejoins le **[Discord Ficher](https://discord.gg/CNa3rk23Zv)**.

## Licence

MIT, voir [LICENSE](LICENSE). Les portraits et images d'exemple viennent de Wikimedia Commons ; leur
auteur et leur licence sont dans `exemples/portraits/credits.json` et affichés sur chaque carte.
Les fonds de carte de `moteur/assets/` sont tirés de Natural Earth (domaine public).

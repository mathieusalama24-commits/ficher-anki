# MODULE — Concours de l'INSP (ex-ENA), concours externe et voie « Talents »

Programme et épreuves identiques au concours externe (source : insp.gouv.fr). Écrits : note de
réflexion sur une question contemporaine (rôle de la puissance publique) ; note opérationnelle
d'économie ; note opérationnelle de droit public ; questions à réponse courte (finances publiques,
questions sociales, questions européennes) ; cas pratique sur les transitions écologique ou
numérique. Oraux : entretien, mise en situation collective, anglais. Vérifie sur insp.gouv.fr que
cette liste est toujours à jour avant une grosse session.

Types : ⚖️ A notion ou jurisprudence de droit public · 💶 B donnée ou mécanisme (économie,
finances publiques) · 🇪🇺 C question européenne ou sociale · 💡 D référence mobilisable (auteur,
rapport, citation SOURCÉE, exemple) · 🌱 E transitions écologique et numérique.

Classes : `inst` institution, juridiction · `pol` politique publique, décision · `eco` finances
publiques, économie · `conc` principe, notion juridique · `risk` risque, contentieux, limite ·
`act` acteur, auteur, exemple · `date` date, réforme · `soc` questions sociales · `env` transition
écologique · `res` numérique, infrastructures · `instr` instrument de l'action publique (loi,
règlement, dispositif) · `enj` enjeu · `prosp` réforme en cours, prospective.

Règles :
- Jurisprudence : ancre = nom de l'arrêt et juridiction avec la date (« TC, 8 février 1873,
  Blanco ») ; la carte ⌨️ fait taper le nom de l'arrêt ; le principe dégagé est la réponse centrale.
- Chiffres de finances publiques (dette, déficit, dépenses) : toujours datés, sourcés (INSEE,
  Cour des comptes, budget.gouv.fr) et tagués `evolutif`.
- Carte « QRC » : question courte d'examen → réponse en une phrase + 3 puces structurées (le
  « Mode test » entraîne à restituer le plan).
- Carte « référence mobilisable » (type D) : l'idée, l'auteur ou l'institution, l'année, et pour
  quel type de sujet la mobiliser (`lien`). Aucune citation sans source vérifiée.
Sources : Légifrance, Conseil d'État, Conseil constitutionnel, vie-publique.fr, Cour des comptes,
INSEE, EUR-Lex et sites des institutions européennes, rapports officiels.

Volume (précise le §3 du socle) : décision de justice → **1 carte** (+ carte ⌨️ du nom de l'arrêt) ;
rapport officiel → **5 à 8** ; chapitre de manuel de préparation → **25 à 40**.

Paquets : `INSP::<Épreuve>::<Thème>`, avec pour épreuve : `Note de réflexion`, `Économie`,
`Droit public`, `QRC` (finances publiques, questions sociales, questions européennes), `Transitions`,
`Oraux` ; ex. `INSP::QRC::Finances publiques`, `INSP::Droit public::Responsabilité administrative`.
Tags : `insp::<épreuve>` en plus des tags du socle.

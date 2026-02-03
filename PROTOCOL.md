# ÉTAPE 0 — CADRAGE : “GENAI BREAKS PROD”

## Objectif

Poser un cadre technique et conceptuel clair avant toute ligne de code.
Cette étape formalise pourquoi une sortie brute de LLM est dangereuse en production et pourquoi un contrat strict est une exigence d’ingénierie, pas une option de confort.

L’objectif n’est pas de “faire de l’IA”, mais de protéger un système critique contre un composant probabiliste.

## Définition de l’environnement de travail

**Environnement cible**

- OS: Linux ou Windows (testé sur environnement développeur standard)

- Python: 3.11+

- Gestion des dépendances: pip, venv

- Aucune dépendance réseau

- Aucun accès externe

- Aucune exécution asynchrone

**Outils autorisés**

- Python standard library

- pydantic (v2)

- pytest (tests uniquement)

- Aucune autre dépendance n’est justifiée pour ce projet.

## Arborescence du projet

genai-output-validator/
│

├── src/

│   ├── schemas.py        # Contrat strict Pydantic

│   ├── sanitizer.py      # Sanitation contrôlée

│   ├── validator.py      # Validation fail-fast

│   └── demo.py           # Exécution démonstrative
│

├── samples/

│   └── bad_outputs.py    # Sorties LLM volontairement incorrectes
│

├── tests/

│   └── test_validator.py # Tests unitaires minimaux
│

├── README.md

└── PROTOCOL.md

## Pourquoi les sorties LLM sont fondamentalement instables

1. Non-déterminisme

Un LLM ne garantit jamais:

- le même format

- les mêmes clés

- les mêmes types

- la même sémantique

- Même avec un prompt identique.

Ce n’est pas un bug.
C’est le fonctionnement normal d’un modèle probabiliste.

2. Hallucinations structurelles

Un LLM peut:

- inventer un champ

- renommer une clé

- omettre une information critique

- produire une valeur “plausible” mais fausse

Le plus dangereux n’est pas l’erreur grossière,
mais l’erreur crédible.

3. Format drift

En production, les sorties peuvent dériver à cause de:

- mise à jour du modèle

- changement du prompt

- ajout de contexte

- variation de température

- longueur de conversation

Le format n’est jamais stable dans le temps.

## Trois scénarios concrets où une sortie LLM casse la prod

1. API backend

Une API attend:

{
  "prediction": "Fraude",
  "probability": 0.87
}


Le LLM renvoie:

{
  "prediction": "fraud",
  "confidence": "87%"
}


Résultat:

500 interne

contrat violé

client impacté

2. Base de données

Un champ probability attendu en FLOAT.

Le LLM renvoie:

"0,92"

"92%"

"high"

Résultat:

insertion impossible

données corrompues

rollback ou crash silencieux

3. Logique métier

Une règle métier:

if prediction == "Fraude" and probability > 0.8:
    block_transaction()


Le LLM renvoie:

"probability": 1.2

"prediction": "MaybeFraud"

Résultat:

décision incohérente

comportement non maîtrisé

incident métier

## Pourquoi un “bon prompt” n’est PAS une garantie d’ingénierie

Un prompt:

- n’est pas typé

- n’est pas versionné

- n’est pas validé

- n’est pas exécutable

- n’est pas testable

Un prompt est une suggestion statistique,
pas un contrat logiciel.

En production:

- on ne fait pas confiance à un texte

- on fait confiance à un contrat validé

## Principe fondamental du projet

Les LLM sont des composants probabilistes.
Tout composant probabiliste doit être encapsulé, contraint et validé.

## Ce projet démontre comment:

ne jamais faire confiance à une sortie brute

forcer un contrat strict

échouer vite, clairement, proprement

ne jamais casser le système aval

############################################################################################################################


# ÉTAPE 1 — CONTRAT DE SORTIE STRICT (Pydantic)
## Objectif

Définir un schéma de sortie strict, orienté production, pour encapsuler les réponses d’un LLM dans un contrat stable et validable.

## Le contrat impose:

types (str, float, datetime…)

contraintes (non vide, bornes, pattern…)

valeurs autorisées (Literal)

interdiction des champs inconnus (extra="forbid")

Résultat attendu: le système aval consomme uniquement des données validées, ou reçoit un rejet propre et explicite.

## Pourquoi c’est critique en production

Contrat stable = système aval stable

Une API, une base, une logique métier ne “comprennent” pas l’intention.

Elles comprennent:

des types

des formats

des invariants

Si la sortie change (format drift), tu as:

erreurs 500

données incohérentes

décisions métiers fausses

incidents difficiles à diagnostiquer

Interdire les champs inconnus = mesure de sécurité

Sans extra="forbid", un LLM peut injecter:

- debug

- internal_note

- tool_output

- pii

- ou n’importe quel champ “plausible”

Et toi, humain optimiste, tu risques de:

- stocker des infos sensibles

- exposer des détails internes

- faire confiance à des champs non maîtrisés

- créer des comportements implicites

- Forbid = tu contrôles l’interface. Le reste est rejeté.

## Risques / pièges

Laisser passer des champs en extra (par défaut Pydantic peut accepter selon config). Mauvaise idée.

Coercition excessive: Pydantic peut convertir des types. Utile parfois, dangereux si tu ne contrôles pas.
Ici, on veut un contrat strict, la “réparation” sera gérée plus tard par sanitizer.py.

Datetime: un LLM peut produire un format exotique. On validera strict, et on décidera en sanitation ce qu’on corrige.

Regex de version: mal définie, tu acceptes v1 ou version1. Ici on impose vMAJOR.MINOR.PATCH.

## Alternatives possibles

Dataclasses + validation manuelle: plus verbeux, plus fragile, moins standard.

Marshmallow: ok mais inutile ici, et tu veux Pydantic.

JSON Schema: bon pour décrire, moins pratique pour valider/instancier en Python pur.

TypedDict: statique seulement, aucune validation runtime.

Dans un système critique Python: Pydantic est un compromis solide (lisible, strict, testable).


############################################################################################################################

# ÉTAPE 2 — SORTIES LLM “SALES” (CATALOGUE D’ÉCHECS)
## Objectif

Créer un catalogue réaliste de sorties LLM incorrectes (dicts + JSON strings) afin de:

tester la robustesse du pipeline (parse → sanitation → validation)

démontrer les risques concrets du “raw output”

fournir une base stable pour demo.py et tests/

Le but est d’avoir au moins 8 cas couvrant les erreurs les plus fréquentes:

JSON non parseable

champ obligatoire manquant

types incorrects (ex: "0,87" au lieu de 0.87)

label invalide

probability hors bornes

reason vide/trop courte

version invalide

champ inattendu

## Pourquoi c’est critique en production

En production, les sorties LLM “sales” arrivent:

même avec un prompt parfait

même avec un modèle “aligné”

même si ça marche 95% du temps

Et devine quoi: c’est le 5% restant qui te coûte un incident.

Ces cas doivent être:

reproductibles

testables

intégrés dans la CI (tests unitaires)

## Cas d’échecs (et pourquoi ça arrive vraiment)

- Cas 1 — JSON non parseable

Symptôme: guillemets cassés, virgule en trop, commentaire, bloc tronqué.
Pourquoi: le LLM “complète” un format, mélange du texte et du JSON, ou coupe en fin de génération.

- Cas 2 — Champ obligatoire manquant

Symptôme: request_id ou created_at absent.
Pourquoi: le LLM “oublie” un champ, surtout si le contexte est long ou si la réponse est résumée.

- Cas 3 — Mauvais type (float européen / string)

Symptôme: "0,87" ou "87%" au lieu de 0.87.
Pourquoi: influence locale (virgule décimale), ou “format humain” au lieu de “format machine”.

- Cas 4 — Label invalide

Symptôme: "Fraud", "FRAUDE", "Maybe"…
Pourquoi: traduction automatique, variation stylistique, ou volonté de nuancer (“peut-être”).

- Cas 5 — Probability > 1

Symptôme: 1.2, 120, 1.0001.
Pourquoi: confusion entre probabilité et pourcentage, ou arrondi/approximation.

- Cas 6 — Reason trop courte / vide

Symptôme: "", "OK", "RAS".
Pourquoi: le LLM privilégie la concision, ou répond “comme un humain” sans détails.

- Cas 7 — Version invalide

Symptôme: "1.2.3", "v1", "v1.2", "version 1.2.3".
Pourquoi: le LLM “décore” la version ou oublie le pattern strict.

- Cas 8 — Champ inattendu (extra field)

Symptôme: debug, internal_note, tool_trace, confidence_text.
Pourquoi: le LLM ajoute des infos “utiles” ou fuit une partie du raisonnement / tool output.

- Cas 9 — created_at invalide

Symptôme: "02/02/2026 01:00", "yesterday", "2026-13-40".
Pourquoi: format régional, langage naturel, date impossible.

- Cas 10 — Mauvaises clés (format drift)

Symptôme: requestId, prob, predicted_label.
Pourquoi: le LLM reformule les noms de champs pour “être plus clair”.

## Risques / pièges

Croire que ces cas sont “théoriques”: ils sont quotidiens en prod.

Se contenter d’un seul type d’erreur (ex: uniquement JSON cassé): il faut couvrir structure + types + sémantique.

Mélanger correction et validation ici: à cette étape, on collecte les échecs, on ne les corrige pas encore.

Alternatives possibles

Générer ces cas via fuzzing (property-based testing) plus tard.
Bonne idée, mais pour ce mini-projet, un catalogue manuel explicable est plus pédagogique.

Utiliser de vrais outputs LLM.
Interdit ici: on simule, on contrôle, on rend reproductible.



############################################################################################################################

# ÉTAPE 3 — STRATÉGIE “CORRIGER VS REJETER”

## Objectif

Définir une politique claire et défendable pour traiter des sorties LLM non conformes:

Corriger uniquement les erreurs mécaniques, non ambiguës, réversibles

Rejeter toute ambiguïté sémantique ou toute correction qui change le sens

Ne jamais réparer silencieusement: toute correction doit être tracée (liste d’actions)

**Cette étape introduit la “sanitation contrôlée”:**

- transformations minimales

- justifiées

- auditables

## Pourquoi c’est critique en production

Corriger aveuglément = créer des erreurs crédibles

Le pire en prod, ce n’est pas “ça plante”.
Le pire, c’est “ça passe mais c’est faux”.

**Exemples classiques:**

convertir "87%" en 0.87 sans savoir si l’intention était 87 ou 0.87

normaliser "Fraud" en "Fraude" sans être sûr du mapping souhaité

tronquer un champ texte trop long (perte d’info) ou remplir un champ manquant (invention)

**Une correction non justifiée:**

rend les bugs invisibles

pollue les données

produit des décisions métier incorrectes

complique les audits (santé/défense/industrie: bon courage)

**Le but n’est pas d’accepter plus, c’est de casser moins (correctement)**

Le pipeline doit:

- protéger l’aval

- refuser ce qui n’est pas sûr

- expliquer clairement pourquoi

## Politique de correction (règles)

✅ Corriger (mécanique, non ambigu)

- Trim des strings (espaces avant/après)

- Conversion d’un float depuis:

  - "0.87" (string numérique simple)

  - "0,87" (virgule décimale → point) uniquement si forme simple

- Conversion depuis "87%" → 0.87 (acceptable si et seulement si le pattern est strict % et que 0–100)

- Normalisation simple des labels:

  - "OK" → "OK"

  - "Fraude" → "Fraude"

  - "FRAUDE" / " fraude " → "Fraude" (normalisation casse + trim)

- created_at:

  - accepter ISO 8601 standard (avec ou sans Z)

  - (optionnel) convertir Z → +00:00 si nécessaire, sans inventer la date

**❌ Rejeter (ambigu, sémantique, dangereux)**

Champ obligatoire manquant (on n’invente pas)

Probabilité hors bornes après tentative raisonnable de conversion

Labels “peut-être”, “unknown”, “Fraud”, “MaybeFraud” (ambigu sémantiquement)

Champs inattendus (extra fields) → rejet (surface d’attaque et drift)

Dates en langage naturel ("yesterday", "today") ou format régional non fiable ("02/02/2026 01:00")

Changement de clés (prob au lieu de probability)
On ne “devine” pas les mappings. C’est du drift.

## Risques / pièges

Over-sanitization: vouloir sauver trop de cas et finir par accepter des données fausses.

Silent fixes: corriger sans tracer. Résultat: impossible à auditer.

Heuristiques non bornées: “si ça ressemble à…” = instable, non testable.

Règles qui changent sans versioning: la sanitation devient un second modèle probabiliste (ironie).

Alternatives possibles

Rejet total (aucune correction): plus simple, mais moins robuste en pratique (et ça peut bloquer des cas mécaniques).

Auto-réparation par LLM: tentant, mais tu rajoutes un composant probabiliste pour corriger un autre.
Dans un système critique, c’est un sketch.

Fuzzing + property-based tests: excellent en complément, mais après la base.


############################################################################################################################

# ÉTAPE 4 — VALIDATION FAIL-FAST

## Objectif

Implémenter validate_output(raw_output) qui applique une chaîne de sécurité déterministe:

Parse JSON si raw_output est une string

Applique la sanitation contrôlée (ÉTAPE 3)

Valide strictement via Pydantic (ÉTAPE 1)

Retourne un verdict structuré, sans jamais lever d’exception non gérée

Le système aval ne voit jamais une sortie LLM brute.

# Pourquoi c’est critique en production

Une erreur LLM ne doit jamais faire tomber:

- un worker

- une API

- un batch

- un orchestrateur

En systèmes critiques, une sortie invalide est une situation prévue:

- elle doit être capturée

- expliquée

- tracée

- puis rejetée proprement

Le “fail-fast” ici ne veut pas dire “crash”, mais:

- refuser vite

- avec une cause claire

- sans contaminer l’aval

## Risques / pièges

Laisser passer des exceptions (json.loads, model_validate, sanitizer) → crash.

Retourner des erreurs vagues (“invalid output”) → impossible à débugger.

Mélanger acceptation et correction silencieuse → données fausses acceptées.

Logger des données sensibles sans prudence (ici on logue surtout les erreurs et le type, pas un dump complet).

## Alternatives possibles

Rejet direct sans sanitation: plus simple, moins robuste (tu rejettes des cas mécaniques).

Tolérer des champs inconnus: plus “souple”, mais ouvre la porte au drift et aux fuites.

Auto-réparation par LLM: tu ajoutes un second composant probabiliste pour corriger le premier. Mauvais plan en critique.

############################################################################################################################

# ÉTAPE 5 — DÉMO EXÉCUTABLE


## Objectif

Fournir un script exécutable (demo.py) qui:

parcourt toutes les sorties LLM “sales”

appelle validate_output pour chaque cas

affiche clairement le verdict (accepted / rejected)

affiche les erreurs de manière lisible

ne plante jamais

termine avec exit code 0, même si 100% des cas sont rejetés

## Cette démo sert à:

prouver la robustesse du pipeline

montrer le comportement en conditions dégradées

rassurer un recruteur ou un reviewer technique

Pourquoi c’est critique en production

## En prod:

un batch ne doit pas s’arrêter à cause d’une sortie LLM invalide

un worker ne doit pas crasher parce qu’un JSON est mal formé

un incident doit être visible, pas destructeur

La démo montre que:

- chaque cas est isolé

- chaque erreur est contenue

- le système continue de fonctionner

C’est exactement ce qu’on attend dans:

industrie

santé

défense

finance

## Risques / pièges

Faire lever une exception non gérée dans la boucle → démonstration ratée.

Afficher des logs illisibles → personne ne comprend ce qui se passe.

Masquer les erreurs → fausse impression de robustesse.

Quitter avec exit code ≠ 0 → interprété comme un échec global par CI / orchestrateur.

## Alternatives possibles

Démo via notebook: joli, mais pas représentatif de la prod.

Démo via tests uniquement: utile, mais moins pédagogique pour un humain.

Logging structuré JSON: pertinent plus tard, ici on veut du lisible immédiat.

############################################################################################################################

# ÉTAPE 6 — TESTS MINIMAUX


## Objectif

Ajouter des tests unitaires minimaux pour verrouiller le comportement attendu du validateur:

**Cas valide:** entrée conforme → accepted

**Cas corrigé:** entrée mécaniquement corrigeable → accepted

**Cas rejeté:** entrée invalide/ambiguë → rejected

## Les tests prouvent que:

le pipeline ne crashe pas

la sanitation est contrôlée (corrige uniquement le mécanique)

la validation Pydantic est fail-fast (rejet clair)

## Pourquoi c’est critique en production

- Sans tests:

une “petite” modification de sanitation peut accepter des données fausses

une modification du schéma peut casser le parse/validator

tu ne détectes pas les regressions avant prod

- Dans un système critique, les tests sont le minimum syndical pour:

garantir des invariants

documenter le comportement

sécuriser l’évolution du code

## Risques / pièges

Tester uniquement des cas “happy path”.

Écrire des tests trop couplés aux messages exacts d’erreur (fragile).

Oublier le cas “corrigé”, alors que c’est le cœur de la politique ÉTAPE 3.

Ne pas couvrir la non-régression: validate_output ne doit jamais lever d’exception.

############################################################################################################################

## Bilan 

samples/bad_outputs.py
   |
   v
src/demo.py  ---------------------> src/validator.py
                                      |
                                      |-- _parse_raw_output (json.loads)
                                      |
                                      |-- src/sanitizer.py : sanitize_output
                                      |
                                      |-- src/schemas.py : FraudPredictionOutput (Pydantic)
                                      |
                                      v
                             verdict structuré (accepted/rejected)

tests/test_validator.py  ----> src/validator.py (même chemin)


## Détail par fichier (responsabilités)

- src/schemas.py

Déclare le contrat strict (types + contraintes)

extra="forbid": interdit les champs inconnus

Valide model_version (regex vMAJOR.MINOR.PATCH)

- samples/bad_outputs.py

Contient la liste BAD_OUTPUTS (8–10 cas sales)

Mélange dicts + JSON strings

Sert de carburant à la démo

- src/sanitizer.py

Applique des corrections mécaniques et non ambiguës

Ne “devine” jamais

Retourne SanitizeResult(sanitized, actions) pour tracer ce qui a été corrigé

- src/validator.py

Point d’entrée “prod”: validate_output(raw_output)

Jamais d’exception non gérée

Parse → sanitize → validate

Retourne un verdict structuré

- src/demo.py

Parcourt tous les cas

Affiche verdict + erreurs

ne plante jamais

exit code 0

- tests/test_validator.py

Vérifie 3 invariants:

un cas valide accepté

un cas corrigé accepté

un cas rejeté rejeté

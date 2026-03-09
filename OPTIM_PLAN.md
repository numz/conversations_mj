# Plan d'optimisation des outils Legifrance

## Historique des modifications

### Tir 5 — Fallback retry (REVERT)
- **Branche**: `feat/legifrance-tools`
- **Modification**: Ajout d'un fallback retry avec simplification de query (suppression stop words) dans `search_codes_lois.py` et `search_jurisprudence.py` + `core/query_fallback.py`
- **Résultat**: Composite **0.42** — REGRESSION
- **Action**: Revert complet, fichiers supprimés

### Tir 6 — Renforcement instructions LLM
- **Branche**: `feat/legifrance-tools`
- **Fichier**: `src/backend/conversations/configuration/llm/default.json`
- **Modification**: Réécriture de `_default` tool_instructions pour forcer l'usage des outils (SEARCH FIRST, ANSWER SECOND)
- **Résultat**: Composite **0.51**, tool usage 64% — AMELIORATION
- **Status**: ✅ Conservé

### Tir 7 — TITLE pour JORF/CIRC
- **Branche**: `feat/legifrance-tools`
- **Fichiers**:
  - `src/backend/chat/tools/legifrance/constants.py` — ajout `SEARCH_FIELD_TITLE`, `SEARCH_FIELD_NUM_ARTICLE`
  - `src/backend/chat/tools/legifrance/tools/search_admin.py` — `typeChamp: TITLE` pour JORF/CIRC au lieu de ALL
- **Résultat**: Composite **0.49**, résultats vides 67→15 — AMELIORATION du bruit
- **Status**: ✅ Conservé
- **Note**: Variance d'échantillonnage (pas de seed) rend la comparaison directe difficile

### Tir 7bis — Ajout seed pour reproductibilité
- **Branche**: `feat/eval-legifrance`
- **Fichiers**:
  - `src/eval/dataset.py` — `seed` param dans `sample_stratified()` avec `random.Random(seed)`
  - `src/eval/run.py` — `--seed` CLI argument
- **Status**: ✅ Conservé

### Tir 8a — BASELINE SANS NUM_ARTICLE (seed 42) ⭐ REFERENCE
- **But**: Établir une baseline reproductible avant la modif NUM_ARTICLE
- **Config**: seed 42, --sample 2, --api, 22 questions
- **Résultat**: Composite **0.50**
- **Détail scores**:
  - Retrieval articles: 1.00/3
  - Retrieval jurisprudence: 2.59/3
  - Sélection outil: 0.86/2
  - Qualité juridique: 2.00/5
  - Hallucination: 1.55/3
- **Fichier résultats**: `src/eval/output/results_20260309_023816.jsonl`

### Tir 8b — AVEC NUM_ARTICLE (seed 42)
- **Branche**: `feat/legifrance-tools`
- **Fichier**: `src/backend/chat/tools/legifrance/api.py`
- **Modification**: `search_code_article()` utilise `typeChamp: NUM_ARTICLE` au lieu de `ALL`
- **Validation**: Testé avec art. 1242 Code civil et art. L121-1 Code consommation — OK
- **Résultat**: Composite **0.42** (seed 42, 22 questions, 0 erreurs)
- **Détail scores**:
  - Retrieval articles: 0.82/3
  - Retrieval jurisprudence: 2.32/3
  - Sélection outil: 0.77/2
  - Qualité juridique: 1.45/5
  - Hallucination: 1.41/3
- **Fichier résultats**: `src/eval/output/results_20260309_021312.jsonl`
- **Comparaison A/B détaillée**:
  - Diff composite: -0.08 (non significatif)
  - `search_code_article_by_number` utilisé dans 7/22 questions
  - Impact réel positif: QRC_droit_public_2025::9 — 39 calls→11 calls, score +0.20 (NUM_ARTICLE a cassé la boucle)
  - Impact neutre: questions_reponses_droit_civil::12 — même score, mais 2 appels au lieu de 5
  - Les diffs > 0.10 sur les autres questions = **bruit LLM** (questions sans appel outil dans les 2 runs)
- **Conclusion**: NUM_ARTICLE est techniquement correct (moins de bruit, moins de boucles), la diff globale -0.08 est du bruit LLM
- **Status**: ✅ Conservé

---

## Optimisations planifiées (par priorité)

Basées sur l'analyse de la doc PISTE API (`description-des-tris-et-filtres-de-l-api.xlsx`).

### 1. ✅ `NUM_ARTICLE` pour `search_code_article` (FAIT — Tir 8)
- **Fichier**: `api.py` → `search_code_article()`
- **Avant**: `typeChamp: ALL` + `EXACTE`
- **Après**: `typeChamp: NUM_ARTICLE` + `EXACTE`
- **Impact**: Cible uniquement l'index numéro d'article, élimine le bruit

### 2. `getArticleWithIdAndNum` — accès direct article
- **Fichier**: `api.py` + nouveau tool ou modification de `search_code_article_by_number.py`
- **Endpoint**: `/consult/getArticleWithIdAndNum` avec `id=LEGITEXT...` + `num="1242"`
- **Avantage**: Un seul appel API au lieu de search + getArticle (2 appels)
- **Prérequis**: Mapper nom du code → LEGITEXT ID (via `list_codes`)

### 3. `NUM_DEC` / `NUM_AFFAIRE` pour jurisprudence
- **Fichier**: `tools/search_jurisprudence.py` + `core/criteria.py`
- **Modification**: Détecter quand la query contient un numéro de décision et utiliser:
  - CONSTIT: `typeChamp: NUM_DEC`
  - CETAT: `typeChamp: NUM_DEC`
  - JURI: `typeChamp: NUM_AFFAIRE`
- **Impact**: Recherche ciblée par numéro au lieu de full-text

### 4. `TITLE` pour LODA
- **Fichier**: `tools/search_codes_lois.py`
- **Modification**: Quand `type_source=LODA`, utiliser `typeChamp: TITLE` au lieu de `ALL`
- **Impact**: Réduit le bruit (30K→671 pour "Constitution")
- **Déjà validé**: Test Docker réussi

### 5. `ABSTRATS` / `RESUMES` pour jurisprudence thématique
- **Fichier**: `tools/search_jurisprudence.py`
- **Modification**: Pour les recherches thématiques (pas de numéro), utiliser `ABSTRATS` ou `RESUMES` au lieu de `ALL`
- **Champs disponibles**: CETAT (`ABSTRATS`, `RESUMES`), JURI (`ABSTRATS`, `RESUMES`)
- **Impact**: Résumés contiennent les mots-clés juridiques qualifiés

### 6. Filtres `NATURE_CONSTIT` pour QPC
- **Fichier**: `tools/search_jurisprudence.py`
- **Modification**: Auto-détecter "QPC" dans la query → ajouter filtre `NATURE_CONSTIT`
- **Filtres disponibles**: `NATURE_CONSTIT`, `SOLUTION_CONSTIT`, `TITRE_DEFEREE`, `NUM_LOI`

### 7. Filtres `NATURE` / `MINISTERE` pour JORF
- **Fichier**: `tools/search_admin.py`
- **Modification**: Si la query mentionne "décret", "arrêté", "ordonnance" → filtre `NATURE`
- **Filtres disponibles**: `NATURE`, `MINISTERE`, `EMETTEUR`, `DECORATION`, `DELEGATION`

### 8. `getJoWithNor` — accès direct par NOR
- **Fichier**: `api.py` + `tools/search_admin.py`
- **Endpoint**: `/consult/getJoWithNor` avec `nor="MAEJ9830052D"`
- **Avantage**: Accès instantané quand le NOR est connu (1 appel vs search+consult)

### 9. `ARTICLE` pour recherche dans contenu d'articles
- **Fichier**: `tools/search_codes_lois.py`
- **Modification**: Nouveau paramètre `search_in_article_content=True` → `typeChamp: ARTICLE`
- **Champs disponibles**: CODE (`ARTICLE`), LODA (`ARTICLE`), JORF (`ARTICLE`)

### 10. `IDCC` comme champ de recherche pour conventions
- **Fichier**: `tools/search_conventions.py`
- **Modification**: Quand l'utilisateur donne un numéro IDCC, utiliser `typeChamp: IDCC`
- **Champ disponible**: KALI (`IDCC`)

---

## Problèmes identifiés (tir 8, seed 42)

| Problème | Questions | Impact | Solution proposée |
|----------|-----------|--------|-------------------|
| **Pas d'appel outil (59%)** | 13/22 questions avec tool_selection=0 | Levier principal | Renforcer encore les instructions |
| **Boucles massives** | QRC_public_2025::9 (39 calls avant NUM_ARTICLE) | Score faible | NUM_ARTICLE a aidé (39→11 calls) |
| **Réponses vides** | CP_Civil_2023::3, NS_open_data::9 (score 0.00) | Perte sèche | Diagnostic streaming/timeout |
| **Hallucinations sévères (h=0)** | 7/22 questions | Score plombé | Forcer l'usage des outils |
| **Variance LLM** | Écarts ±0.50 entre 2 runs identiques | Comparaison difficile | Seed aide mais LLM reste non déterministe |

### Leçon clé du tir 8
Le **problème dominant n'est pas la qualité des requêtes API** mais le fait que le LLM **n'appelle pas les outils** dans 59% des cas. Les optimisations API (NUM_ARTICLE, TITLE, etc.) n'ont d'impact que sur les ~40% de questions où les outils sont effectivement appelés.

---

## Workflow de test

1. Modifier dans `feat/legifrance-tools`
2. Tester dans Docker: `docker exec conversations-app-dev-1 python -c "..."`
3. Commit
4. Merge dans `integration/all-features`
5. `docker restart conversations-app-dev-1`
6. Lancer eval: `python -m src.eval.run --api --sample 2 --seed 42`
7. Comparer composite score avec tir précédent

## Conventions

- **Pas de Co-Authored-By** dans les commits
- **`git -c commit.gpgsign=false`** pour tous les commits
- **tool_instructions en anglais** dans default.json
- Code legifrance → `feat/legifrance-tools`
- Code eval → `feat/eval-legifrance`

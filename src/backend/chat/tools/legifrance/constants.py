"""Constants for Legifrance API and Tools."""

from __future__ import annotations

# --- General URLs ---
LEGIFRANCE_UI_BASE_URL = "https://www.legifrance.gouv.fr"
DEFAULT_API_BASE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
DEFAULT_OAUTH_URL = "https://oauth.piste.gouv.fr/api/oauth/token"

# --- Search Fonds (Databases) ---
FOND_CODE_ETAT = "CODE_ETAT"
FOND_CODE_DATE = "CODE_DATE"
FOND_JURI = "JURI"
FOND_CETAT = "CETAT"
FOND_JUFI = "JUFI"
FOND_CNIL = "CNIL"
FOND_ACCO = "ACCO"
FOND_CIRC = "CIRC"
FOND_LODA_DATE = "LODA_DATE"
FOND_KALI = "KALI"
FOND_CONSTIT = "CONSTIT"
FOND_JORF = "JORF"

# --- Fond Prefixes (for startswith checks) ---
FOND_PREFIX_LODA = "LODA"
FOND_PREFIX_CODE = "CODE"

# --- Facet Names (Filters) ---
FACET_NOM_CODE = "NOM_CODE"
FACET_ARTICLE_LEGAL_STATUS = "ARTICLE_LEGAL_STATUS"
FACET_DATE_VERSION = "DATE_VERSION"
FACET_DATE_DECISION = "DATE_DECISION"
FACET_NUMERO_DECISION = "NUMERO_DECISION"
FACET_DATE_SIGNATURE = "DATE_SIGNATURE"
FACET_IDCC = "IDCC"
FACET_LEGAL_STATUS = "LEGAL_STATUS"
FACET_NATURE_DELIB = "NATURE_DELIB"
FACET_NOR = "NOR"
FACET_DATE_DELIB = "DATE_DELIB"

# --- Sort Keys ---
SORT_PERTINENCE = "PERTINENCE"
SORT_DATE_DESC = "DATE_DESC"
SORT_DATE_ASC = "DATE_ASC"
SORT_PUBLICATION_DATE_DESC = "PUBLICATION_DATE_DESC"
SORT_PUBLICATION_DATE_ASC = "PUBLICATION_DATE_ASC"
SORT_SIGNATURE_DATE_DESC = "SIGNATURE_DATE_DESC"
SORT_DATE_DECISION_DESC = "DATE_DECISION_DESC"
SORT_TITLE_ASC = "TITLE_ASC"

# --- API Endpoints ---
ENDPOINTS = {
    "search": "/search",
    "list_codes": "/consult/listCodes",
    "consult_acco": "/consult/acco",
    "consult_circulaire": "/consult/circulaire",
    "consult_cnil": "/consult/cnil",
    "consult_code": "/consult/code",
    "consult_article": "/consult/getArticle",
    "consult_jorf": "/consult/jorf",
    "consult_juri": "/consult/juri",
    "consult_loda": "/consult/lawDecree",
    "consult_kali_article": "/consult/kaliArticle",
    "consult_kali_text": "/consult/kaliText",
    "consult_article_id_num": "/consult/getArticleWithIdAndNum",
    "list_code_legacy": "/list/code",
}

# --- Search Defaults ---
DEFAULT_PAGE_NUMBER = 1
DEFAULT_PAGE_SIZE = 5
DEFAULT_OPERATOR = "ET"
DEFAULT_PAGINATION_TYPE = "DEFAUT"
PAGINATION_TYPE_ARTICLE = "ARTICLE"

# --- Search Field Types ---
SEARCH_FIELD_ALL = "ALL"

# --- Search Types ---
SEARCH_TYPE_EXACTE = "EXACTE"
SEARCH_TYPE_UN_DES_MOTS = "UN_DES_MOTS"

# --- Legal Status Values ---
LEGAL_STATUS_VIGUEUR = "VIGUEUR"

# --- UI Path Segments for URL Generation ---
UI_PATH_CODES_ARTICLE = "codes/article_lc"
UI_PATH_CODES_TEXTE = "codes/texte_lc"
UI_PATH_JURI = "juri/id"
UI_PATH_JUFI = "jufi/id"
UI_PATH_CNIL = "cnil/id"
UI_PATH_ACCO = "acco/id"
UI_PATH_CIRC = "circulaire/id"
UI_PATH_LODA = "loda/id"
UI_PATH_JORF = "jorf/id"
UI_PATH_CONS = "cons/id"
UI_PATH_CONV_COLL = "conv_coll/id"
UI_PATH_CONV_COLL_ARTICLE = "conv_coll/article"
UI_PATH_CETA = "ceta/id"

# --- Default Fallback Strings ---
DEFAULT_TITLE_FALLBACK = "Document sans titre"
DEFAULT_SECTION_TITLE = "Section sans titre"
DEFAULT_NATURE_FALLBACK = "Code/Loi"
NO_TITLE_FALLBACK = "No Title"
ARTICLE_TITLE_FALLBACK = "Article"

# --- Type Source Values ---
TYPE_SOURCE_CODE = "CODE"
TYPE_SOURCE_CODE_DATE = "CODE_DATE"
TYPE_SOURCE_LODA = "LODA"
TYPE_SOURCE_KALI = "KALI"
TYPE_SOURCE_ACCO = "ACCO"
TYPE_SOURCE_JORF = "JORF"
TYPE_SOURCE_CIRC = "CIRC"
TYPE_SOURCE_CNIL = "CNIL"

# --- Juridiction Types ---
JURIDICTION_JUDICIAIRE = "JUDICIAIRE"
JURIDICTION_ADMINISTRATIF = "ADMINISTRATIF"
JURIDICTION_CONSTITUTIONNEL = "CONSTITUTIONNEL"
JURIDICTION_FINANCIER = "FINANCIER"

# --- ID Prefixes ---
ID_PREFIX_LEGIARTI = "LEGIARTI"
ID_PREFIX_LEGITEXT = "LEGITEXT"
ID_PREFIX_JURITEXT = "JURITEXT"
ID_PREFIX_JUFITEXT = "JUFITEXT"
ID_PREFIX_CNILTEXT = "CNILTEXT"
ID_PREFIX_ACCOTEXT = "ACCOTEXT"
ID_PREFIX_JORFTEXT = "JORFTEXT"
ID_PREFIX_JORFARTI = "JORFARTI"
ID_PREFIX_CONSTEXT = "CONSTEXT"
ID_PREFIX_CETATEXT = "CETATEXT"
ID_PREFIX_KALITEXT = "KALITEXT"
ID_PREFIX_KALIARTI = "KALIARTI"
ID_PREFIX_CEHR = "CEHR"

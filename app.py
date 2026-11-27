"""
Rent or Buy in Geneva — application Streamlit.
Lancer avec :  streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from datetime import date, timedelta

import csv
import importlib
import re
from pathlib import Path

import graphique as _graphique
import marche as _marche
import model as _model
import validation as _validation

for _mod in (_model, _marche, _graphique, _validation):   # évite qu'une ancienne version reste en mémoire après une mise à jour
    importlib.reload(_mod)

from graphique import graphique_anime
from marche import CSS as CSS_MARCHE, bandeau, serie_bns, taux_hypothecaires
from validation import calcul_main_annee1, tests_coherence
from model import Hypotheses, amortissement_minimum, annee_equilibre, controle_financement, simuler

st.set_page_config(page_title="Acheter ou louer à Genève ?", page_icon="🏠", layout="wide")

# Paramètres par défaut préparés à partir des données publiques brutes (data/preparer_donnees.py)
with open(Path(__file__).resolve().parent / "data" / "parametres.csv", encoding="utf-8") as _f:
    PARAMS = {r["parametre"]: float(r["valeur"]) for r in csv.DictReader(_f)}

BLEU, ORANGE = "#338ced", "#e76624"   # Acheter, Louer (palette validée daltonisme, mode sombre)
TEXTE, TEXTE2, GRILLE = "#efefef", "#b0b0b0", "#3d4148"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp td, .stApp th,
.stApp div[data-testid="stMetricValue"], .stApp div[data-testid="stMarkdownContainer"],
.stApp div[data-baseweb="select"], .stApp div[data-baseweb="tab-list"] button {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  letter-spacing: -0.005em;}
.hero h1 {letter-spacing: -0.02em; font-weight: 800;}
.footer {margin-top: 48px; padding: 18px 22px; border-radius: 14px; background: rgba(30,33,38,.90);
         border: 1px solid #474c55; color: #b0b0b0; font-size: .82rem; line-height: 1.55;}
.footer b {color: #efefef;}
.block-container {padding-top: 2rem; max-width: 1150px;}
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"], [data-testid="stAppViewContainer"], [data-testid="stMain"] {background: transparent;}
.stApp {background:
         linear-gradient(rgba(20,22,26,.18), rgba(20,22,26,.30)),
         url("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Jet_d%27eau_from_Lake_Geneva.jpg/1920px-Jet_d%27eau_from_Lake_Geneva.jpg") center 35% / cover fixed no-repeat, #2b2e34;}
.hero {position: relative; color: #fff; border-radius: 20px; padding: 46px 38px 40px 38px;
       margin-bottom: 26px; min-height: 270px; overflow: hidden;
       background: linear-gradient(100deg, rgba(10,28,52,.70) 0%, rgba(10,28,52,.35) 50%, rgba(10,28,52,0) 100%);
       border: 1px solid rgba(255,255,255,.18); backdrop-filter: blur(1px);
       box-shadow: 0 10px 30px rgba(0,0,0,.25);}
.block-container p, .block-container span, .block-container label {text-shadow: 0 1px 6px rgba(0,0,0,.55);}
.section {background: rgba(30,33,38,.82); border-radius: 14px; padding: 8px 16px 8px 8px; width: fit-content;}
div[data-baseweb="tab-list"] {background: rgba(30,33,38,.85); border-radius: 12px; padding: 4px 8px;}
div[data-baseweb="tab-panel"] {background: rgba(30,33,38,.90); border-radius: 14px; padding: 16px 18px;}
div[data-testid="stExpander"] details {background: rgba(30,33,38,.90); border-radius: 12px;}
div[data-testid="stAlert"] {background: rgba(30,33,38,.88); border-radius: 12px;}
.hero h1, .hero p {text-shadow: 0 2px 10px rgba(0,0,0,.45);}
.hero .credit {position: absolute; right: 14px; bottom: 8px; font-size: .68rem; color: rgba(255,255,255,.7);}
.hero .credit a {color: rgba(255,255,255,.7);}
.hero h1 {color: #fff; font-size: 2.4rem; margin: 0 0 8px 0; padding: 0; line-height: 1.2;}
.hero p {color: #dbe7f7; font-size: 1.02rem; margin: 0; max-width: 760px;}
.chips {margin-top: 16px;}
.chip {display: inline-block; background: rgba(255,255,255,.14); color: #fff; border-radius: 999px;
       padding: 4px 12px; font-size: .82rem; margin: 0 6px 6px 0;}
.section {display: flex; align-items: center; gap: 12px; margin: 30px 0 12px 0;}
.section .num {background: #24364d; color: #8cc0f5; font-weight: 700; border-radius: 10px;
               width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;}
.section .titre {font-size: 1.35rem; font-weight: 700; color: #efefef;}
div[data-testid="stMetric"] {background: #363a41; border: 1px solid #474c55; border-radius: 14px;
       padding: 14px 18px;}
div[data-testid="stMetricLabel"] p {color: #b0b0b0; font-size: .86rem;}
div[data-testid="stMetricValue"] {font-size: 1.55rem; color: #efefef;}
.checks {display: flex; flex-wrap: wrap; gap: 10px; margin: 6px 0 4px 0;}
.check {border-radius: 12px; padding: 10px 14px; font-size: .92rem; border: 1px solid;}
.check.ok {background: #1f3a2a; border-color: #1f5a37; color: #8be0a9;}
.check.ko {background: #4a2526; border-color: #6b2a2c; color: #f5a3a3;}
.verdict {border-radius: 16px; padding: 22px 26px; margin: 4px 0 18px 0; border: 1px solid #474c55;}
.verdict .big {font-size: 1.6rem; font-weight: 700; color: #efefef; line-height: 1.25;}
.verdict .small {color: #b5b5b5; margin-top: 6px; font-size: 1rem;}
.verdict.achat {background: #24364d; border-left: 6px solid #338ced;}
.verdict.loc {background: #45301f; border-left: 6px solid #e76624;}
.etapes {display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 6px;}
.etape {background: #363a41; border: 1px solid #474c55; border-radius: 14px; padding: 18px;}
.etape b {display: block; color: #8cc0f5; margin-bottom: 4px;}
section[data-testid="stSidebar"] h2 {font-size: 1.02rem; color: #8cc0f5; margin-top: .6rem;}
</style>
""", unsafe_allow_html=True)
st.markdown(f"<style>{CSS_MARCHE}</style>", unsafe_allow_html=True)


DOSSIER_DATA = Path(__file__).resolve().parent / "data"
FICHIERS_BRUTS = [
    ("Taux hypothécaires (BNS)", "bns_hypotheques_zikrepro.csv"),
    ("Obligations de la Confédération (BNS)", "bns_obligations_confederation.csv"),
    ("Prix des appartements (OCSTAT)", "ocstat_prix_ppe.csv"),
    ("Loyers (OCSTAT)", "ocstat_loyers.csv"),
    ("Frais et règles bancaires", "frais_et_regles.csv"),
    ("Casatax (Genève)", "casatax.csv"),
]


def _avec_liens(df):
    """Sépare le texte de la source et son lien, pour afficher un lien cliquable."""
    if "source" in df.columns:
        df = df.copy()
        df["lien"] = df["source"].map(lambda t: (re.findall(r"https?://\S+", str(t)) or [None])[0])
        df["source"] = df["source"].map(lambda t: re.sub(r"\s*https?://\S+", "", str(t)).strip(" ;,") or "voir le lien")
    return df


@st.dialog("Les données utilisées", width="large")
def fenetre_donnees():
    st.markdown("Toutes les hypothèses par défaut viennent de **sources publiques**. "
                "Voici les chiffres bruts, puis les paramètres calculés à partir d'eux.")
    onglets = st.tabs(["Paramètres calculés"] + [nom for nom, _ in FICHIERS_BRUTS])
    with onglets[0]:
        p = pd.read_csv(DOSSIER_DATA / "parametres.csv")
        p = p.rename(columns={"parametre": "Paramètre", "valeur": "Valeur", "unite": "Unité",
                              "formule": "Calcul", "source": "source"})
        st.dataframe(_avec_liens(p), hide_index=True, use_container_width=True,
                     column_config={"lien": st.column_config.LinkColumn("Lien", display_text="ouvrir")})
        st.caption("Ces valeurs sont calculées à partir des données brutes (onglets suivants) et préremplies dans l'outil. "
                   "Les taux BNS sont en plus relus en direct à chaque visite.")
    for onglet, (nom, fichier) in zip(onglets[1:], FICHIERS_BRUTS):
        with onglet:
            d = pd.read_csv(DOSSIER_DATA / "brut" / fichier)
            st.dataframe(_avec_liens(d), hide_index=True, use_container_width=True,
                         column_config={"lien": st.column_config.LinkColumn("Lien", display_text="ouvrir")})
            st.download_button("Télécharger ce fichier (CSV)", (DOSSIER_DATA / "brut" / fichier).read_bytes(),
                               fichier, "text/csv", key=f"dl_{fichier}")
    if st.button("Fermer", type="primary", key="fermer_donnees"):
        st.rerun()


@st.dialog("Vérification du calcul", width="large")
def fenetre_verification(h):
    st.markdown("**1. L'année 1 refaite à la main**, formule par formule, avec vos chiffres, "
                "puis comparée au résultat de l'outil.")
    lignes = calcul_main_annee1(h)
    tab = pd.DataFrame([{"Étape": n, "Formule": f, "Calcul à la main": chf(m), "Outil": chf(o),
                         "": "✓" if abs(m - o) < 1 else "✗"} for n, f, m, o in lignes])
    st.dataframe(tab, hide_index=True, use_container_width=True)
    ok = all(abs(m - o) < 1 for _, _, m, o in lignes)
    (st.success if ok else st.error)("Le calcul à la main et l'outil donnent les mêmes résultats."
                                     if ok else "Différence entre le calcul à la main et l'outil.")
    st.markdown("**2. Tests de cohérence** : l'outil réagit-il dans le bon sens quand on change une hypothèse ?")
    tests = tests_coherence(h)
    for txt, r in tests:
        st.markdown(f"{'✅' if r else '❌'} {txt}")
    st.caption(f"{sum(r for _, r in tests)} tests réussis sur {len(tests)}.")
    if st.button("Fermer", type="primary", key="fermer_verif"):
        st.rerun()


def sources_et_methode():
    t5, t10 = TAUX_BNS["Fixe 5 ans"], TAUX_BNS["Fixe 10 ans"]
    d_obl = ".".join(reversed(oblig["date"].split("-"))) if oblig else "26.11.2026"
    with st.expander("Sources et méthode"):
        st.markdown(f"""
**Toutes les hypothèses par défaut viennent de sources publiques.** L'utilisateur peut les modifier dans la barre de gauche.

| Hypothèse | Valeur par défaut | Source publique | Comment on l'obtient |
|---|---|---|---|
| Taux hypothécaire fixe 5 ans | {t5:.2f} % | Banque nationale suisse (BNS), [data.snb.ch](https://data.snb.ch), série *zikrepro* | Moyenne des taux publiés pour les nouvelles hypothèques, {MOIS_TAUX}. Lu automatiquement. |
| Taux hypothécaire fixe 10 ans | {t10:.2f} % | BNS, série *zikrepro* | Idem. |
| Hausse des prix de l'immobilier | {PARAMS["hausse_prix"]:.2f} % / an | Office cantonal de la statistique (OCSTAT), statistique des transactions immobilières | Prix médian au m² des appartements non neufs à Genève : 8 535 CHF (2016) → 10 853 CHF (2024), soit (10 853 / 8 535)^(1/8) − 1. |
| Hausse des loyers | {PARAMS["hausse_loyers"]:.2f} % / an | OCSTAT, statistique cantonale des loyers | Loyers libres non neufs à Genève : +1,8 % (mai 2024 → mai 2025) et +1,3 % (mai 2025 → mai 2026). Moyenne géométrique des deux. |
| Rendement de l'épargne | {REND_DEFAUT:.2f} % | BNS, série *rendoblid* | Rendement des obligations de la Confédération à 10 ans (placement sans risque), {d_obl}. Lu automatiquement. |
| Frais d'achat | {PARAMS["frais_achat"]:.1f} % du prix | Loi genevoise sur les droits d'enregistrement (rsGE D 3 30) | Droits d'enregistrement 3 % + registre foncier 0,3 % + notaire 0,6 % (milieu de la fourchette 0,5–0,7 %). |
| Frais de vente | 3 % du prix | Pratique du marché | Commission de courtage usuelle (2 à 3 %). |
| Entretien | 1 % de la valeur / an | Règles des banques suisses (p. ex. calculateur UBS) | Valeur utilisée par les banques pour les frais d'entretien. |
| Casatax (résidence principale) | −{PARAMS["casatax_reduction"]:,.0f} CHF de droits d'enregistrement si prix ≤ {PARAMS["casatax_plafond"]:,.0f} CHF | Loi genevoise sur les droits d'enregistrement, art. 8A ; règlement rsGE D 3 30.03 (montants 2026) | Réduction = min(20 924 CHF ; 3 % du prix). La réduction de moitié des frais de cédule hypothécaire n'est pas comptée (calcul prudent). |
| Règles de financement | 20 % d'apport, charges ≤ 1/3 du revenu au taux théorique de 5 %, dette ramenée à 2/3 du prix en 15 ans | Directives de l'Association suisse des banquiers ; calculateur UBS | Appliquées telles quelles dans « Votre financement est-il possible ? ». |
| Bandeau défilant | SARON, obligations 10 ans, EUR/CHF, USD/CHF, GBP/CHF | BNS, séries *zimoma*, *rendoblid*, *devkum* | Dernières valeurs publiées, relues toutes les 3 heures. |

**Préparation des données** : chaque paramètre est calculé à partir des chiffres bruts publiés par les sources (formules ci-dessus). Cliquez sur **« Voir les données »** pour afficher les données brutes, les calculs et les liens vers les sources.

**Méthode de calcul**
- **Même départ** : les deux ménages ont la même épargne. L'acheteur paie l'apport et les frais d'achat avec, et place le reste ; le locataire place tout.
- **Même budget** : chaque année, celui dont le logement coûte le moins place la différence au rendement de l'épargne.
- **Acheteur** : paie les intérêts, le remboursement annuel et l'entretien. Patrimoine = valeur du bien − frais de vente − dette restante + épargne placée.
- **Locataire** : paie le loyer, qui augmente chaque année. Patrimoine = épargne placée.
- **Année d'équilibre** : première année à partir de laquelle le patrimoine de l'acheteur reste supérieur à celui du locataire.

**Limites**
- Pas d'impôts (valeur locative, déductions, impôt sur le gain immobilier, impôt sur la fortune) ni de 2e pilier.
- Taux hypothécaire constant (renouvellement supposé au même taux).
- Hausses des prix et des loyers constantes, tirées du passé : elles ne prédisent pas l'avenir.
- Pas de risque : le rendement du placement et la hausse des prix sont appliqués chaque année comme s'ils étaient garantis.
""")


def pied_de_page():
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("Voir les données", use_container_width=True, key="btn_donnees"):
        fenetre_donnees()
    h_courant = globals().get("h")
    if c2.button("Vérifier le calcul", use_container_width=True, key="btn_verif", disabled=h_courant is None,
                 help=None if h_courant else "Remplissez d'abord vos chiffres (ou cliquez sur « Voir une démo »)."):
        fenetre_verification(h_courant)
    sources_et_methode()
    st.markdown(f"""
<div class="footer">
  <b>Avertissement.</b> Cet outil a été développé à des fins pédagogiques dans le cadre d'un projet universitaire.
  Les résultats reposent sur des hypothèses simplifiées (pas d'impôts, taux constant, hausse des prix et des loyers
  constante) et ne constituent en aucun cas un conseil financier, fiscal ou hypothécaire. Les conditions réelles
  dépendent de votre banque et de votre situation personnelle : consultez un professionnel avant toute décision.<br>
  Données : Banque nationale suisse, Office cantonal de la statistique (Genève). Taux hypothécaires : {MOIS_TAUX}.
</div>""", unsafe_allow_html=True)

def section(num, titre):
    st.markdown(f'<div class="section"><div class="num">{num}</div><div class="titre">{titre}</div></div>',
                unsafe_allow_html=True)


def chf(x: float) -> str:
    return f"{x:,.0f} CHF".replace(",", "'")


# ---------------------------------------------------------------- Démo
DEMO = {"prix": 1_200_000, "loyer": 2_700, "revenu": 220_000, "epargne": 300_000,
        "emprunt": 960_000, "amort": None}


def charger_demo():
    for k, v in DEMO.items():
        st.session_state[k] = v


def effacer():
    for k in DEMO:
        st.session_state[k] = None


# ---------------------------------------------------------------- Saisie
sb = st.sidebar
b1, b2 = sb.columns(2)
b1.button("Voir une démo", on_click=charger_demo, type="primary", use_container_width=True)
b2.button("Effacer", on_click=effacer, use_container_width=True)
sb.header("1. Vos deux logements")
prix = sb.number_input("Prix du logement à acheter (CHF)", min_value=0, value=None, key="prix", step=10_000,
                       placeholder="ex. 1200000")
loyer = sb.number_input("Loyer du logement à louer (CHF/mois)", min_value=0, value=None, key="loyer", step=50,
                        placeholder="ex. 2700")

sb.header("2. Votre argent")
revenu = sb.number_input("Revenu brut du ménage (CHF/an)", min_value=0, value=None, key="revenu", step=5_000,
                         placeholder="ex. 220000")
epargne = sb.number_input("Combien avez-vous d'épargne ? (CHF)", min_value=0, value=None, key="epargne", step=5_000,
                          placeholder="ex. 300000",
                          help="Tout ce que vous pouvez mettre dans l'achat : apport et frais. Le reste est placé.")

sb.header("3. Votre hypothèque")
emprunt = sb.number_input("Combien empruntez-vous ? (CHF)", min_value=0, value=None, key="emprunt", step=10_000,
                          placeholder="ex. 960000",
                          help="Les banques prêtent au maximum 80 % du prix.")
if prix and emprunt is not None:
    apport_calc = prix - emprunt
    part = apport_calc / prix if prix else 0
    sb.caption(f"➡️ Votre apport : **{chf(apport_calc)}** ({part:.0%} du prix) "
               f"· emprunt maximum : {chf(0.8 * prix)}")
# Taux moyens publiés pour les nouvelles hypothèques : BNS, cube zikrepro (D0 = "M" moyenne,
# D1 = "50" fixe 5 ans / "10" fixe 10 ans), lus en direct. Valeurs de secours : septembre 2026.
TAUX_BNS, MOIS_TAUX = taux_hypothecaires({"Fixe 5 ans": round(PARAMS["taux_fixe_5_ans"], 2),
                                            "Fixe 10 ans": round(PARAMS["taux_fixe_10_ans"], 2)})
type_hypo = sb.selectbox("Type d'hypothèque", list(TAUX_BNS), index=1)
taux = sb.number_input("Taux hypothécaire (%)", min_value=0.0, max_value=15.0,
                       value=TAUX_BNS[type_hypo], step=0.05, format="%.2f",
                       key=f"taux_{type_hypo}",
                       help=f"Taux moyen des nouvelles hypothèques publié par la BNS ({MOIS_TAUX}). "
                            "Modifiez-le si votre banque vous propose un autre taux.")
amort_min = amortissement_minimum(prix, emprunt) if prix and emprunt is not None else None
amort = sb.number_input("Combien remboursez-vous par an ? (CHF)", min_value=0, value=None, key="amort", step=1_000,
                        placeholder=f"minimum {amort_min:,.0f}".replace(",", "'") if amort_min is not None else "ex. 10667",
                        help="Laissez vide pour appliquer le minimum des banques : "
                             "la dette redescend à 2/3 du prix en 15 ans.")
duree_amort = sb.slider("Pendant combien d'années remboursez-vous ?", 1, 40, 15)

sb.header("4. Votre projet")
horizon = sb.slider("Combien d'années comptez-vous rester ?", 1, 40, 30)
residence = sb.checkbox("Ce sera ma résidence principale (au moins 3 ans)", value=True, key="residence",
                        help="À Genève, l'achat de sa résidence principale donne droit à Casatax : une réduction "
                             f"des droits d'enregistrement de {PARAMS['casatax_reduction']:,.0f} CHF au maximum, si le prix "
                             f"ne dépasse pas {PARAMS['casatax_plafond']:,.0f} CHF (montants 2026).".replace(",", "'"))

sb.divider()
sb.caption("Hypothèses (préremplies, modifiables)")
# Valeurs par défaut tirées de données publiques (voir README) :
# Toutes ces valeurs sont calculées par data/preparer_donnees.py et lues dans data/parametres.csv :
# - hausse des prix : OCSTAT, appartements PPE non neufs, prix médian au m2 : 8 535 CHF (2016) -> 10 853 CHF (2024)
# - hausse des loyers : OCSTAT, loyers libres non neufs, +1,8 % (2024-25) et +1,3 % (2025-26) -> 1,5 % par an
# - rendement : BNS, obligations de la Confédération à 10 ans (dernière valeur, lue en direct ; 0,575 % au 26.11.2026)
# - frais d'achat : droits d'enregistrement 3 % (LDE, Genève) + registre foncier 0,3 % + notaire 0,6 %
oblig = serie_bns("rendoblid", (("D0", "10J0"),), (date.today() - timedelta(days=60)).isoformat())
REND_DEFAUT = round(float(oblig["valeur"]), 2) if oblig else round(PARAMS["rendement_epargne"], 2)

with sb.expander("Marché", expanded=False):
    hausse_prix = st.number_input("Hausse annuelle des prix de l'immobilier (%)", -10.0, 10.0, round(PARAMS["hausse_prix"], 2), 0.1,
                                  help="OCSTAT, prix médian au m² des appartements non neufs à Genève : 8 535 CHF en 2016, 10 853 CHF en 2024.")
    hausse_loyers = st.number_input("Hausse annuelle des loyers (%)", -5.0, 10.0, round(PARAMS["hausse_loyers"], 2), 0.1,
                                    help="OCSTAT, loyers libres à Genève : +1,8 % (2024-2025) et +1,3 % (2025-2026).")
    rendement = st.number_input("Rendement de l'épargne placée (%)", -5.0, 15.0, REND_DEFAUT, 0.05,
                                help="BNS, rendement des obligations de la Confédération à 10 ans (placement sans risque), dernière valeur publiée.")

with sb.expander("Frais", expanded=False):
    frais_achat = st.number_input("Frais d'achat (% du prix)", 0.0, 15.0, round(PARAMS["frais_achat"], 2), 0.5,
                                  help="Droits d'enregistrement genevois 3 % (loi D 3 30) + registre foncier 0,3 % + notaire 0,6 %.")
    frais_vente = st.number_input("Frais de vente (% du prix de vente)", 0.0, 10.0, round(PARAMS["frais_vente"], 2), 0.5,
                                  help="Commission de courtage usuelle (2 à 3 %).")
    entretien = st.number_input("Entretien et charges (% de la valeur/an)", 0.0, 5.0, round(PARAMS["entretien"], 2), 0.1,
                                help="Règle des banques suisses (ex. calculateur UBS) : environ 1 % de la valeur par an.")

# ---------------------------------------------------------------- En-tête
ticker = bandeau(TAUX_BNS)
if ticker:
    st.markdown(ticker, unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>Acheter ou louer à Genève ?</h1>
  <p>Entrez le logement que vous pourriez acheter, celui que vous pourriez louer et votre situation.
  L'outil compare votre <b>patrimoine</b> dans les deux cas, année après année, et vous dit
  <b>à partir de quand acheter devient plus rentable</b>.</p>
  <div class="chips"><span class="chip">Règles des banques suisses</span>
  <span class="chip">Taux BNS</span><span class="chip">Marché genevois</span></div>
  <div class="credit">Photo : Jurate Daugelaite, <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank">CC BY-SA 4.0</a>, via Wikimedia Commons</div>
</div>
""", unsafe_allow_html=True)

manquants = [nom for nom, v in [
    ("le prix du logement", prix), ("le loyer", loyer), ("votre revenu", revenu),
    ("votre épargne", epargne), ("le montant emprunté", emprunt),
] if v is None or (nom in ("le prix du logement", "le loyer") and v == 0)]
if manquants:
    st.markdown("""
<div class="etapes">
  <div class="etape"><b>1 · Les deux logements</b>Le prix de l'appartement à acheter et le loyer de celui à louer.</div>
  <div class="etape"><b>2 · Votre argent</b>Votre revenu brut et l'épargne que vous pouvez mobiliser.</div>
  <div class="etape"><b>3 · Votre hypothèque</b>Combien vous empruntez ; le taux se remplit tout seul.</div>
</div>
""", unsafe_allow_html=True)
    liste = manquants[0] if len(manquants) == 1 else ", ".join(manquants[:-1]) + " et " + manquants[-1]
    st.info("Entrez " + liste + ".")
    st.button("Pas d'idée ? Voir une démo", on_click=charger_demo, type="primary", key="demo_main")
    pied_de_page()
    st.stop()

h = Hypotheses(
    prix=prix, loyer_mensuel=loyer, revenu_annuel=revenu, epargne=epargne,
    emprunt=emprunt, taux_hypo=taux / 100,
    amort_annuel=amort if amort is not None else amort_min, duree_amort=duree_amort,
    frais_achat=frais_achat / 100, frais_vente=frais_vente / 100, entretien=entretien / 100,
    hausse_prix=hausse_prix / 100, hausse_loyers=hausse_loyers / 100, rendement=rendement / 100,
    horizon=horizon,
    residence_principale=residence,
    casatax_plafond=PARAMS["casatax_plafond"], casatax_reduction=PARAMS["casatax_reduction"],
)

# ---------------------------------------------------------------- Financement
fin = controle_financement(h)
section(1, "Votre financement est-il possible ?")

regles = [
    (fin["part_apport"] >= 0.20, f"Apport de {fin['part_apport']:.0%} du prix (min. 20 %)"),
    (h.epargne >= h.apport + h.frais, f"Épargne suffisante ({chf(h.apport + h.frais)} nécessaires)"),
    (fin["ratio"] <= 1 / 3, f"Charges théoriques : {fin['ratio']:.1%} du revenu (max. 33 %)"),
]
st.markdown('<div class="checks">' + "".join(
    f'<div class="check {"ok" if ok else "ko"}">{"✓" if ok else "✗"} {txt}</div>' for ok, txt in regles
) + "</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Votre apport", chf(fin["apport"]))
c2.metric("Frais d'achat", chf(fin["frais"]),
          f"−{chf(fin['casatax'])} grâce à Casatax" if fin["casatax"] else None, delta_color="inverse")
c3.metric("Hypothèque", chf(h.emprunt))
c4.metric("Remboursement / an", chf(h.amort_annuel),
          help="Vide dans la barre de gauche = minimum des banques (dette ramenée à 2/3 du prix en 15 ans).")

if fin["casatax"]:
    st.markdown(f'<div class="check ok" style="margin:8px 0">✓ <b>Casatax</b> : comme résidence principale à moins de '
                f'{chf(h.casatax_plafond)}, vous économisez <b>{chf(fin["casatax"])}</b> de droits d\'enregistrement '
                f'(aide genevoise, à condition d\'y habiter au moins 3 ans).</div>', unsafe_allow_html=True)
elif residence and h.prix > h.casatax_plafond:
    st.caption(f"Pas de Casatax : le prix dépasse le plafond de {chf(h.casatax_plafond)}.")
for a in fin["avertissements"]:
    st.warning(a)
if not fin["ok"]:
    for e in fin["erreurs"]:
        st.error(e)
    st.info(f"Revenu minimum pour ce logement : **{chf(fin['revenu_minimum'])}** par an.")
    pied_de_page()
    st.stop()

# ---------------------------------------------------------------- Simulation
lignes = simuler(h)
df = pd.DataFrame(lignes)
eq = annee_equilibre(lignes)
fin_h = lignes[-1]

section(2, "Le verdict")
if eq:
    st.markdown(f"""
<div class="verdict achat">
  <div class="big">Acheter devient plus rentable à partir de la {eq}<sup>e</sup> année.</div>
  <div class="small">Si vous restez moins de {eq} ans, louer vous laisse plus de patrimoine.
  Après {horizon} ans, l'achat vous rapporte <b>{chf(fin_h['ecart'])}</b> de plus.</div>
</div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div class="verdict loc">
  <div class="big">Sur {horizon} ans, louer reste plus avantageux.</div>
  <div class="small">Après {horizon} ans, la location vous laisse <b>{chf(-fin_h['ecart'])}</b> de plus que l'achat.</div>
</div>""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("Coût mensuel si vous achetez", chf(lignes[0]["cout_acheteur"] / 12),
          help="1re année : intérêts + remboursement + entretien, divisés par 12.")
c2.metric("Loyer mensuel", chf(loyer))
c3.metric(f"Patrimoine après {horizon} ans", f"{chf(fin_h['patrimoine_acheteur'])}",
          f"{chf(fin_h['ecart'])} vs location", delta_color="normal")

# ---------------------------------------------------------------- Graphiques
section(3, "L'évolution année par année")

AXES = dict(gridColor=GRILLE, domain=False, tickColor=GRILLE,
            labelColor=TEXTE2, titleColor=TEXTE2, labelFontSize=12, titleFontSize=12)

def style(ch):
    return (ch.configure(font="Inter", background="transparent").configure_axis(**AXES).configure_view(stroke=None)
              .configure_legend(orient="top", labelColor=TEXTE, titleColor=TEXTE2, labelFontSize=13))

large = df[["annee", "patrimoine_acheteur", "patrimoine_locataire", "ecart"]]
long = large.melt(id_vars="annee", value_vars=["patrimoine_acheteur", "patrimoine_locataire"],
                  var_name="option", value_name="patrimoine")
long["option"] = long["option"].map({"patrimoine_acheteur": "Acheter", "patrimoine_locataire": "Louer"})
couleurs = alt.Scale(domain=["Acheter", "Louer"], range=[BLEU, ORANGE])

survol = alt.selection_point(fields=["annee"], nearest=True, on="mouseover", empty=False)
base = alt.Chart(long).encode(
    x=alt.X("annee:Q", title="Années", axis=alt.Axis(tickMinStep=1, format="d")),
    y=alt.Y("patrimoine:Q", title="Patrimoine net (CHF)", axis=alt.Axis(format="~s")),
    color=alt.Color("option:N", scale=couleurs, legend=alt.Legend(title=None, orient="top", direction="horizontal")),
)
courbes = base.mark_line(strokeWidth=2.5, interpolate="monotone")
points = base.mark_point(filled=True, size=80, stroke="#2b2e34", strokeWidth=2).encode(
    opacity=alt.condition(survol, alt.value(1), alt.value(0)))
curseur = alt.Chart(large).mark_rule(strokeWidth=16, color="#ffffff").encode(
    x="annee:Q",
    opacity=alt.condition(survol, alt.value(0.08), alt.value(0)),
    tooltip=[alt.Tooltip("annee:Q", title="Année"),
             alt.Tooltip("patrimoine_acheteur:Q", title="Acheter (CHF)", format=",.0f"),
             alt.Tooltip("patrimoine_locataire:Q", title="Louer (CHF)", format=",.0f"),
             alt.Tooltip("ecart:Q", title="Écart (CHF)", format="+,.0f")],
).add_params(survol)
etiquettes = base.transform_filter(alt.datum.annee == horizon).mark_text(
    align="left", dx=8, fontSize=13, fontWeight="bold").encode(text="option:N", color=alt.value(TEXTE))
couches = [courbes, points, curseur, etiquettes]
if eq:
    seuil = pd.DataFrame({"annee": [eq], "txt": [f"Équilibre : année {eq}"]})
    couches.insert(0, alt.Chart(seuil).mark_rule(strokeDash=[5, 5], color=TEXTE2).encode(x="annee:Q"))
    couches.append(alt.Chart(seuil).mark_text(align="left", dx=6, dy=-6, color=TEXTE2, fontSize=12)
                   .encode(x="annee:Q", y=alt.value(12), text="txt:N"))

onglet1, onglet2, onglet3, onglet4 = st.tabs(["📈 Patrimoine", "📊 Écart par année", "🔀 Scénarios", "📋 Tableau"])

with onglet1:
    components.html(graphique_anime(df["annee"], df["patrimoine_acheteur"], df["patrimoine_locataire"], eq),
                    height=410)
    st.caption("Patrimoine net si vous vendez (ou arrêtez de louer) à la fin de chaque année. "
               "Les courbes se redessinent à chaque simulation ; passez la souris pour voir les montants.")

with onglet2:
    ecart = large.assign(gagnant=lambda d: d["ecart"].map(lambda v: "Acheter" if v >= 0 else "Louer"))
    barres = alt.Chart(ecart).mark_bar(cornerRadiusEnd=4, size=14).encode(
        x=alt.X("annee:Q", title="Années", axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("ecart:Q", title="Avance de l'achat sur la location (CHF)", axis=alt.Axis(format="~s")),
        color=alt.Color("gagnant:N", scale=couleurs, legend=alt.Legend(title="Plus rentable", orient="top", direction="horizontal")),
        tooltip=[alt.Tooltip("annee:Q", title="Année"), alt.Tooltip("gagnant:N", title="Plus rentable"),
                 alt.Tooltip("ecart:Q", title="Écart (CHF)", format="+,.0f")],
    )
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=TEXTE2).encode(y="y:Q")
    st.altair_chart(style(alt.layer(barres, zero).properties(height=380)), use_container_width=True)
    st.caption("Au-dessus de zéro, acheter vous laisse plus de patrimoine ; en dessous, c'est la location.")

with onglet3:
    st.write("Le résultat dépend surtout de l'évolution des prix et des taux. "
             "Voici le verdict si une seule hypothèse change.")

    def tableau_scenarios(nom, cle, valeurs):
        rows = []
        for v in valeurs:
            ll = simuler(Hypotheses(**{**h.__dict__, cle: v / 100}))
            e = annee_equilibre(ll)
            rows.append({nom: f"{v:+.1f} %" if cle == "hausse_prix" else f"{v:.2f} %",
                         "Acheter gagne après": f"{e} ans" if e else "jamais",
                         f"Écart à {horizon} ans": chf(ll[-1]["ecart"])})
        return pd.DataFrame(rows)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Si les prix de l'immobilier évoluent de…**")
        st.dataframe(tableau_scenarios("Hausse des prix / an", "hausse_prix", [-2, -1, 0, 1, 2, 3]),
                     hide_index=True, use_container_width=True)
    with col_b:
        st.markdown("**Si le taux hypothécaire est de…**")
        st.dataframe(tableau_scenarios("Taux", "taux_hypo", [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]),
                     hide_index=True, use_container_width=True)

with onglet4:
    affiche = df.rename(columns={
        "annee": "Année", "valeur_bien": "Valeur du bien", "dette": "Dette", "interets": "Intérêts",
        "amortissement": "Remboursement", "entretien": "Entretien", "cout_acheteur": "Coût acheteur",
        "loyer": "Loyer annuel", "epargne_acheteur": "Épargne acheteur",
        "patrimoine_acheteur": "Patrimoine acheteur", "patrimoine_locataire": "Patrimoine locataire",
        "ecart": "Écart",
    })
    st.dataframe(affiche.style.format({c: "{:,.0f}" for c in affiche.columns if c != "Année"}),
                 hide_index=True, use_container_width=True, height=420)
    st.download_button("⬇️ Télécharger le tableau (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "simulation_acheter_louer.csv", "text/csv")


pied_de_page()

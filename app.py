"""
Rent or Buy in Geneva — application Streamlit.
Lancer avec :  streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from model import Hypotheses, amortissement_minimum, annee_equilibre, controle_financement, simuler

st.set_page_config(page_title="Acheter ou louer à Genève ?", page_icon="🏠", layout="wide")

BLEU, ORANGE = "#257de0", "#f47230"   # Acheter, Louer (palette validée daltonisme)

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1150px;}
#MainMenu, footer {visibility: hidden;}
.hero {background: linear-gradient(120deg, #0f2a4a 0%, #1d4f8c 60%, #257de0 100%);
       color: #fff; border-radius: 18px; padding: 30px 34px; margin-bottom: 26px;}
.hero h1 {color: #fff; font-size: 2.1rem; margin: 0 0 8px 0; padding: 0; line-height: 1.2;}
.hero p {color: #dbe7f7; font-size: 1.02rem; margin: 0; max-width: 760px;}
.chips {margin-top: 16px;}
.chip {display: inline-block; background: rgba(255,255,255,.14); color: #fff; border-radius: 999px;
       padding: 4px 12px; font-size: .82rem; margin: 0 6px 6px 0;}
.section {display: flex; align-items: center; gap: 12px; margin: 30px 0 12px 0;}
.section .num {background: #e8f1fc; color: #1d4f8c; font-weight: 700; border-radius: 10px;
               width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;}
.section .titre {font-size: 1.35rem; font-weight: 700; color: #191919;}
div[data-testid="stMetric"] {background: #fff; border: 1px solid #e6eaf0; border-radius: 14px;
       padding: 14px 18px; box-shadow: 0 1px 3px rgba(15,42,74,.06);}
div[data-testid="stMetricLabel"] p {color: #666; font-size: .86rem;}
div[data-testid="stMetricValue"] {font-size: 1.55rem; color: #191919;}
.checks {display: flex; flex-wrap: wrap; gap: 10px; margin: 6px 0 4px 0;}
.check {border-radius: 12px; padding: 10px 14px; font-size: .92rem; border: 1px solid;}
.check.ok {background: #effaf3; border-color: #bfe8cf; color: #14532d;}
.check.ko {background: #fdf0f0; border-color: #f3c4c4; color: #7f1d1d;}
.verdict {border-radius: 16px; padding: 22px 26px; margin: 4px 0 18px 0; border: 1px solid #e6eaf0;}
.verdict .big {font-size: 1.6rem; font-weight: 700; color: #191919; line-height: 1.25;}
.verdict .small {color: #555; margin-top: 6px; font-size: 1rem;}
.verdict.achat {background: #eef5fd; border-left: 6px solid #257de0;}
.verdict.loc {background: #fef3ec; border-left: 6px solid #f47230;}
.etapes {display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 6px;}
.etape {background: #f4f6fa; border-radius: 14px; padding: 18px;}
.etape b {display: block; color: #1d4f8c; margin-bottom: 4px;}
section[data-testid="stSidebar"] h2 {font-size: 1.02rem; color: #1d4f8c; margin-top: .6rem;}
</style>
""", unsafe_allow_html=True)


def section(num, titre):
    st.markdown(f'<div class="section"><div class="num">{num}</div><div class="titre">{titre}</div></div>',
                unsafe_allow_html=True)


def chf(x: float) -> str:
    return f"{x:,.0f} CHF".replace(",", "'")


# ---------------------------------------------------------------- Saisie
sb = st.sidebar
sb.header("1. Vos deux logements")
prix = sb.number_input("Prix du logement à acheter (CHF)", min_value=0, value=None, step=10_000,
                       placeholder="ex. 1200000")
loyer = sb.number_input("Loyer du logement à louer (CHF/mois)", min_value=0, value=None, step=50,
                        placeholder="ex. 2700")

sb.header("2. Votre argent")
revenu = sb.number_input("Revenu brut du ménage (CHF/an)", min_value=0, value=None, step=5_000,
                         placeholder="ex. 220000")
epargne = sb.number_input("Combien avez-vous d'épargne ? (CHF)", min_value=0, value=None, step=5_000,
                          placeholder="ex. 300000",
                          help="Tout ce que vous pouvez mettre dans l'achat : apport et frais. Le reste est placé.")

sb.header("3. Votre hypothèque")
emprunt = sb.number_input("Combien empruntez-vous ? (CHF)", min_value=0, value=None, step=10_000,
                          placeholder="ex. 960000",
                          help="Les banques prêtent au maximum 80 % du prix.")
if prix and emprunt is not None:
    apport_calc = prix - emprunt
    part = apport_calc / prix if prix else 0
    sb.caption(f"➡️ Votre apport : **{chf(apport_calc)}** ({part:.0%} du prix) "
               f"· emprunt maximum : {chf(0.8 * prix)}")
# Taux moyens des nouvelles hypothèques, BNS (portail data.snb.ch, cube zikrepro), avril 2026.
# À mettre à jour avec le dernier mois publié.
TAUX_BNS = {"Fixe 5 ans": 1.70, "Fixe 10 ans": 1.98}
type_hypo = sb.selectbox("Type d'hypothèque", list(TAUX_BNS), index=1)
taux = sb.number_input("Taux hypothécaire (%)", min_value=0.0, max_value=15.0,
                       value=TAUX_BNS[type_hypo], step=0.05, format="%.2f",
                       key=f"taux_{type_hypo}",
                       help="Taux moyen du marché pour ce type d'hypothèque. "
                            "Modifiez-le si votre banque vous propose un autre taux.")
amort_min = amortissement_minimum(prix, emprunt) if prix and emprunt is not None else None
amort = sb.number_input("Combien remboursez-vous par an ? (CHF)", min_value=0, value=None, step=1_000,
                        placeholder=f"minimum {amort_min:,.0f}".replace(",", "'") if amort_min is not None else "ex. 10667",
                        help="Laissez vide pour appliquer le minimum des banques : "
                             "la dette redescend à 2/3 du prix en 15 ans.")
duree_amort = sb.slider("Pendant combien d'années remboursez-vous ?", 1, 40, 15)

sb.header("4. Votre projet")
horizon = sb.slider("Combien d'années comptez-vous rester ?", 1, 40, 30)

sb.divider()
sb.caption("Hypothèses (préremplies, modifiables)")
with sb.expander("Marché", expanded=False):
    hausse_prix = st.number_input("Hausse annuelle des prix de l'immobilier (%)", -10.0, 10.0, 1.5, 0.1)
    hausse_loyers = st.number_input("Hausse annuelle des loyers (%)", -5.0, 10.0, 1.0, 0.1)
    rendement = st.number_input("Rendement net de l'épargne placée (%)", -5.0, 15.0, 2.0, 0.1)

with sb.expander("Frais", expanded=False):
    frais_achat = st.number_input("Frais d'achat (% du prix)", 0.0, 15.0, 5.0, 0.5)
    frais_vente = st.number_input("Frais de vente (% du prix de vente)", 0.0, 10.0, 3.0, 0.5)
    entretien = st.number_input("Entretien et charges (% de la valeur/an)", 0.0, 5.0, 1.0, 0.1)

# ---------------------------------------------------------------- En-tête
st.markdown("""
<div class="hero">
  <h1>🏠 Acheter ou louer à Genève ?</h1>
  <p>Entrez le logement que vous pourriez acheter, celui que vous pourriez louer et votre situation.
  L'outil compare votre <b>patrimoine</b> dans les deux cas, année après année, et vous dit
  <b>à partir de quand acheter devient plus rentable</b>.</p>
  <div class="chips"><span class="chip">Règles des banques suisses</span>
  <span class="chip">Taux BNS</span><span class="chip">Marché genevois</span></div>
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
    st.info("👈 Il manque encore : " + ", ".join(manquants) + ".")
    st.stop()

h = Hypotheses(
    prix=prix, loyer_mensuel=loyer, revenu_annuel=revenu, epargne=epargne,
    emprunt=emprunt, taux_hypo=taux / 100,
    amort_annuel=amort if amort is not None else amort_min, duree_amort=duree_amort,
    frais_achat=frais_achat / 100, frais_vente=frais_vente / 100, entretien=entretien / 100,
    hausse_prix=hausse_prix / 100, hausse_loyers=hausse_loyers / 100, rendement=rendement / 100,
    horizon=horizon,
)

# ---------------------------------------------------------------- Financement
fin = controle_financement(h)
section(1, "La banque vous suivrait-elle ?")

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
c2.metric("Frais d'achat", chf(fin["frais"]))
c3.metric("Hypothèque", chf(h.emprunt))
c4.metric("Remboursement / an", chf(h.amort_annuel),
          help="Vide dans la barre de gauche = minimum des banques (dette ramenée à 2/3 du prix en 15 ans).")

for a in fin["avertissements"]:
    st.warning(a)
if not fin["ok"]:
    for e in fin["erreurs"]:
        st.error(e)
    st.info(f"Revenu minimum pour ce logement : **{chf(fin['revenu_minimum'])}** par an.")
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

AXES = dict(gridColor="#eef1f5", domain=False, tickColor="#e6eaf0",
            labelColor="#666666", titleColor="#666666", labelFontSize=12, titleFontSize=12)

def style(ch):
    return (ch.configure_axis(**AXES).configure_view(stroke=None)
              .configure_legend(orient="top", labelColor="#191919", labelFontSize=13))

large = df[["annee", "patrimoine_acheteur", "patrimoine_locataire", "ecart"]]
long = large.melt(id_vars="annee", value_vars=["patrimoine_acheteur", "patrimoine_locataire"],
                  var_name="option", value_name="patrimoine")
long["option"] = long["option"].map({"patrimoine_acheteur": "Acheter", "patrimoine_locataire": "Louer"})
couleurs = alt.Scale(domain=["Acheter", "Louer"], range=[BLEU, ORANGE])

survol = alt.selection_point(fields=["annee"], nearest=True, on="mouseover", empty=False)
base = alt.Chart(long).encode(
    x=alt.X("annee:Q", title="Années", axis=alt.Axis(tickMinStep=1, format="d")),
    y=alt.Y("patrimoine:Q", title="Patrimoine net (CHF)", axis=alt.Axis(format="~s")),
    color=alt.Color("option:N", scale=couleurs, legend=alt.Legend(title=None)),
)
courbes = base.mark_line(strokeWidth=2.5, interpolate="monotone")
points = base.mark_point(filled=True, size=80, stroke="white", strokeWidth=2).encode(
    opacity=alt.condition(survol, alt.value(1), alt.value(0)))
curseur = alt.Chart(large).mark_rule(strokeWidth=16, color="#191919").encode(
    x="annee:Q",
    opacity=alt.condition(survol, alt.value(0.08), alt.value(0)),
    tooltip=[alt.Tooltip("annee:Q", title="Année"),
             alt.Tooltip("patrimoine_acheteur:Q", title="Acheter (CHF)", format=",.0f"),
             alt.Tooltip("patrimoine_locataire:Q", title="Louer (CHF)", format=",.0f"),
             alt.Tooltip("ecart:Q", title="Écart (CHF)", format="+,.0f")],
).add_params(survol)
etiquettes = base.transform_filter(alt.datum.annee == horizon).mark_text(
    align="left", dx=8, fontSize=13, fontWeight="bold").encode(text="option:N", color=alt.value("#191919"))
couches = [courbes, points, curseur, etiquettes]
if eq:
    seuil = pd.DataFrame({"annee": [eq], "txt": [f"Équilibre : année {eq}"]})
    couches.insert(0, alt.Chart(seuil).mark_rule(strokeDash=[5, 5], color="#999999").encode(x="annee:Q"))
    couches.append(alt.Chart(seuil).mark_text(align="left", dx=6, dy=-6, color="#666666", fontSize=12)
                   .encode(x="annee:Q", y=alt.value(12), text="txt:N"))

onglet1, onglet2, onglet3, onglet4 = st.tabs(["📈 Patrimoine", "📊 Écart par année", "🔀 Scénarios", "📋 Tableau"])

with onglet1:
    st.altair_chart(style(alt.layer(*couches).properties(height=400, padding={"right": 70})),
                    use_container_width=True)
    st.caption("Patrimoine net si vous vendez (ou arrêtez de louer) à la fin de chaque année. "
               "Passez la souris sur le graphique pour voir les montants.")

with onglet2:
    ecart = large.assign(gagnant=lambda d: d["ecart"].map(lambda v: "Acheter" if v >= 0 else "Louer"))
    barres = alt.Chart(ecart).mark_bar(cornerRadiusEnd=4, size=14).encode(
        x=alt.X("annee:Q", title="Années", axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("ecart:Q", title="Avance de l'achat sur la location (CHF)", axis=alt.Axis(format="~s")),
        color=alt.Color("gagnant:N", scale=couleurs, legend=alt.Legend(title="Plus rentable")),
        tooltip=[alt.Tooltip("annee:Q", title="Année"), alt.Tooltip("gagnant:N", title="Plus rentable"),
                 alt.Tooltip("ecart:Q", title="Écart (CHF)", format="+,.0f")],
    )
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#999999").encode(y="y:Q")
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

with st.expander("ℹ️ Comment l'outil calcule"):
    st.markdown("""
- **Même départ** : les deux ménages ont la même épargne. L'acheteur paie l'apport et les frais d'achat avec, et place le reste ; le locataire place tout.
- **Même budget** : chaque année, celui dont le logement coûte le moins place la différence au rendement choisi.
- **Acheteur** : paie les intérêts, le remboursement annuel et l'entretien. Son patrimoine = valeur du bien moins frais de vente, moins la dette, plus son épargne.
- **Locataire** : paie le loyer, qui augmente chaque année. Son patrimoine = son épargne placée.
- **Pas inclus** : impôts (valeur locative, déductions, impôt sur le gain immobilier, fortune), 2e pilier, renouvellement de l'hypothèque à un autre taux.
""")

"""
Rent or Buy in Geneva — application Streamlit.
Lancer avec :  streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from model import Hypotheses, annee_equilibre, controle_financement, simuler

st.set_page_config(page_title="Acheter ou louer à Genève ?", page_icon="🏠", layout="wide")


def chf(x: float) -> str:
    return f"{x:,.0f} CHF".replace(",", "'")


# ---------------------------------------------------------------- Saisie
st.sidebar.header("Vos deux logements")
prix = st.sidebar.number_input("Prix du logement à acheter (CHF)", 100_000, 10_000_000, 1_200_000, 10_000)
loyer = st.sidebar.number_input("Loyer du logement à louer (CHF/mois)", 500, 20_000, 2_700, 50)

st.sidebar.header("Votre situation")
revenu = st.sidebar.number_input("Revenu brut du ménage (CHF/an)", 0, 5_000_000, 220_000, 5_000)
epargne = st.sidebar.number_input("Épargne disponible (CHF)", 0, 10_000_000, 300_000, 5_000)
horizon = st.sidebar.slider("Combien d'années comptez-vous rester ?", 1, 40, 30)

with st.sidebar.expander("Financement", expanded=False):
    apport = st.slider("Apport (% du prix)", 10, 100, 20)
    taux = st.number_input("Taux hypothécaire (%)", 0.0, 10.0, 1.9, 0.05)
    amortir = st.slider("Dette ramenée à (% du prix) en 15 ans", 0, 80, 67)

with st.sidebar.expander("Hypothèses de marché", expanded=False):
    hausse_prix = st.number_input("Hausse annuelle des prix de l'immobilier (%)", -10.0, 10.0, 1.5, 0.1)
    hausse_loyers = st.number_input("Hausse annuelle des loyers (%)", -5.0, 10.0, 1.0, 0.1)
    rendement = st.number_input("Rendement net de l'épargne placée (%)", -5.0, 15.0, 2.0, 0.1)

with st.sidebar.expander("Frais", expanded=False):
    frais_achat = st.number_input("Frais d'achat (% du prix)", 0.0, 15.0, 5.0, 0.5)
    frais_vente = st.number_input("Frais de vente (% du prix de vente)", 0.0, 10.0, 3.0, 0.5)
    entretien = st.number_input("Entretien et charges (% de la valeur/an)", 0.0, 5.0, 1.0, 0.1)

h = Hypotheses(
    prix=prix, loyer_mensuel=loyer, revenu_annuel=revenu, epargne=epargne,
    part_apport=apport / 100, taux_hypo=taux / 100, amortir_jusqua=amortir / 100,
    frais_achat=frais_achat / 100, frais_vente=frais_vente / 100, entretien=entretien / 100,
    hausse_prix=hausse_prix / 100, hausse_loyers=hausse_loyers / 100, rendement=rendement / 100,
    horizon=horizon,
)

# ---------------------------------------------------------------- En-tête
st.title("🏠 Acheter ou louer à Genève ?")
st.write(
    "Saisissez le logement que vous pourriez acheter et celui que vous pourriez louer. "
    "L'outil compare le **patrimoine** des deux options année après année, avec le même "
    "capital de départ et le même budget annuel, et vous dit **à partir de quand acheter devient plus rentable**."
)

# ---------------------------------------------------------------- Financement
fin = controle_financement(h)
st.subheader("1. La banque vous suivrait-elle ?")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Apport", chf(fin["apport"]))
c2.metric("Frais d'achat", chf(fin["frais"]))
c3.metric("Hypothèque", chf(fin["dette"]))
c4.metric("Charges théoriques / revenu", f"{fin['ratio']:.1%}", help="Calcul des banques : 5 % de la dette + 1 % du prix + amortissement, au maximum 1/3 du revenu brut.")

if not fin["ok"]:
    for e in fin["erreurs"]:
        st.error(e)
    st.info(f"Revenu minimum pour ce logement : **{chf(fin['revenu_minimum'])}** par an.")
    st.stop()
st.success("Financement accepté selon les règles usuelles des banques (20 % d'apport, charges ≤ 1/3 du revenu).")

# ---------------------------------------------------------------- Simulation
lignes = simuler(h)
df = pd.DataFrame(lignes)
eq = annee_equilibre(lignes)
fin_h = lignes[-1]

st.subheader("2. Le verdict")
c1, c2, c3 = st.columns(3)
c1.metric("Acheter devient plus rentable", f"après {eq} ans" if eq else "jamais sur cette durée")
c2.metric(f"Écart après {horizon} ans", chf(fin_h["ecart"]),
          help="Patrimoine de l'acheteur moins patrimoine du locataire. Positif : acheter est mieux.")
c3.metric("Coût mensuel la 1re année", f"{chf(lignes[0]['cout_acheteur'] / 12)} vs {chf(loyer)}",
          help="Acheteur (intérêts + amortissement + entretien) contre loyer.")

if eq and eq <= horizon:
    st.write(f"👉 Si vous restez **plus de {eq - 1} ans**, acheter vous rend plus riche. En dessous, louer est préférable.")
else:
    st.write("👉 Sur la durée choisie, **louer** laisse un plus gros patrimoine.")

# Graphique du patrimoine
long = df.melt(id_vars="annee", value_vars=["patrimoine_acheteur", "patrimoine_locataire"],
               var_name="option", value_name="patrimoine")
long["option"] = long["option"].map({"patrimoine_acheteur": "Acheter", "patrimoine_locataire": "Louer"})
lignes_chart = alt.Chart(long).mark_line(strokeWidth=3).encode(
    x=alt.X("annee:Q", title="Années"),
    y=alt.Y("patrimoine:Q", title="Patrimoine net (CHF)", axis=alt.Axis(format="~s")),
    color=alt.Color("option:N", title=None, scale=alt.Scale(range=["#2563eb", "#9ca3af"])),
    tooltip=[alt.Tooltip("annee:Q", title="Année"), "option:N",
             alt.Tooltip("patrimoine:Q", title="Patrimoine", format=",.0f")],
)
chart = lignes_chart
if eq:
    regle = alt.Chart(pd.DataFrame({"annee": [eq]})).mark_rule(strokeDash=[4, 4]).encode(x="annee:Q")
    chart = lignes_chart + regle
st.altair_chart(chart.properties(height=380), use_container_width=True)

# ---------------------------------------------------------------- Scénarios
st.subheader("3. Et si les hypothèses changent ?")
st.write("Le résultat dépend surtout de l'évolution des prix et des taux. Voici le verdict pour d'autres scénarios, toutes choses égales par ailleurs.")

col_a, col_b = st.columns(2)

def tableau_scenarios(nom, cle, valeurs):
    rows = []
    for v in valeurs:
        hh = Hypotheses(**{**h.__dict__, cle: v / 100})
        ll = simuler(hh)
        e = annee_equilibre(ll)
        rows.append({nom: f"{v:+.1f} %" if cle == "hausse_prix" else f"{v:.2f} %",
                     "Acheter gagne après": f"{e} ans" if e else "jamais",
                     f"Écart à {horizon} ans": chf(ll[-1]["ecart"])})
    return pd.DataFrame(rows)

with col_a:
    st.markdown("**Hausse annuelle des prix**")
    st.dataframe(tableau_scenarios("Hausse des prix", "hausse_prix", [-2, -1, 0, 1, 2, 3]),
                 hide_index=True, use_container_width=True)
with col_b:
    st.markdown("**Taux hypothécaire**")
    st.dataframe(tableau_scenarios("Taux", "taux_hypo", [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]),
                 hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- Détail
st.subheader("4. Le détail année par année")
affiche = df.rename(columns={
    "annee": "Année", "valeur_bien": "Valeur du bien", "dette": "Dette", "interets": "Intérêts",
    "amortissement": "Amortissement", "entretien": "Entretien", "cout_acheteur": "Coût acheteur",
    "loyer": "Loyer annuel", "epargne_acheteur": "Épargne acheteur",
    "patrimoine_acheteur": "Patrimoine acheteur", "patrimoine_locataire": "Patrimoine locataire",
    "ecart": "Écart",
})
st.dataframe(affiche.style.format({c: "{:,.0f}" for c in affiche.columns if c != "Année"}),
             hide_index=True, use_container_width=True)
st.download_button("Télécharger le tableau (CSV)", df.to_csv(index=False).encode("utf-8"),
                   "simulation_acheter_louer.csv", "text/csv")

with st.expander("Comment l'outil calcule"):
    st.markdown("""
- **Même départ** : les deux ménages ont le même capital (apport + frais d'achat). L'acheteur le met dans le logement, le locataire le place.
- **Même budget** : chaque année, celui dont le logement coûte le moins place la différence au rendement choisi.
- **Acheteur** : paie les intérêts, l'amortissement (la dette redescend linéairement en 15 ans) et l'entretien. Son patrimoine = valeur du bien moins frais de vente, moins la dette, plus son épargne.
- **Locataire** : paie le loyer, qui augmente chaque année. Son patrimoine = son épargne placée.
- **Pas encore inclus** : impôts (valeur locative, déductions, impôt sur le gain immobilier, fortune), 2e pilier, renouvellement de l'hypothèque à un autre taux.
""")

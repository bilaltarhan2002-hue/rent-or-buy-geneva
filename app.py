"""
Rent or Buy in Geneva — application Streamlit.
Lancer avec :  streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from model import Hypotheses, amortissement_minimum, annee_equilibre, controle_financement, simuler

st.set_page_config(page_title="Acheter ou louer à Genève ?", page_icon="🏠", layout="wide")


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
taux = sb.number_input("Taux hypothécaire (%)", min_value=0.0, max_value=15.0, value=None, step=0.05,
                       format="%.2f", placeholder="ex. 1.90")
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
st.title("🏠 Acheter ou louer à Genève ?")
st.write(
    "Saisissez le logement que vous pourriez acheter et celui que vous pourriez louer, puis votre situation. "
    "L'outil compare le **patrimoine** des deux options année après année, avec la même "
    "épargne de départ et le même budget annuel, et vous dit **à partir de quand acheter devient plus rentable**."
)

manquants = [nom for nom, v in [
    ("le prix du logement", prix), ("le loyer", loyer), ("votre revenu", revenu),
    ("votre épargne", epargne), ("le montant emprunté", emprunt), ("le taux hypothécaire", taux),
] if v is None or (nom in ("le prix du logement", "le loyer") and v == 0)]
if manquants:
    st.info("👈 Remplissez dans la barre de gauche : " + ", ".join(manquants) + ".")
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
st.subheader("1. La banque vous suivrait-elle ?")
c1, c2, c3 = st.columns(3)
c1.metric("Votre apport", chf(fin["apport"]), f"{fin['part_apport']:.0%} du prix", delta_color="off")
c2.metric("Frais d'achat", chf(fin["frais"]))
c3.metric("Épargne restante (placée)", chf(fin["reste_epargne"]))
c4, c5, c6 = st.columns(3)
c4.metric("Hypothèque", chf(h.emprunt))
c5.metric("Remboursement par an", chf(h.amort_annuel),
          "minimum des banques" if amort is None else None, delta_color="off")
c6.metric("Charges théoriques / revenu", f"{fin['ratio']:.1%}",
          help="Calcul des banques : 5 % de la dette + 1 % du prix + remboursement annuel, au maximum 1/3 du revenu brut.")

for a in fin["avertissements"]:
    st.warning(a)
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
c1, c2 = st.columns(2)
c1.metric("Acheter devient plus rentable", f"après {eq} ans" if eq else "jamais sur cette durée")
c2.metric(f"Écart après {horizon} ans", chf(fin_h["ecart"]),
          help="Patrimoine de l'acheteur moins patrimoine du locataire. Positif : acheter est mieux.")
c3, c4 = st.columns(2)
c3.metric("Coût mensuel acheteur (1re année)", chf(lignes[0]["cout_acheteur"] / 12),
          help="Intérêts + amortissement + entretien, divisés par 12.")
c4.metric("Loyer mensuel (1re année)", chf(loyer))

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
- **Même départ** : les deux ménages ont la même épargne. L'acheteur paie l'apport et les frais d'achat avec, et place le reste ; le locataire place tout.
- **Même budget** : chaque année, celui dont le logement coûte le moins place la différence au rendement choisi.
- **Acheteur** : paie les intérêts, le remboursement annuel que vous avez choisi et l'entretien. Son patrimoine = valeur du bien moins frais de vente, moins la dette, plus son épargne.
- **Locataire** : paie le loyer, qui augmente chaque année. Son patrimoine = son épargne placée.
- **Pas encore inclus** : impôts (valeur locative, déductions, impôt sur le gain immobilier, fortune), 2e pilier, renouvellement de l'hypothèque à un autre taux.
""")

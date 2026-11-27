"""
Rent or Buy in Geneva — moteur de simulation.

Deux ménages identiques partent avec le même capital et dépensent le même
budget chaque année :
  - l'acheteur met son capital dans l'apport et les frais d'achat ;
  - le locataire place ce même capital.
Chaque année, celui dont le logement coûte le moins place la différence.
On compare ensuite leur patrimoine net, année après année.
"""

from dataclasses import dataclass


@dataclass
class Hypotheses:
    # Les deux logements
    prix: float = 1_200_000          # prix du logement à acheter (CHF)
    loyer_mensuel: float = 2_700     # loyer du logement à louer (CHF/mois)

    # Situation du ménage
    revenu_annuel: float = 220_000   # revenu brut annuel (CHF)
    epargne: float = 300_000         # épargne disponible (CHF)

    # Financement
    part_apport: float = 0.20        # apport en % du prix (min. 20 %)
    taux_hypo: float = 0.019         # taux hypothécaire annuel
    amortir_jusqua: float = 2 / 3    # la dette redescend à cette part du prix...
    duree_amort: int = 15            # ... en ce nombre d'années

    # Coûts
    frais_achat: float = 0.05        # notaire + droits d'enregistrement, % du prix
    frais_vente: float = 0.03        # % du prix de vente
    entretien: float = 0.01          # entretien et charges PPE, % de la valeur / an

    # Marché
    hausse_prix: float = 0.015       # hausse annuelle de la valeur du bien
    hausse_loyers: float = 0.01      # hausse annuelle des loyers
    rendement: float = 0.02          # rendement net annuel de l'épargne placée

    horizon: int = 30                # nombre d'années simulées


def controle_financement(h: Hypotheses) -> dict:
    """Règles usuelles des banques suisses."""
    apport = h.part_apport * h.prix
    frais = h.frais_achat * h.prix
    dette = h.prix - apport
    amort = max(dette - h.amortir_jusqua * h.prix, 0) / h.duree_amort
    # Charges théoriques : taux de 5 %, 1 % d'entretien, amortissement
    charges = 0.05 * dette + 0.01 * h.prix + amort
    ratio = charges / h.revenu_annuel if h.revenu_annuel > 0 else float("inf")

    erreurs = []
    if h.part_apport < 0.20:
        erreurs.append("L'apport doit être d'au moins 20 % du prix.")
    if h.epargne < apport + frais:
        erreurs.append(
            f"Épargne insuffisante : il faut {apport + frais:,.0f} CHF "
            f"(apport {apport:,.0f} + frais {frais:,.0f}).".replace(",", "'")
        )
    if ratio > 1 / 3:
        erreurs.append(
            f"Charges théoriques trop élevées : {ratio:.1%} du revenu (max. 33,3 %)."
        )
    return {
        "apport": apport,
        "frais": frais,
        "dette": dette,
        "amortissement": amort,
        "charges_theoriques": charges,
        "ratio": ratio,
        "revenu_minimum": 3 * charges,
        "ok": not erreurs,
        "erreurs": erreurs,
    }


def simuler(h: Hypotheses) -> list[dict]:
    """Simulation année par année. Renvoie une ligne par année."""
    apport = h.part_apport * h.prix
    capital_depart = apport + h.frais_achat * h.prix

    dette = h.prix - apport
    plancher = min(h.amortir_jusqua * h.prix, dette)
    amort_annuel = (dette - plancher) / h.duree_amort

    epargne_locataire = capital_depart   # le locataire place tout son capital
    epargne_acheteur = 0.0               # l'acheteur a tout mis dans le logement

    lignes = []
    for t in range(1, h.horizon + 1):
        valeur_debut = h.prix * (1 + h.hausse_prix) ** (t - 1)
        valeur_fin = h.prix * (1 + h.hausse_prix) ** t

        interets = h.taux_hypo * dette
        amort = min(amort_annuel, dette - plancher) if t <= h.duree_amort else 0.0
        entretien = h.entretien * valeur_debut
        cout_acheteur = interets + amort + entretien

        loyer = 12 * h.loyer_mensuel * (1 + h.hausse_loyers) ** (t - 1)

        dette -= amort

        # Même budget : celui qui paie le moins place la différence
        epargne_locataire = epargne_locataire * (1 + h.rendement) + max(cout_acheteur - loyer, 0)
        epargne_acheteur = epargne_acheteur * (1 + h.rendement) + max(loyer - cout_acheteur, 0)

        patrimoine_acheteur = valeur_fin * (1 - h.frais_vente) - dette + epargne_acheteur
        patrimoine_locataire = epargne_locataire

        lignes.append({
            "annee": t,
            "valeur_bien": valeur_fin,
            "dette": dette,
            "interets": interets,
            "amortissement": amort,
            "entretien": entretien,
            "cout_acheteur": cout_acheteur,
            "loyer": loyer,
            "epargne_acheteur": epargne_acheteur,
            "patrimoine_acheteur": patrimoine_acheteur,
            "patrimoine_locataire": patrimoine_locataire,
            "ecart": patrimoine_acheteur - patrimoine_locataire,
        })
    return lignes


def annee_equilibre(lignes: list[dict]):
    """Première année à partir de laquelle acheter reste plus rentable."""
    for i, l in enumerate(lignes):
        if all(x["ecart"] >= 0 for x in lignes[i:]):
            return l["annee"]
    return None

"""
Rent or Buy in Geneva — moteur de simulation.

Deux ménages identiques partent avec la même épargne et dépensent le même
budget chaque année :
  - l'acheteur paie l'apport et les frais d'achat avec son épargne, et place le reste ;
  - le locataire place toute son épargne.
Chaque année, celui dont le logement coûte le moins place la différence.
On compare ensuite leur patrimoine net, année après année.
"""

from dataclasses import dataclass


@dataclass
class Hypotheses:
    # Les deux logements
    prix: float                      # prix du logement à acheter (CHF)
    loyer_mensuel: float             # loyer du logement à louer (CHF/mois)

    # Situation du ménage
    revenu_annuel: float             # revenu brut annuel (CHF)
    epargne: float                   # épargne totale disponible (CHF)

    # Financement choisi par l'utilisateur
    emprunt: float                   # montant emprunté (hypothèque, CHF)
    taux_hypo: float                 # taux hypothécaire annuel
    amort_annuel: float              # montant remboursé chaque année (CHF)
    duree_amort: int = 15            # nombre d'années de remboursement

    # Coûts
    frais_achat: float = 0.05        # notaire + droits d'enregistrement, % du prix
    frais_vente: float = 0.03        # % du prix de vente
    entretien: float = 0.01          # entretien et charges PPE, % de la valeur / an

    # Marché
    hausse_prix: float = 0.015       # hausse annuelle de la valeur du bien
    hausse_loyers: float = 0.01      # hausse annuelle des loyers
    rendement: float = 0.02          # rendement net annuel de l'épargne placée

    horizon: int = 30                # nombre d'années simulées

    # Casatax (Genève) : réduction des droits d'enregistrement pour une résidence principale
    residence_principale: bool = False
    casatax_plafond: float = 1_394_928     # prix maximum (2026)
    casatax_reduction: float = 20_924      # réduction maximale du droit de vente (2026)
    droits_enregistrement: float = 0.03    # taux genevois du droit de vente

    @property
    def apport(self) -> float:
        return self.prix - self.emprunt

    @property
    def casatax(self) -> float:
        """Montant de la réduction Casatax (0 si non applicable)."""
        # condition légale : y habiter au moins 3 ans, sinon la réduction doit être remboursée
        if self.residence_principale and self.prix <= self.casatax_plafond and self.horizon >= 3:
            return min(self.casatax_reduction, self.droits_enregistrement * self.prix)
        return 0.0

    @property
    def frais(self) -> float:
        return self.frais_achat * self.prix - self.casatax


def amortissement_minimum(prix: float, emprunt: float) -> float:
    """Règle des banques : la dette redescend à 2/3 du prix en 15 ans au plus."""
    return max(emprunt - 2 / 3 * prix, 0) / 15


def controle_financement(h: Hypotheses) -> dict:
    """Règles usuelles des banques suisses."""
    charges = 0.05 * h.emprunt + 0.01 * h.prix + h.amort_annuel
    ratio = charges / h.revenu_annuel if h.revenu_annuel > 0 else float("inf")
    part_apport = h.apport / h.prix if h.prix > 0 else 0
    amort_min = amortissement_minimum(h.prix, h.emprunt)

    erreurs, avertissements = [], []
    if h.emprunt > h.prix:
        erreurs.append("Le montant emprunté ne peut pas dépasser le prix.")
    if part_apport < 0.20:
        erreurs.append(
            f"Apport trop faible : {part_apport:.1%} du prix. Les banques demandent au moins 20 %, "
            f"donc un emprunt de {fmt(0.8 * h.prix)} au maximum."
        )
    if h.epargne < h.apport + h.frais:
        erreurs.append(
            f"Épargne insuffisante : il faut {fmt(h.apport + h.frais)} "
            f"(apport {fmt(h.apport)} + frais d'achat {fmt(h.frais)})."
        )
    if ratio > 1 / 3:
        erreurs.append(f"Charges théoriques trop élevées : {ratio:.1%} du revenu (max. 33,3 %).")
    if h.amort_annuel * h.duree_amort > h.emprunt + 1:
        erreurs.append("Vous remboursez plus que le montant emprunté.")
    if h.amort_annuel < amort_min - 0.5:
        avertissements.append(
            f"Amortissement inférieur au minimum des banques ({fmt(amort_min)} par an "
            f"pour ramener la dette à 2/3 du prix en 15 ans)."
        )
    return {
        "apport": h.apport,
        "part_apport": part_apport,
        "frais": h.frais,
        "casatax": h.casatax,
        "reste_epargne": h.epargne - h.apport - h.frais,
        "charges_theoriques": charges,
        "ratio": ratio,
        "revenu_minimum": 3 * charges,
        "amort_min": amort_min,
        "ok": not erreurs,
        "erreurs": erreurs,
        "avertissements": avertissements,
    }


def simuler(h: Hypotheses) -> list[dict]:
    """Simulation année par année. Renvoie une ligne par année."""
    dette = h.emprunt
    epargne_locataire = h.epargne                         # le locataire place tout
    epargne_acheteur = h.epargne - h.apport - h.frais     # l'acheteur place le reste

    lignes = []
    for t in range(1, h.horizon + 1):
        valeur_debut = h.prix * (1 + h.hausse_prix) ** (t - 1)
        valeur_fin = h.prix * (1 + h.hausse_prix) ** t

        interets = h.taux_hypo * dette
        amort = min(h.amort_annuel, dette) if t <= h.duree_amort else 0.0
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


def fmt(x: float) -> str:
    return f"{x:,.0f} CHF".replace(",", "'")

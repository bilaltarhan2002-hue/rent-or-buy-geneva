"""
Validation du modèle :
1. l'année 1 recalculée « à la main », formule par formule, indépendamment de simuler() ;
2. des tests de cohérence (le modèle réagit dans le bon sens quand on change une hypothèse).
"""

from dataclasses import replace

from model import annee_equilibre, simuler


def chf(x):
    return f"{x:,.0f} CHF".replace(",", "'")


def calcul_main_annee1(h):
    """Refait l'année 1 avec les formules écrites une par une. Renvoie (lignes, résultat de l'outil)."""
    P, E, D0 = h.prix, h.epargne, h.emprunt
    apport = P - D0
    reduc = min(h.casatax_reduction, h.droits_enregistrement * P) \
        if (h.residence_principale and P <= h.casatax_plafond and h.horizon >= 3) else 0.0
    frais = h.frais_achat * P - reduc
    A = min(h.amort_annuel, D0) if h.duree_amort >= 1 else 0.0

    V1 = P * (1 + h.hausse_prix)
    interets = h.taux_hypo * D0
    entretien = h.entretien * P
    cout = interets + A + entretien
    loyer = 12 * h.loyer_mensuel
    D1 = D0 - A
    ep_a = (E - apport - frais) * (1 + h.rendement) + max(loyer - cout, 0)
    W_a = V1 * (1 - h.frais_vente) - D1 + ep_a
    W_l = E * (1 + h.rendement) + max(cout - loyer, 0)

    pct = lambda x: f"{100 * x:.2f} %"
    outil = simuler(h)[0]
    lignes = [
        ("Frais d'achat", f"{pct(h.frais_achat)} × {chf(P)}" + (f" − Casatax {chf(reduc)}" if reduc else ""),
         frais, h.frais),
        ("Valeur du bien en fin d'année", f"{chf(P)} × (1 + {pct(h.hausse_prix)})", V1, outil["valeur_bien"]),
        ("Intérêts", f"{pct(h.taux_hypo)} × {chf(D0)}", interets, outil["interets"]),
        ("Remboursement", "montant annuel choisi", A, outil["amortissement"]),
        ("Entretien", f"{pct(h.entretien)} × {chf(P)}", entretien, outil["entretien"]),
        ("Coût de l'acheteur", "intérêts + remboursement + entretien", cout, outil["cout_acheteur"]),
        ("Loyer annuel", f"12 × {chf(h.loyer_mensuel)}", loyer, outil["loyer"]),
        ("Dette restante", f"{chf(D0)} − remboursement", D1, outil["dette"]),
        ("Épargne placée de l'acheteur", f"({chf(E)} − {chf(apport)} − {chf(frais)}) × (1 + {pct(h.rendement)}) + max(loyer − coût ; 0)",
         ep_a, outil["epargne_acheteur"]),
        ("Patrimoine de l'acheteur", f"valeur × (1 − {pct(h.frais_vente)}) − dette + épargne", W_a, outil["patrimoine_acheteur"]),
        ("Patrimoine du locataire", f"{chf(E)} × (1 + {pct(h.rendement)}) + max(coût − loyer ; 0)", W_l, outil["patrimoine_locataire"]),
        ("Écart (acheter − louer)", "patrimoine acheteur − patrimoine locataire", W_a - W_l, outil["ecart"]),
    ]
    return lignes


def tests_coherence(h):
    """Chaque test : (description, réussi ?)."""
    base = simuler(h)
    ecart = base[-1]["ecart"]
    T = len(base)
    tests = []

    def ecart_si(**k):
        return simuler(replace(h, **k))[-1]["ecart"]

    tests.append(("Si les prix de l'immobilier montent plus vite, l'achat devient plus avantageux",
                  ecart_si(hausse_prix=h.hausse_prix + 0.01) > ecart))
    tests.append(("Si le loyer est plus cher, l'achat devient plus avantageux",
                  ecart_si(loyer_mensuel=h.loyer_mensuel * 1.10) > ecart))
    tests.append(("Si le taux hypothécaire monte, l'achat devient moins avantageux",
                  ecart_si(taux_hypo=h.taux_hypo + 0.01) < ecart))
    tests.append(("Si l'épargne rapporte plus, la location devient plus avantageuse",
                  ecart_si(rendement=h.rendement + 0.01) < ecart))
    tests.append(("Si les frais d'achat augmentent, l'achat devient moins avantageux",
                  ecart_si(frais_achat=h.frais_achat + 0.01) < ecart))
    rembourse = sum(l["amortissement"] for l in base)
    tests.append((f"La dette finale vaut l'emprunt moins tout ce qui a été remboursé ({chf(h.emprunt)} − {chf(rembourse)})",
                  abs(base[-1]["dette"] - (h.emprunt - rembourse)) < 1))
    tests.append(("La dette ne devient jamais négative", all(l["dette"] >= -1e-6 for l in base)))
    eq = annee_equilibre(base)
    tests.append(("L'année d'équilibre est bien la première année où l'achat reste devant jusqu'à la fin",
                  eq is None or (base[eq - 1]["ecart"] >= 0 and (eq == 1 or base[eq - 2]["ecart"] < 0))))
    return tests

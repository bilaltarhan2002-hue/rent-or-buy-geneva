"""
Préparation des données : des sources publiques brutes (data/brut/) aux paramètres
par défaut de l'outil (data/parametres.csv).

Utilisation :
    python data/preparer_donnees.py                  # calcule à partir des fichiers de data/brut/
    python data/preparer_donnees.py --telecharger    # met d'abord à jour les séries BNS via l'API

Chaque paramètre est calculé par une formule écrite ci-dessous, avec sa source.
L'application (app.py) lit data/parametres.csv au démarrage.
"""

import csv
import io
import sys
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
BRUT = DOSSIER / "brut"
SORTIE = DOSSIER / "parametres.csv"


def lire(nom):
    with open(BRUT / nom, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- Téléchargement BNS (optionnel)
def telecharger_bns():
    """Met à jour data/brut/bns_hypotheques_zikrepro.csv depuis l'API de la BNS."""
    url = "https://data.snb.ch/api/cube/zikrepro/data/csv/en?fromDate=2025-01"
    with urllib.request.urlopen(url, timeout=20) as r:
        lignes = r.read().decode("utf-8").splitlines()
    debut = next(i for i, l in enumerate(lignes) if l.startswith('"Date"'))
    lecteur = csv.DictReader(io.StringIO("\n".join(lignes[debut:])), delimiter=";")
    rows = []
    for r in lecteur:
        if r["D0"] == "M" and r["D1"] in ("50", "10") and r["Value"]:
            duree = 5 if r["D1"] == "50" else 10
            rows.append({"date": r["Date"], "serie": "moyenne nouvelles hypotheques taux fixe",
                         "duree_ans": duree, "taux_pct": r["Value"],
                         "source": f"https://data.snb.ch/api/cube/zikrepro/data/csv/en (D0=M D1={r['D1']})"})
    with open(BRUT / "bns_hypotheques_zikrepro.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"BNS : {len(rows)} observations téléchargées.")


# ---------------------------------------------------------------- Calcul des paramètres
def preparer():
    params = []

    def ajouter(nom, valeur, unite, formule, source):
        params.append({"parametre": nom, "valeur": round(valeur, 4), "unite": unite,
                       "formule": formule, "source": source})

    # 1. Taux hypothécaires : dernier mois publié par la BNS
    hyp = lire("bns_hypotheques_zikrepro.csv")
    for duree in ("5", "10"):
        serie = sorted((r for r in hyp if r["duree_ans"] == duree), key=lambda r: r["date"])
        der = serie[-1]
        ajouter(f"taux_fixe_{duree}_ans", float(der["taux_pct"]), "%",
                f"dernière valeur mensuelle ({der['date']})", der["source"])

    # 2. Hausse annuelle des prix : taux de croissance annuel moyen (TCAM) du prix médian au m2
    prix = {int(r["annee"]): r for r in lire("ocstat_prix_ppe.csv") if "non neufs" in r["objet"]}
    a0, a1 = min(prix), max(prix)
    p0, p1 = float(prix[a0]["prix_median_chf_m2"]), float(prix[a1]["prix_median_chf_m2"])
    n = a1 - a0
    tcam = (p1 / p0) ** (1 / n) - 1
    ajouter("hausse_prix", 100 * tcam, "% / an",
            f"({p1:.0f} / {p0:.0f})^(1/{n}) - 1, prix médian au m2 {a0} -> {a1}",
            f"{prix[a0]['source']} ; {prix[a1]['source']}")

    # 3. Hausse annuelle des loyers : moyenne géométrique des variations annuelles
    loy = lire("ocstat_loyers.csv")
    produit = 1.0
    for r in loy:
        produit *= 1 + float(r["variation_annuelle_pct"]) / 100
    moy = produit ** (1 / len(loy)) - 1
    ajouter("hausse_loyers", 100 * moy, "% / an",
            "moyenne géométrique de " + " et ".join(r["variation_annuelle_pct"] + " %" for r in loy),
            loy[0]["source"])

    # 4. Rendement de l'épargne : obligations de la Confédération à 10 ans (valeur de secours)
    obl = lire("bns_obligations_confederation.csv")[-1]
    ajouter("rendement_epargne", float(obl["rendement_pct"]), "% / an",
            f"rendement au {obl['date']} (l'application lit la dernière valeur en direct)", obl["source"])

    # 5. Frais et règles bancaires
    fr = {r["parametre"]: r for r in lire("frais_et_regles.csv")}
    achat = sum(float(fr[k]["valeur_pct"]) for k in ("droits_enregistrement", "registre_foncier", "notaire"))
    ajouter("frais_achat", achat, "% du prix",
            "droits d'enregistrement + registre foncier + notaire = "
            + " + ".join(fr[k]["valeur_pct"] for k in ("droits_enregistrement", "registre_foncier", "notaire")),
            " ; ".join(fr[k]["source"] for k in ("droits_enregistrement", "registre_foncier", "notaire")))
    for k in ("frais_vente", "entretien", "apport_minimum", "taux_theorique", "charges_max_revenu"):
        ajouter(k, float(fr[k]["valeur_pct"]), "%", "valeur reprise telle quelle", fr[k]["source"])

    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(params[0]))
        w.writeheader()
        w.writerows(params)
    for p in params:
        print(f"{p['parametre']:<22} {p['valeur']:>8} {p['unite']:<10} {p['formule']}")
    print(f"\n-> {SORTIE.relative_to(DOSSIER.parent)}")


if __name__ == "__main__":
    if "--telecharger" in sys.argv:
        telecharger_bns()
    preparer()

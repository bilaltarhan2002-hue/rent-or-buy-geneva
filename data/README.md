# Données

Toutes les hypothèses par défaut de l'outil viennent de **sources publiques**.

| Dossier / fichier | Contenu |
|---|---|
| `brut/bns_hypotheques_zikrepro.csv` | BNS : taux moyens des nouvelles hypothèques à taux fixe 5 et 10 ans (mensuel) |
| `brut/bns_obligations_confederation.csv` | BNS : rendement des obligations de la Confédération à 10 ans |
| `brut/ocstat_prix_ppe.csv` | OCSTAT : prix médian au m² des appartements en PPE à Genève |
| `brut/ocstat_loyers.csv` | OCSTAT : variation annuelle des loyers libres à Genève |
| `brut/frais_et_regles.csv` | Loi genevoise (droits d'enregistrement), frais usuels, règles des banques |
| `preparer_donnees.py` | Calcule chaque paramètre à partir des fichiers bruts (formules dans le code) |
| `parametres.csv` | Résultat : paramètres par défaut lus par l'application |

Chaque ligne des fichiers bruts indique sa source (lien).

Pour recalculer :

```
python data/preparer_donnees.py                 # à partir des fichiers bruts
python data/preparer_donnees.py --telecharger   # met d'abord à jour les taux BNS via l'API
```

L'application lit aussi en direct, à chaque visite, les dernières valeurs de la BNS
(taux hypothécaires, obligations à 10 ans, SARON, devises) ; `parametres.csv` sert de valeur de secours.

"""
Bandeau défilant : dernières valeurs publiées par la Banque nationale suisse (data.snb.ch).
Les données sont relues au plus toutes les 3 heures. Si la BNS ne répond pas, l'élément est omis.
"""

import io
import urllib.request
from datetime import date, timedelta

import pandas as pd
import streamlit as st

API = "https://data.snb.ch/api/cube/{cube}/data/csv/en"
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _lire(url: str) -> pd.DataFrame:
    req = urllib.request.Request(url, headers={"User-Agent": "rent-or-buy-geneva (projet etudiant)"})
    with urllib.request.urlopen(req, timeout=10) as r:
        texte = r.read().decode("utf-8")
    lignes = texte.splitlines()
    debut = next(i for i, l in enumerate(lignes) if l.startswith('"Date"'))
    return pd.read_csv(io.StringIO("\n".join(lignes[debut:])), sep=";", dtype=str)


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def serie_bns(cube, filtre, depuis=None):
    """Deux dernières observations (date, valeur) d'une série BNS, ou None."""
    try:
        df = None
        if depuis:
            try:
                df = _lire(API.format(cube=cube) + f"?fromDate={depuis}")
            except Exception:
                df = None
        if df is None or df.empty:
            df = _lire(API.format(cube=cube))
        for col, val in filtre:
            df = df[df[col] == val]
        df = df.dropna(subset=["Value"])
        df["Value"] = df["Value"].astype(float)
        if df.empty:
            return None
        der = df.iloc[-1]
        prec = df.iloc[-2] if len(df) > 1 else None
        return {"date": der["Date"], "valeur": der["Value"],
                "precedent": None if prec is None else prec["Value"]}
    except Exception:
        return None


def taux_hypothecaires():
    """Taux moyens BNS des hypothèques fixes 5 et 10 ans (dernier mois publié)."""
    secours = {"Fixe 5 ans": 2.03, "Fixe 10 ans": 2.20}, "septembre 2026"
    depuis = (date.today() - timedelta(days=240)).strftime("%Y-%m")
    t5 = serie_bns("zikrepro", (("D0", "M"), ("D1", "50")), depuis)
    t10 = serie_bns("zikrepro", (("D0", "M"), ("D1", "10")), depuis)
    if not (t5 and t10):
        return secours
    mois = _date_fr(t10["date"])
    mois = mois.replace("janv.", "janvier").replace("févr.", "février").replace("avr.", "avril") \
               .replace("juil.", "juillet").replace("sept.", "septembre").replace("oct.", "octobre") \
               .replace("nov.", "novembre").replace("déc.", "décembre")
    return {"Fixe 5 ans": round(float(t5["valeur"]), 2), "Fixe 10 ans": round(float(t10["valeur"]), 2)}, mois


def _date_fr(d: str) -> str:
    p = d.split("-")
    if len(p) == 2:
        return f"{MOIS[int(p[1]) - 1]} {p[0]}"
    if len(p) == 3:
        return f"{int(p[2])} {MOIS[int(p[1]) - 1]}"
    return d


def bandeau(taux_hypo: dict) -> str:
    """HTML du bandeau défilant."""
    il_y_a = (date.today() - timedelta(days=60)).isoformat()
    il_y_a_mois = (date.today() - timedelta(days=150)).strftime("%Y-%m")
    elements = [
        ("SARON", serie_bns("zimoma", (("D0", "SARON"),), il_y_a_mois), "%", 2),
        ("Oblig. Confédération 10 ans", serie_bns("rendoblid", (("D0", "10J0"),), il_y_a), "%", 2),
        ("EUR/CHF", serie_bns("devkum", (("D0", "M0"), ("D1", "EUR1")), il_y_a_mois), "", 4),
        ("USD/CHF", serie_bns("devkum", (("D0", "M0"), ("D1", "USD1")), il_y_a_mois), "", 4),
        ("GBP/CHF", serie_bns("devkum", (("D0", "M0"), ("D1", "GBP1")), il_y_a_mois), "", 4),
    ]
    items = []
    for nom, s, unite, dec in elements:
        if not s:
            continue
        var = ""
        if s["precedent"] is not None:
            d = s["valeur"] - s["precedent"]
            if abs(d) >= 10 ** -dec:
                sens, cls = ("▲", "up") if d > 0 else ("▼", "down")
                var = f'<span class="var {cls}">{sens} {abs(d):.{dec}f}</span>'
        items.append(f'<span class="tk"><span class="nom">{nom}</span>'
                     f'<span class="val">{s["valeur"]:.{dec}f}{(" " + unite) if unite else ""}</span>{var}'
                     f'<span class="dt">{_date_fr(s["date"])}</span></span>')
    for nom, t in taux_hypo.items():
        items.append(f'<span class="tk"><span class="nom">Hypothèque {nom.lower()}</span>'
                     f'<span class="val">{t:.2f} %</span><span class="dt">moy. BNS</span></span>')
    if not items:
        return ""
    piste = "".join(items)
    return (f'<div class="ticker"><div class="ticker-track">{piste}{piste}</div></div>')


CSS = """
.ticker {overflow: hidden; white-space: nowrap; background: rgba(15,18,22,.88); border: 1px solid #474c55;
         border-radius: 12px; margin: 0 0 16px 0; position: relative;
         -webkit-mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
                 mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);}
.ticker-track {display: inline-block; padding: 10px 0; animation: defile 45s linear infinite;}
.ticker:hover .ticker-track {animation-play-state: paused;}
@keyframes defile {from {transform: translateX(0);} to {transform: translateX(-50%);}}
@media (prefers-reduced-motion: reduce) {.ticker-track {animation: none;}}
.tk {display: inline-flex; align-items: baseline; gap: 8px; padding: 0 26px; border-right: 1px solid #474c55;
     font-size: .88rem;}
.tk, .tk span {text-shadow: none !important;}
.tk .nom {color: #b0b0b0; font-weight: 500;}
.tk .val {color: #efefef; font-weight: 700; font-variant-numeric: tabular-nums;}
.tk .var {font-size: .78rem; font-weight: 600;}
.tk .var.up {color: #8be0a9;}
.tk .var.down {color: #f5a3a3;}
.tk .dt {color: #7d828a; font-size: .74rem;}
"""

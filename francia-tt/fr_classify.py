#!/usr/bin/env python3
"""Classify FR dataset tweets: frame, actor, foreign."""
import json, re

RAW = "/Users/pinperepette/Github/postmortem/francia-tt/fr_dataset_raw.json"
OUT = "/Users/pinperepette/Github/postmortem/francia-tt/fr_dataset.json"

# ---- foreign (non-French amplifier) by handle ----
FOREIGN_HANDLES = {
    "daily_bruxelles", "BruxellesMabel2", "Nouvellesdafriq", "africanewsfr",
    "Nyamuhombeza", "epinoke3018", "Carene1984", "Good_Will2024", "TheNancyRoc",
    "Guigz75116", "BaixSegura_es", "MarioNawfal", "MAGAVoice", "GautamainhP",
    "BergsonBtk600", "SergeNaud", "ya_moto0123", "KURUisKURU", "DTovev",
    "Ellynismos", "Noway499763",
}
# handles that look foreign but are French-domestic actors -> keep non-foreign
FOREIGN_OVERRIDE_FALSE = set()

# ---- actor classification ----
MEDIA_HANDLES = {
    "AlertesInfos", "TF1Info", "CNEWS", "RTLFrance", "Europe1", "GG_RMC",
    "Frontieresmedia", "FrDesouche", "F_Desouche", "BastionMediaFR",
    "Frontieresmedia", "africanewsfr", "Nouvellesdafriq", "daily_bruxelles",
    "RMCInfo", "LeParisien_75", "PoliceRealites", "PoliceSCSI", "BFMTV",
    "MagLiber3", "Observteurdi", "le_Parisien", "LBleuBlancRouge",
}
POLITICIAN_HANDLES = {
    "MarionMarechal", "Clemence_Guette", "eciotti", "EricNaulleau",
    "ljacobelli", "HeleneLaporteRN", "Samuel_Lafont", "mvalet_officiel",
    "J_Bardella",
}
# influencer = large-following activist/commentator accounts (non-official)
INFLUENCER_HANDLES = {
    "PsyGuy007", "Goldenretour", "MatthiasRN", "Ilangabet", "JeremBenhaim",
    "SlMONWEINBERG", "Resistance_SM", "VictorSinclair3", "Mileistesfr",
    "Gdams70", "FranceSouvUnie", "Guigz75116", "MagLiber3", "tegnererik",
    "veritebeaute", "JssAyoub_", "KillianB22", "EstelleMidi", "EdgarFleuryLDF",
}


def classify_frame(text):
    t = text.lower()

    immigration_kw = [
        "immigr", "grand remplac", "remplac", "tiers-monde", "tiers monde",
        "ensauvag", "allog", "ethni", "raciale", "racial", "afriqu", "africain",
        "arabe", "arabo", "magreb", "maghreb", "islam", "envahis", "conquête",
        "conquete", "coup d'état migratoire", "déchoir", "dechoir", "nationalité de papier",
        "français de papier", "racisme anti blanc", "anti blanc", "anti-blanc",
        "expulsions massives", "kaïra", "kaira", "que des arabes", "blacks et des beurs",
        "noir ou arabe", "barbar", "hordes", "horde", "sauvage", "razzia",
    ]
    antisem_kw = ["c'est pour les juifs", "pour les juifs", "lance-roquette",
                  "djihadiste", "intifada", "israël éradiqué", "hamas",
                  "palestiniens en", "drapeaux palestin", "drapeaux de l'algérie et de la palestine"]
    police_state_kw = [
        "préfet", "prefet", "ministre de l'intérieur", "nunez", "nuñez",
        "maintien de l'ordre", "fanzone", "fan zone", "pas de fanzone",
        "infrastructure", "macron", "elysee", "élysée", "gestion de l'ordre",
        "responsabilité de l'état", "responsabilite de l'etat", "incompéten",
        "incompeten", "démission", "demission", "8000", "fdo", "crs avait",
        "laissé faire", "laisse faire", "couvre-feu", "armée dans les rues",
        "irresponsabilité", "préfecture", "prefecture", "sous contrôle",
        "mutualise le coût", "mutualise le cout", "qui paiera", "facture",
    ]
    hooligan_kw = [
        "supporter", "casseur", "débordement", "debordement", "hooligan",
        "fête sportive", "fete sportive", "célébration", "celebration",
        "voitures brûlées", "voiture", "mortier", "pillage", "saccag",
        "fan", "voyou", "lens", "barcelone", "madrid",
    ]
    counter_kw = [
        "il n'y avait pas que des arabes", "non, il n'y avait pas",
        "ce ne sont pas des émeutes", "police française qui les a forcé",
        "0 de qi", "on ne gaze pas", "pas la faute des émeutiers",
        "extrême droite attendait", "pain béni pour l'extrême droite",
        "racaille peut désigner n'importe",
        "détourner le regard", "aucun lien entre les émeutes",
        "n'a pas été organisée",
    ]
    mockery_kw = [
        "image de la france", "ternissent", "le monde nous regarde",
        "le monde entier vous regarde", "font le tour du monde",
        "cité des fleurs", "champions du monde du déni", "champions du monde du deni",
        "pays de confettis", "consternés", "consternes",
        "anomalie dans le monde",
    ]
    news_kw = [
        "interpellations", "780", "890", "219 blessés", "219 blesse",
        "178 policiers", "bilan", "un mort", "57 po", "426 interpellations",
        "480 à paris", "centaines de personnes ont été", "dégradations se poursuivent",
        "police detain", "feu en cours", "incendiée dans le 8",
    ]

    def hit(kws):
        return any(k in t for k in kws)

    # priority order
    if hit(antisem_kw):
        return "antisemitism"
    if hit(counter_kw):
        return "counter"
    if hit(immigration_kw):
        return "immigration"
    if hit(police_state_kw) and not hit(immigration_kw):
        return "police_state"
    if hit(mockery_kw) and not hit(immigration_kw):
        return "mockery"
    # pure neutral news/wire
    if hit(news_kw) and not hit(immigration_kw) and not hit(police_state_kw):
        # neutral if mostly toll figures
        return "news"
    if hit(hooligan_kw):
        return "hooliganism"
    # generic delinquency framing ("racaille/voyou/casse") without ethnic cause
    generic_kw = ["racaille", "voyou", "casse", "saccag", "pillage", "émeut",
                  "emeut", "violenc", "débord", "debord", "chaos", "détru",
                  "detru", "feu", "incendi", "interpellation", "blessé", "blesse"]
    if hit(generic_kw):
        return "hooliganism"
    return "other"


def classify_actor(handle, followers, verified):
    h = handle or ""
    if h in POLITICIAN_HANDLES:
        return "politician"
    if h in MEDIA_HANDLES:
        return "media"
    if h in INFLUENCER_HANDLES:
        return "influencer"
    # heuristic by followers
    if followers and followers >= 50000:
        return "influencer"
    return "user"


def main():
    data = json.load(open(RAW, encoding="utf-8"))
    for r in data:
        h = r["handle"]
        r["frame"] = classify_frame(r["text"])
        r["actor"] = classify_actor(h, r.get("followers", 0), r.get("verified"))
        r["foreign"] = h in FOREIGN_HANDLES
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---- report ----
    from collections import Counter, defaultdict
    n = len(data)
    foreign = [r for r in data if r["foreign"]]
    dom = [r for r in data if not r["foreign"]]
    dates = sorted([r["date"] for r in data if r["date"]])
    authors = set(r["handle"] for r in data)

    frame_n = Counter()
    frame_likes = defaultdict(int)
    for r in dom:
        frame_n[r["frame"]] += 1
        frame_likes[r["frame"]] += r["likes"]
    actor_n = Counter(r["actor"] for r in data)

    print("=== REPORT ===")
    print("on_topic:", n)
    print("date_range:", dates[0], "->", dates[-1])
    print("unique_authors:", len(authors))
    print("foreign:", len(foreign))
    print("\nFRAME (domestic only) [frame: n, sum_likes]")
    for f in ["immigration", "hooliganism", "police_state", "mockery",
              "antisemitism", "news", "counter", "other"]:
        print(f"  {f}: {frame_n.get(f,0)}, {frame_likes.get(f,0)}")
    print("\nACTOR (all):")
    for a, c in actor_n.most_common():
        print(f"  {a}: {c}")
    print("\nTOP 12 by likes:")
    for r in sorted(data, key=lambda x: x["likes"], reverse=True)[:12]:
        snip = r["text"].replace("\n", " ")[:70]
        print(f"  @{r['handle']} | {r['likes']} | {r['frame']} | {snip}")

    htags = Counter()
    for r in data:
        for h2 in r["hashtags"]:
            htags[h2.lower()] += 1
    print("\nTOP HASHTAGS:")
    for h2, c in htags.most_common(15):
        print(f"  #{h2}: {c}")


if __name__ == "__main__":
    main()

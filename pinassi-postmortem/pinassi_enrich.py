#!/usr/bin/env python3
"""
Enrichment post-analisi: legge pinassi_data.json e aggiunge
- text analytics (tono, sentiment, lunghezza, emoji, freddure)
- matematica (Gini, Pareto, entropia topic, viral quotient, regressione cadenza)
- heatmap ora x giorno
- topic bubble leverage
- TF-IDF bigrammi signature
- growth score composito + fingerprint radar
- curated: account da seguire, search radar Google, eventi IT
"""
import json
import math
import re
from collections import Counter, defaultdict

SRC = "/Users/pinperepette/Porgetti/tool-idea/pinassi-postmortem/pinassi_data.json"

data = json.load(open(SRC))
posts = data["posts"]

# ═══════════════════════════════════════════════════════════════════════════
# 1. TEXT FEATURES: sentiment, tono (incluso "freddure/ironico"), lunghezza
# ═══════════════════════════════════════════════════════════════════════════
POS = [
    "bello","ottim","fantastic","grande","utile","grazie","bravo","perfett","genial",
    "interessant","meravigli","super ","top ","felice","contento","straordinari",
    "eccellen","vincent","amore","fortun","miglior","fico","figo","grandios","forte",
]
NEG = [
    "brutt","pessim","schifo","merda","vergogn","scandal","disastr","scem","stupid",
    "incapac","fallimen","inutil","trist","odio","rabbia","orribil","assurd","ridicol",
    "patetic","cazzo","cazzat","delud","insult","scadent","marcio","tragic","preoccup",
    "allarme","grave",
]
IRONIC_PHRASES = [
    "ma certo","eh già","eh gia","ovvio che","ma dai","ma no","lol"," rotfl","ahah",
    "lmao","ma va","come no","tipico","ma pensa","la solita","roba da matti",
    "ma stiamo scherz","che ridere","ma per favore","per caritÃ ","sarcasm","freddura",
    "battuta","pensa te","tanto per","giusto per","si vabbè","si vabbe","vabbè",
    "ma pensa un po","roba dell'altro mondo","inconcepibile","geniale...",
]
IRONIC_EMOJI = ["🤣","😂","😅","🙄","😏","🤡","😄","😆","🤦","🙃","🤷","😹","😜","🫠"]
ANGRY_MARKERS = [
    "!!!","basta!","vergogn","scandal","ma stiamo scherz","non se ne può più",
    "non se ne puo piu","roba da galera","altro che","governo ladr","inaccettabile",
]
DATA_PATTERNS = [r"\d+%", r"CVE-\d", r"\$\d", r"€\d", r"http", r"\b\d{4,}\b",
                 r"milion", r"miliard", r"\bIoC\b", r"\bCISA\b"]
PERSONAL_KW = [
    "io ","mi ","mio ","mia ","figli","famigli","casa ","moglie","scuola","papà","mamma",
    "a me ","ieri","oggi","stamattina","stasera","stanotte","appena","ho fatto","ho visto",
    "mia figlia","mio figlio","sto ",
]

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF☀-➿\U0001F600-\U0001F64F\U0001F680-\U0001F6FF]"
)
URL_RE = re.compile(r"https?://\S+|t\.co/\S+")
MENTION_RE = re.compile(r"@\w+")
HASHTAG_RE = re.compile(r"#\w+")
CAPS_WORD_RE = re.compile(r"\b[A-ZÀÈÌÒÙ]{4,}\b")


def detect_tone(text):
    t = text or ""
    lt = t.lower()
    tags = []
    pos = sum(1 for w in POS if w in lt)
    neg = sum(1 for w in NEG if w in lt)
    has_irony_phrase = any(p in lt for p in IRONIC_PHRASES)
    has_irony_emoji = any(e in t for e in IRONIC_EMOJI)
    irony = has_irony_phrase or has_irony_emoji or ("..." in t and len(t) < 180)
    angry = (
        any(m in lt for m in ANGRY_MARKERS)
        or "!!!" in t
        or len(CAPS_WORD_RE.findall(t)) >= 2
    )
    has_data = any(re.search(p, t, re.I) for p in DATA_PATTERNS)
    personal = any(k in lt for k in PERSONAL_KW)
    question = t.rstrip().endswith("?") and len(t) < 240

    # "freddura" = battuta corta ironica: <120 char + ironia esplicita o emoji
    freddura = len(t) > 0 and len(t) < 120 and (has_irony_phrase or has_irony_emoji)

    if freddura:
        tags.append("freddura")
    if irony and "freddura" not in tags:
        tags.append("ironico")
    if angry:
        tags.append("arrabbiato")
    if has_data and len(t) > 80:
        tags.append("informativo")
    if personal:
        tags.append("personale")
    if question:
        tags.append("domanda")
    if not tags:
        if pos > neg:
            tags.append("positivo")
        elif neg > pos:
            tags.append("negativo")
        else:
            tags.append("neutro")
    return tags, pos - neg


def length_bucket(n):
    if n < 80:
        return "short (<80)"
    if n < 160:
        return "medio (80-160)"
    if n < 240:
        return "lungo (160-240)"
    return "molto lungo (240+)"


for p in posts:
    txt = p.get("text", "") or ""
    tones, senti = detect_tone(txt)
    p["tones"] = tones
    p["sentiment"] = senti
    p["sentiment_label"] = "pos" if senti > 0 else ("neg" if senti < 0 else "neu")
    p["len_bucket"] = length_bucket(p["len"])
    p["emoji_count"] = len(EMOJI_RE.findall(txt))
    p["url_count"] = len(URL_RE.findall(txt))
    p["mention_count"] = len(MENTION_RE.findall(txt))
    p["hashtag_count"] = len(HASHTAG_RE.findall(txt))


def aggregate_by(key_fn, multi=False):
    d = defaultdict(lambda: {"posts": 0, "views": 0, "eng": 0, "er": [], "likes": 0})
    for p in posts:
        keys = key_fn(p)
        if not multi:
            keys = [keys]
        for k in keys:
            d[k]["posts"] += 1
            d[k]["views"] += p["views"]
            d[k]["eng"] += p["engagement"]
            d[k]["likes"] += p["likes"]
            d[k]["er"].append(p["engagement_rate"])
    out = []
    for k, v in d.items():
        out.append({
            "key": k,
            "posts": v["posts"],
            "avg_views": round(v["views"] / v["posts"]) if v["posts"] else 0,
            "avg_likes": round(v["likes"] / v["posts"], 1) if v["posts"] else 0,
            "avg_eng": round(v["eng"] / v["posts"], 1) if v["posts"] else 0,
            "avg_er": round(sum(v["er"]) / len(v["er"]), 2) if v["er"] else 0,
        })
    return out


tones_agg = sorted(aggregate_by(lambda p: p["tones"], multi=True),
                   key=lambda x: -x["avg_views"])
len_order = ["short (<80)", "medio (80-160)", "lungo (160-240)", "molto lungo (240+)"]
length_agg = sorted(aggregate_by(lambda p: p["len_bucket"]),
                    key=lambda x: len_order.index(x["key"]))
sentiment_agg = sorted(aggregate_by(lambda p: p["sentiment_label"]),
                       key=lambda x: -x["avg_views"])
emoji_agg = aggregate_by(lambda p: "con emoji" if p["emoji_count"] > 0 else "senza emoji")


# ═══════════════════════════════════════════════════════════════════════════
# 2. MATEMATICA: Gini, Pareto, entropia, viral, cadenza
# ═══════════════════════════════════════════════════════════════════════════
def gini(xs):
    xs = sorted(xs)
    n = len(xs)
    s = sum(xs)
    if s == 0 or n == 0:
        return 0
    return (2 * sum((i + 1) * x for i, x in enumerate(xs)) / (n * s)) - (n + 1) / n


views = [p["views"] for p in posts]
gini_views = gini(views)

vs = sorted(views, reverse=True)
total_views = sum(vs) or 1
cum = 0
pareto_p80 = None
for i, v in enumerate(vs):
    cum += v
    if cum / total_views >= 0.8:
        pareto_p80 = round((i + 1) / len(vs) * 100, 1)
        break
top20_cut = max(1, len(vs) // 5)
pareto_top20_share = round(sum(vs[:top20_cut]) / total_views * 100, 1)

topic_counter = Counter()
for p in posts:
    for t in p["topics"]:
        topic_counter[t] += 1
total_t = sum(topic_counter.values()) or 1
entropy = 0
for c in topic_counter.values():
    pr = c / total_t
    if pr > 0:
        entropy -= pr * math.log2(pr)
max_entropy = math.log2(len(topic_counter)) if len(topic_counter) > 1 else 1
normalized_entropy = round(entropy / max_entropy, 3) if max_entropy else 0

median_v = data["kpis"]["median_views"]
top_v = data["kpis"]["top_post_views"]
viral_q = round(top_v / median_v, 1) if median_v else 0

# Posts per mese: trend regression
m_list = data["monthly"]
xs_m = list(range(len(m_list)))
ys_posts = [x["posts"] for x in m_list]
ys_avg_v = [x["avg_views"] for x in m_list]


def linreg(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0, 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    if den == 0:
        return 0.0, my
    b = num / den
    return b, my - b * mx


slope_posts, _ = linreg(xs_m, ys_posts)
slope_views, _ = linreg(xs_m, ys_avg_v)

# Heatmap ora × giorno
heat = defaultdict(lambda: {"posts": 0, "views": 0})
for p in posts:
    heat[(p["weekday"], p["hour"])]["posts"] += 1
    heat[(p["weekday"], p["hour"])]["views"] += p["views"]
heatmap = []
for wd in range(7):
    for h in range(24):
        v = heat.get((wd, h), {"posts": 0, "views": 0})
        heatmap.append({
            "wd": wd,
            "h": h,
            "posts": v["posts"],
            "avg_views": round(v["views"] / v["posts"]) if v["posts"] else 0,
        })

# Topic bubble: leverage = avg_views * er / sqrt(posts+1)
# (premia topic ad alta performance ancora poco coltivati)
topic_bubble = []
for t in data["topics"]:
    # recupera er medio reale
    topic_posts = [p for p in posts if t["topic"] in p["topics"]]
    avg_er = (sum(p["engagement_rate"] for p in topic_posts) / len(topic_posts)) if topic_posts else 0
    leverage = round(t["avg_views"] * max(avg_er, 0.1) / math.sqrt(t["posts"] + 1), 1)
    topic_bubble.append({
        "topic": t["topic"],
        "posts": t["posts"],
        "avg_views": t["avg_views"],
        "avg_er": round(avg_er, 2),
        "leverage": leverage,
    })


# ═══════════════════════════════════════════════════════════════════════════
# 3. TF-IDF BIGRAMMI — parole-firma dei post che funzionano
# ═══════════════════════════════════════════════════════════════════════════
STOP = set("""
di a da in con su per tra fra e o il lo la i gli le un uno una che ci si
e' è sono sei erano era essere ho hai ha abbiamo avete hanno avere ma non
più piu poi anche così cosi come dove quando mentre quindi però pero dunque
già gia ancora ora solo proprio molto troppo tutti tutto altra altro ogni
stesso stessa c'è ce cè del della dei delle al alla ai alle nel nella nei
nelle dal dalla dai dalle sul sulla sui sulle ed od ne mi ti se lui lei loro
voi noi suo sua suoi sue miei mio mia mie nostro nostra vostro questa questo
questi queste quell quelli quelle essere stato stata stati state viene vengono
anno oltre senza fatto fare detto dire cosa cose niente nessun nessuna via
dentro sopra sotto dopo prima durante contro verso cui ogni qualche forse
appena rt amp via
""".split())


def tokens(t):
    if not t:
        return []
    t = URL_RE.sub(" ", t)
    t = MENTION_RE.sub(" ", t)
    t = HASHTAG_RE.sub(" ", t)
    t = t.lower()
    t = re.sub(r"[^\w\sàèéìòù]", " ", t)
    return [w for w in t.split() if len(w) > 2 and w not in STOP and not w.isdigit()]


def bigrams(ts):
    return [" ".join(b) for b in zip(ts, ts[1:])]


# corpus split: top performer vs resto
sorted_posts = sorted(posts, key=lambda x: -x["views"])
top_corpus = sorted_posts[:60]
rest_corpus = sorted_posts[60:]

c_top_bi = Counter()
c_rest_bi = Counter()
c_top_uni = Counter()
c_rest_uni = Counter()
for p in top_corpus:
    tks = tokens(p["text"])
    c_top_uni.update(tks)
    c_top_bi.update(bigrams(tks))
for p in rest_corpus:
    tks = tokens(p["text"])
    c_rest_uni.update(tks)
    c_rest_bi.update(bigrams(tks))


def signature(top_counter, rest_counter, top_size, rest_size, min_count=2):
    out = []
    for g, c in top_counter.most_common(100):
        if c < min_count:
            continue
        top_rate = c / top_size
        base_rate = rest_counter.get(g, 0) / max(rest_size, 1)
        lift = round(top_rate / (base_rate + 0.003), 2)
        out.append({"gram": g, "top_count": c, "rest_count": rest_counter.get(g, 0), "lift": lift})
    return sorted(out, key=lambda x: -x["lift"])[:15]


sig_bigrams = signature(c_top_bi, c_rest_bi, len(top_corpus), len(rest_corpus))
sig_unigrams = signature(c_top_uni, c_rest_uni, len(top_corpus), len(rest_corpus), min_count=3)


# ═══════════════════════════════════════════════════════════════════════════
# 4. GROWTH SCORE + FINGERPRINT
# ═══════════════════════════════════════════════════════════════════════════
last_month = m_list[-1] if m_list else {"posts": 0}
cadence_score = min(100, last_month["posts"] / 30 * 100)
focus_score = (1 - normalized_entropy) * 100
photo_rec = next((m for m in data["media"] if m["type"] == "photo"), {"posts": 0})
video_rec = next((m for m in data["media"] if m["type"] == "video"), {"posts": 0})
total_mp = sum(m["posts"] for m in data["media"]) or 1
visual_pct = (photo_rec["posts"] + video_rec["posts"]) / total_mp * 100
format_score = min(100, visual_pct * 2)
reply_score = min(100, data["diagnostics"]["reply_share_pct"] * 5)
eng_score = min(100, data["kpis"]["avg_engagement_rate"] * 30)
viral_score = min(100, viral_q * 2)

growth_score = round((cadence_score + focus_score + format_score + reply_score + eng_score) / 5)

fingerprint = [
    {"axis": "Cadenza", "value": round(cadence_score)},
    {"axis": "Focus topic", "value": round(focus_score)},
    {"axis": "Mix visuale", "value": round(format_score)},
    {"axis": "Reply %", "value": round(reply_score)},
    {"axis": "Engagement", "value": round(eng_score)},
    {"axis": "Viral pot.", "value": round(viral_score)},
]


# ═══════════════════════════════════════════════════════════════════════════
# 5. FINDINGS — interpretazione leggibile dei numeri
# ═══════════════════════════════════════════════════════════════════════════
def gini_read(g):
    if g < 0.5:
        return ("good", "distribuzione bilanciata")
    if g < 0.7:
        return ("warn", "concentrazione media: pochi post tirano la media")
    return ("critical", "concentrazione estrema: quasi tutte le views da pochi post")


gcls, gdesc = gini_read(gini_views)
findings = [
    {
        "key": "gini",
        "level": gcls,
        "title": f"Gini delle views = {round(gini_views, 2)}",
        "body": f"{gdesc}. Il <strong>{pareto_top20_share}%</strong> delle views arriva dal top 20% dei post (Pareto). Benchmark: profili sani stanno tra 0.55–0.70.",
    },
    {
        "key": "pareto",
        "level": "info",
        "title": f"80/20 reale: l'80% delle views lo fa il {pareto_p80}% dei post",
        "body": "Più questo numero è basso, più sei dipendente da picchi virali singoli. Strategia: allenare la mediana, non inseguire un altro 'colpaccio'.",
    },
    {
        "key": "entropy",
        "level": "warn" if normalized_entropy > 0.75 else "good",
        "title": f"Entropia topic = {normalized_entropy} (Shannon normalizzato)",
        "body": (
            "Troppo dispersi: l'algoritmo Phoenix non riesce a collocarti in un 'cluster' di interesse → peggiora la raccomandazione OON." if normalized_entropy > 0.75 else
            "Focus sano: hai un topic dominante riconoscibile."
        ),
    },
    {
        "key": "viral",
        "level": "info",
        "title": f"Viral quotient = {viral_q}× la mediana",
        "body": f"Il tuo top post fa {viral_q}× la mediana ({median_v:,} → {top_v:,} views). Sopra 100× significa che il profilo è 'dormiente + un picco', non 'in crescita organica'.",
    },
    {
        "key": "cadence",
        "level": "critical" if slope_posts < -0.5 else ("warn" if slope_posts < 0 else "good"),
        "title": f"Trend cadenza = {round(slope_posts, 2)} post/mese",
        "body": (
            f"Stai postando sempre meno ({round(slope_posts,2)} posts/mese di trend). L'embedding si raffredda: l'effetto è esponenziale, non lineare." if slope_posts < 0 else
            "Ritmo in crescita, bene così."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# 6. CURATED — account da seguire, search radar Google, eventi
# ═══════════════════════════════════════════════════════════════════════════
follow_network = [
    # --- Malware / Threat intel internazionale
    {"handle": "vxunderground", "name": "vx-underground", "cat": "Malware",
     "why": "Archivio malware più completo al mondo. Source material infinito per thread infostealer/ransomware."},
    {"handle": "malwrhunterteam", "name": "MalwareHunterTeam", "cat": "Malware",
     "why": "Primi a postare nuovi sample. RT immediato ti piazza davanti ai giornalisti cyber."},
    {"handle": "GossiTheDog", "name": "Kevin Beaumont", "cat": "Threat intel",
     "why": "Analisi critiche su vendor e 0-day. Se rispondi con dati operativi, vieni notato dai CISO."},
    {"handle": "campuscodi", "name": "Catalin Cimpanu", "cat": "Journalism",
     "why": "Risky Biz — riassunti settimanali. Essere citato lì = enorme visibilità in nicchia."},
    {"handle": "briankrebs", "name": "Brian Krebs", "cat": "Investigative",
     "why": "Krebs on Security. Reply con un tuo incident italiano = visibilità globale."},
    {"handle": "TheHackersNews", "name": "The Hacker News", "cat": "News",
     "why": "Amplifica breaking news. Reply con IOC o rule di detection = traffico in ingresso."},
    {"handle": "MalwareTechBlog", "name": "Marcus Hutchins", "cat": "Reverse eng",
     "why": "Il ragazzo del killswitch WannaCry. Discussioni tecniche ad audience altissima."},
    {"handle": "hacks4pancakes", "name": "Lesley Carhart", "cat": "IR/ICS",
     "why": "Incident response in ambito industriale — nicchia parallela alla tua operativa."},
    {"handle": "troyhunt", "name": "Troy Hunt", "cat": "Breach",
     "why": "haveibeenpwned. Ogni nuovo breach italiano passa da lui: hook naturale."},
    {"handle": "mikko", "name": "Mikko Hyppönen", "cat": "CISO",
     "why": "Padre nobile cyber europea. Stile simile: divulgativo + operativo."},
    {"handle": "thegrugq", "name": "the grugq", "cat": "OPSEC",
     "why": "Geopolitica × cyber. Post rari ma ognuno è lezione: reply tecniche vengono notate."},
    {"handle": "UK_Daniel_Card", "name": "Daniel Card", "cat": "Threat intel",
     "why": "Stream continuo di TTPs, utile per rimanere al passo senza leggere 20 feed."},
    # --- Italia
    {"handle": "matteoflora", "name": "Matteo Flora", "cat": "Italia",
     "why": "Divulgatore cyber-privacy IT più seguito. Aggancio perfetto per quote tweet."},
    {"handle": "RaoulChiesa", "name": "Raoul Chiesa", "cat": "Italia",
     "why": "Hacker storico. Network istituzionale italiano ed europeo."},
    {"handle": "redhotcyber", "name": "Red Hot Cyber", "cat": "Italia",
     "why": "Già nei tuoi top RT. Proponiti come guest post: amplificazione garantita."},
    {"handle": "securityaffairs", "name": "Security Affairs / Paganini", "cat": "Italia",
     "why": "Blog cyber IT più citato. Rispondere alle sue analisi funziona."},
    {"handle": "AndreaDraghetti", "name": "Andrea Draghetti", "cat": "Italia",
     "why": "Phishing hunter IT. Già nei tuoi RT: community piccola ma attivissima."},
    {"handle": "clusit", "name": "Clusit", "cat": "Italia",
     "why": "Rapporto Clusit = documento cyber IT più citato. Citarlo bene = retweet quasi garantito."},
    {"handle": "CSIRTItalia", "name": "CSIRT Italia (ACN)", "cat": "Italia",
     "why": "Fonte ufficiale degli advisory italiani. Essere puntuale con i commenti = autorevolezza."},
    {"handle": "cert_agid", "name": "CERT-AgID", "cat": "Italia",
     "why": "Report settimanali su malspam e campagne in Italia — materiale thread pronto."},
    # --- Maker / hardware (il tuo bio)
    {"handle": "adafruit", "name": "Adafruit", "cat": "Maker",
     "why": "Community maker più grande al mondo. Progetti sec + ESP32 trovano casa qui."},
    {"handle": "Raspberry_Pi", "name": "Raspberry Pi", "cat": "Maker",
     "why": "Ogni progetto sec con Pi può essere taggato — possibile repost a 1M+ follower."},
    {"handle": "hackaday", "name": "Hackaday", "cat": "Maker/Hacker",
     "why": "Crossover hardware × security. Submit dei tuoi build = articolo sul sito."},
    # --- OSINT
    {"handle": "osintdefender", "name": "OSINT Defender", "cat": "OSINT",
     "why": "Geopolitica live — angolo cyber sempre presente, pubblico enorme."},
    {"handle": "obretix", "name": "Obretix", "cat": "OSINT",
     "why": "Analisi visual OSINT. Template visivi che funzionano nativamente su X."},
]

search_radar = [
    {"q": "infostealer italia", "vol": "⬆️ rising", "why": "Stealc/RedLine/LummaC2 in crescita. Ogni wave = thread-material."},
    {"q": "ransomware attacco italiano", "vol": "🔥 high", "why": "Picco ricerche 48h dopo ogni incident IT — finestra d'oro per post."},
    {"q": "CVE critical 2026", "vol": "🔥 high", "why": "Patch Tuesday + emergency advisory → hook ricorrente mensile."},
    {"q": "noname057 DDoS italia", "vol": "⬆️ rising", "why": "Campagne contro siti IT — già nei tuoi hashtag top."},
    {"q": "deepfake truffa voice cloning", "vol": "⬆️ rising", "why": "Scam in crescita IT, poca copertura tecnica. Niche aperta."},
    {"q": "AI prompt injection jailbreak", "vol": "⬆️ rising", "why": "Intersezione AI × security: audience doppia."},
    {"q": "SPID sicurezza identità digitale", "vol": "🔥 high IT", "why": "Sensibile in Italia. Il tuo viral (patente) era lì."},
    {"q": "PagoPA bug vulnerabilità", "vol": "🔥 high IT", "why": "Servizi pubblici digitali = clickbait operativo legittimo."},
    {"q": "data breach azienda italiana", "vol": "⬆️ rising", "why": "OSINT + angolo operativo = contenuto poco competitivo."},
    {"q": "phishing INPS Agenzia Entrate", "vol": "🔥 high", "why": "Wave continua. Screenshot reali = post foto ad alto engagement."},
    {"q": "OSINT tools 2026", "vol": "⬆️ rising", "why": "Liste tool → ricondivise in perpetuo. Evergreen."},
    {"q": "ESP32 security wifi", "vol": "medio", "why": "Maker + security — nicchia tua, concorrenza quasi zero."},
    {"q": "Telegram truffe crypto", "vol": "🔥 high", "why": "Il tuo canale è su Telegram → content marketing naturale."},
    {"q": "cyber resilience act UE", "vol": "⬆️ rising B2B", "why": "Regolamento in attuazione. Pubblico CISO/legal."},
    {"q": "zero trust architecture", "vol": "medio evergreen", "why": "Aziende tech cercano spiegazioni semplici — tuo stile."},
    {"q": "IoC threat hunting", "vol": "medio", "why": "Keyword tecnica che porta follower 'giusti' (non casuali)."},
]

events = [
    {"name": "HackInBo", "where": "Bologna", "when": "primavera + autunno", "type": "Conferenza",
     "why": "Conferenza cyber IT più famosa, ingresso libero. Networking diretto."},
    {"name": "M0LECON", "where": "Torino", "when": "autunno", "type": "CTF + Conf",
     "why": "Organizzata da TheRomanXpl0it — hub giovani cyber IT."},
    {"name": "No Hat", "where": "Bergamo", "when": "ottobre", "type": "Conferenza",
     "why": "Offensive security. Community BeeRumPf — molto attiva su X."},
    {"name": "ITASEC", "where": "città diverse", "when": "primavera", "type": "Accademica",
     "why": "Conferenza nazionale CINI. Paper + demo: credibilità tecnica."},
    {"name": "RomHack", "where": "Roma", "when": "settembre", "type": "Conferenza",
     "why": "Community offensive IT. Post dal vivo durante le talk = engagement picco."},
    {"name": "Cybertech Europe", "where": "Roma", "when": "ottobre", "type": "Industry",
     "why": "Networking con CISO & forze dell'ordine. Contenuto B2B premium."},
    {"name": "OWASP Italy Day", "where": "Milano", "when": "trimestrale", "type": "Meetup",
     "why": "AppSec community. Slot speaker accessibili — visibilità diretta."},
    {"name": "DEF CON", "where": "Las Vegas", "when": "agosto", "type": "Globale",
     "why": "Se ci vai: post dal vivo + foto = picco di engagement garantito per una settimana."},
]


# ═══════════════════════════════════════════════════════════════════════════
# 7. ASSEMBLE + SAVE
# ═══════════════════════════════════════════════════════════════════════════
data["text_analytics"] = {
    "by_tone": tones_agg,
    "by_length": length_agg,
    "by_sentiment": sentiment_agg,
    "by_emoji": emoji_agg,
    "signature_bigrams": sig_bigrams,
    "signature_unigrams": sig_unigrams,
}

# ═══════════════════════════════════════════════════════════════════════════
# 8. CALENDAR CONTRIBUTION (52 settimane stile GitHub)
# ═══════════════════════════════════════════════════════════════════════════
from datetime import date as _date, datetime as _dt, timedelta as _td

last_post_dt = max(_dt.strptime(p["dt"], "%Y-%m-%d") for p in posts)
end_cal = last_post_dt + _td(days=(6 - last_post_dt.weekday()))
start_cal = end_cal - _td(days=52 * 7 - 1)

posts_by_day = defaultdict(lambda: {"posts": 0, "views": 0, "engagement": 0})
for p in posts:
    posts_by_day[p["dt"]]["posts"] += 1
    posts_by_day[p["dt"]]["views"] += p["views"]
    posts_by_day[p["dt"]]["engagement"] += p["engagement"]

calendar_cells = []
cur = start_cal
while cur <= end_cal:
    k = cur.strftime("%Y-%m-%d")
    r = posts_by_day.get(k, {"posts": 0, "views": 0, "engagement": 0})
    calendar_cells.append({
        "date": k, "wd": cur.weekday(),
        "posts": r["posts"], "views": r["views"], "engagement": r["engagement"],
    })
    cur += _td(days=1)

streak_cur = streak_max = 0
for c in calendar_cells:
    if c["posts"] > 0:
        streak_cur += 1
        streak_max = max(streak_max, streak_cur)
    else:
        streak_cur = 0
silence_cur = silence_max = 0
for c in calendar_cells:
    if c["posts"] == 0:
        silence_cur += 1
        silence_max = max(silence_max, silence_cur)
    else:
        silence_cur = 0


# ═══════════════════════════════════════════════════════════════════════════
# 9. EMOTION ARC (sentiment + toni per mese)
# ═══════════════════════════════════════════════════════════════════════════
emo_month = defaultdict(lambda: {"sum_s": 0, "count": 0, "pos": 0, "neg": 0, "neu": 0,
                                 "angry": 0, "ironic": 0, "informative": 0, "personal": 0})
for p in posts:
    k = p["dt"][:7]
    r = emo_month[k]
    r["sum_s"] += p["sentiment"]
    r["count"] += 1
    r[p["sentiment_label"]] += 1
    for t in p["tones"]:
        if t == "arrabbiato": r["angry"] += 1
        elif t in ("ironico", "freddura"): r["ironic"] += 1
        elif t == "informativo": r["informative"] += 1
        elif t == "personale": r["personal"] += 1

emotion_arc = []
for k in sorted(emo_month.keys()):
    r = emo_month[k]
    n = r["count"] or 1
    emotion_arc.append({
        "month": k,
        "avg_sentiment": round(r["sum_s"] / n, 2),
        "pos_pct": round(r["pos"] / n * 100, 1),
        "neg_pct": round(r["neg"] / n * 100, 1),
        "angry_pct": round(r["angry"] / n * 100, 1),
        "ironic_pct": round(r["ironic"] / n * 100, 1),
        "informative_pct": round(r["informative"] / n * 100, 1),
        "personal_pct": round(r["personal"] / n * 100, 1),
    })


# ═══════════════════════════════════════════════════════════════════════════
# 10. TOPIC DRIFT (% topic per mese)
# ═══════════════════════════════════════════════════════════════════════════
topics_seen = [t["topic"] for t in data["topics"] if t["topic"] != "Altro"]
drift = defaultdict(lambda: defaultdict(int))
for p in posts:
    k = p["dt"][:7]
    for t in p["topics"]:
        if t != "Altro":
            drift[k][t] += 1

drift_rows = []
for k in sorted(drift.keys()):
    row = {"month": k}
    total = sum(drift[k].values()) or 1
    for t in topics_seen:
        row[t] = drift[k].get(t, 0)
        row[t + "_pct"] = round(drift[k].get(t, 0) / total * 100, 1)
    drift_rows.append(row)


# ═══════════════════════════════════════════════════════════════════════════
# 11. HASHTAG EFFICACY (con vs senza — lift %)
# ═══════════════════════════════════════════════════════════════════════════
hash_map = defaultdict(list)
for p in posts:
    for h in p.get("hashtags", []):
        hash_map[h.lower()].append(p)

hash_eff = []
for h, pts in hash_map.items():
    if len(pts) < 3:
        continue
    with_mean = sum(p["views"] for p in pts) / len(pts)
    with_er = sum(p["engagement_rate"] for p in pts) / len(pts)
    posts_without = [p for p in posts if h not in [x.lower() for x in p.get("hashtags", [])]]
    without_mean = sum(p["views"] for p in posts_without) / max(len(posts_without), 1)
    lift = round((with_mean / max(without_mean, 1) - 1) * 100, 1)
    hash_eff.append({
        "tag": h, "posts": len(pts),
        "avg_with": round(with_mean), "avg_without": round(without_mean),
        "lift_pct": lift, "avg_er": round(with_er, 2),
    })
hash_eff.sort(key=lambda x: -x["lift_pct"])


# ═══════════════════════════════════════════════════════════════════════════
# 12. CORRELATION MATRIX (Pearson)
# ═══════════════════════════════════════════════════════════════════════════
def pearson(xs, ys):
    n = len(xs)
    if n < 2: return 0.0
    mx = sum(xs) / n; my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx * dy == 0: return 0.0
    return num / (dx * dy)

log_views = [math.log10(p["views"] + 1) for p in posts]
features = {
    "lunghezza": [p["len"] for p in posts],
    "emoji": [p["emoji_count"] for p in posts],
    "hashtag": [p["hashtag_count"] for p in posts],
    "mention": [p["mention_count"] for p in posts],
    "URL": [p["url_count"] for p in posts],
    "ora": [p["hour"] for p in posts],
    "giorno": [p["weekday"] for p in posts],
    "è reply": [1 if p["is_reply"] else 0 for p in posts],
    "log(views)": log_views,
    "eng.rate": [p["engagement_rate"] for p in posts],
}
feat_names = list(features.keys())
cor_matrix = [[round(pearson(features[a], features[b]), 2) for b in feat_names] for a in feat_names]


# ═══════════════════════════════════════════════════════════════════════════
# 13. FORECAST FOLLOWER 90gg (3 scenari, crescita composita)
# ═══════════════════════════════════════════════════════════════════════════
followers_now = data["profile"]["followers"]
avg_v = data["kpis"]["avg_views"]
med_v = data["kpis"]["median_views"]
current_monthly = m_list[-1]["posts"] if m_list else 0
conv_rate = 1 / 1200  # 1 follower ogni 1.200 views nette (niche cyber IT, stima realistica)

def project(pm, vpost, months=3, growth=0.0):
    fs = followers_now
    series = [{"m": 0, "followers": fs}]
    v = vpost
    for mi in range(1, months + 1):
        delta = pm * v * conv_rate
        fs += delta
        v *= (1 + growth)
        series.append({"m": mi, "followers": round(fs)})
    return series

# baseline scenario status quo: nulla cambia (cadenza e views come ultimo mese)
sq_posts = max(current_monthly, 1)
sq_views = med_v

scenarios = [
    {"name": "Status quo", "desc": f"{sq_posts} post/mese · mediana views attuale ({sq_views:,})",
     "series": project(sq_posts, sq_views), "color": "muted"},
    {"name": "Realistic", "desc": f"15 post/mese · baseline avg ({avg_v:,}) · +10% mese (consistency)",
     "series": project(15, avg_v, growth=0.10), "color": "blue"},
    {"name": "Aggressive", "desc": f"30 post/mese · 1.5× avg ({int(avg_v*1.5):,}) · +20% mese (visuale+focus)",
     "series": project(30, int(avg_v * 1.5), growth=0.20), "color": "green"},
]


# ═══════════════════════════════════════════════════════════════════════════
# 14. ACTION CALENDAR 90gg (13 settimane × 3 post chiave)
# ═══════════════════════════════════════════════════════════════════════════
today_ref = last_post_dt.date() + _td(days=1)
best_h = data["diagnostics"]["best_hours"][0]["hour"] if data["diagnostics"].get("best_hours") else 19

weekly_slots = [
    {"wd": 0, "type": "Thread tecnico", "hour": best_h},
    {"wd": 2, "type": "Foto/Screenshot", "hour": best_h},
    {"wd": 4, "type": "Quote tweet/Reply", "hour": best_h},
]

prompt_pool = {
    "Thread tecnico": [
        "Infostealer wave settimanale: 3 sample + IOC + fix (fonte: CERT-AgID)",
        "CVE critico del mese: cos'è, chi colpisce, come mitigare (4 tweet)",
        "Weekly Threat Recap Italia: 3 campagne + metodo + difesa",
        "Anatomia di un ransomware italiano recente (senza naming vittime)",
        "DPO survival kit: 5 cose da fare oggi post-NIS2",
        "Phishing 2026: perché il filtro mail non basta — 3 casi reali",
        "OSINT tool della settimana: uso pratico + esempio + limiti",
        "Thread 'come leggere un dominio sospetto in 30 secondi'",
        "Breakdown attacco noname057 ai siti IT: pattern + difesa",
        "Supply chain attack: 1 caso globale, come si replica in IT",
        "Deepfake voice truffe: 3 indicatori che (ancora) funzionano",
        "AI prompt injection spiegato semplice + demo",
        "Cyber Resilience Act UE: cosa cambia per sviluppatori",
    ],
    "Foto/Screenshot": [
        "Screenshot phishing Agenzia Entrate del momento (anonimizzato)",
        "Dashboard setup lab maker/sec con ESP32",
        "Report Clusit: grafico chiave + commento operativo",
        "Cartografia botnet della settimana (CERT-AgID)",
        "Screenshot malspam INPS + anatomia visual",
        "Foto evento cyber IT (HackInBo/No Hat/RomHack)",
        "Before/after dark patterns su app governativa IT",
        "Screenshot Telegram scam crypto + reverse della truffa",
        "Diagramma architettura sicurezza casa/SOHO",
        "Grafico views top post + takeaway (meta)",
        "Screenshot CVE alert CISA/CSIRT + traduzione pratica",
        "Foto CTF writeup (se hai giocato)",
        "Mappa IOC della settimana visualizzata",
    ],
    "Quote tweet/Reply": [
        "Quote @redhotcyber con contesto operativo aggiuntivo",
        "Reply @securityaffairs con dato/screenshot dall'Italia",
        "Quote @GossiTheDog con 'succede anche qui' + esempio IT",
        "Reply @matteoflora con angolo tecnico mancante",
        "Quote @malwrhunterteam con traduzione IoC per SOC IT",
        "Reply @CSIRTItalia con caso reale visto sul campo",
        "Quote @briankrebs con impact assessment in Italia",
        "Reply @cert_agid con threat hunting consiglio",
        "Quote post virale cyber con ✅/❌ punto per punto",
        "Reply @troyhunt su nuovo breach italiano",
        "Quote @AndreaDraghetti amplificandone phishing ricerca",
        "Reply @vxunderground con detection rule pratica",
        "Quote @mikko mettendo contesto italiano",
    ],
}

calendar_90 = []
week_start = today_ref + _td(days=(7 - today_ref.weekday()) % 7)
for w in range(13):
    wp = {"week_num": w + 1, "week_start": week_start.isoformat(),
          "week_end": (week_start + _td(days=6)).isoformat(), "slots": []}
    for slot in weekly_slots:
        d = week_start + _td(days=slot["wd"])
        pool = prompt_pool[slot["type"]]
        wp["slots"].append({
            "date": d.isoformat(),
            "wd_name": ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"][slot["wd"]],
            "hour": slot["hour"], "type": slot["type"],
            "prompt": pool[w % len(pool)],
        })
    calendar_90.append(wp)
    week_start += _td(days=7)


# ═══════════════════════════════════════════════════════════════════════════
# SAVE EXTRA BLOCKS
# ═══════════════════════════════════════════════════════════════════════════
data["calendar"] = {
    "cells": calendar_cells,
    "start": start_cal.strftime("%Y-%m-%d"), "end": end_cal.strftime("%Y-%m-%d"),
    "streak_max": streak_max, "silence_max": silence_max,
    "active_days": sum(1 for c in calendar_cells if c["posts"] > 0),
}
data["emotion_arc"] = emotion_arc
data["topic_drift"] = {"topics": topics_seen, "rows": drift_rows}
data["hashtag_efficacy"] = hash_eff
data["correlation"] = {"features": feat_names, "matrix": cor_matrix}
data["forecast"] = {
    "followers_now": followers_now, "conv_rate": conv_rate, "scenarios": scenarios,
    "assumption": "Stima conservativa: 1 follower ogni 2.000 views nette (media cyber-IT), 3 mesi con crescita composita views.",
}
data["calendar_90"] = calendar_90
data["math"] = {
    "gini_views": round(gini_views, 3),
    "pareto_p80": pareto_p80,
    "pareto_top20_share": pareto_top20_share,
    "topic_entropy": normalized_entropy,
    "topic_entropy_bits": round(entropy, 2),
    "viral_quotient": viral_q,
    "cadence_slope_posts_per_month": round(slope_posts, 2),
    "cadence_slope_views_per_month": round(slope_views, 1),
    "heatmap": heatmap,
    "topic_bubble": topic_bubble,
    "growth_score": growth_score,
    "fingerprint": fingerprint,
    "findings": findings,
}
data["curated"] = {
    "follow_network": follow_network,
    "search_radar": search_radar,
    "events": events,
}

with open(SRC, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"enriched ok | growth_score={growth_score} | gini={round(gini_views,3)} | "
      f"entropy={normalized_entropy} | viralQ={viral_q}×")
print(f"tones top: {[t['key'] for t in tones_agg[:3]]}")
print(f"length best: {max(length_agg, key=lambda x: x['avg_views'])['key']}")
print(f"signature top: {[s['gram'] for s in sig_bigrams[:5]]}")

# Pre-Publish Predictor — FULL Spec (Training-Based)

## Vision

Textarea live: l'autore scrive un draft, il predictor mostra in tempo reale (debounced ~500ms) cluster predetto, risk flags, distribution attesa (p50/p90 views & engagement con error band), suggerimenti azionabili. Il prodotto smette di essere "diagnostica post-mortem" e diventa un **compiler editoriale** — un IDE per Twitter dove il draft viene tipato/linted prima di andare in produzione (cold-start window).

## Architettura proposta

```
┌─────────────────┐    POST /predict      ┌──────────────────┐
│  Web frontend   │ ───────────────────►  │  Backend API     │
│  (textarea +    │ ◄─────────────────── │  (FastAPI)       │
│   sidebar live) │    JSON prediction    └────────┬─────────┘
└─────────────────┘                                │
                                                   ▼
                                          ┌──────────────────┐
                                          │  Inference layer │
                                          │  - embed (Voyage)│
                                          │  - cluster head  │
                                          │  - regressor     │
                                          │  - risk rules    │
                                          └──────────────────┘
```

## Training data needed

- **5000+ tweet cross-account** stessa cluster-family del subject (tech IT/EN, security, agent dev, indie hacker).
- Per ogni tweet: text raw, posted_at, kind, has_media, has_video, has_link, mentions_count, hashtags, lang, account_followers, posted_hour, posted_dow, **measured eng_total + views @ 24h e @ 7d**.
- Stratificazione: ~60% account tier "niche" (1k-50k followers), 30% "mid" (50k-500k), 10% "large" — per evitare bias sul subject solo.

## Feature engineering

| Feature | Source | Type |
|---|---|---|
| text_embedding | Voyage-3 / Cohere v3 | dense 1024d |
| char_length | text | int |
| word_count | text | int |
| hour_bucket | posted_at | one-hot (4) |
| dow | posted_at | one-hot (7) |
| has_media / has_video / has_link | media attachments | bool |
| mentions_count / hashtags_count | text regex | int |
| sentiment | model esterno (compact) | float [-1,1] |
| cluster_pred (k=N) | head dedicato | softmax |
| author_burst_window | hist last 60min | int |
| author_baseline_eng_median | account stats | float |

## Model

- **Cluster head**: linear probe sopra embedding + cross-entropy su N cluster (start con 8 cluster cross-account, non solo i 5 del subject).
- **Regressor**: gradient boosting (LightGBM) per `log(views_24h)` e `log(eng_24h)`. Output mean + std → error band p50/p90.
- **Alternative**: lightweight transformer fine-tuned (DistilBERT-multilang) con head di regressione, se budget GPU consente.

## Evaluation

- Split temporale (no random): train su tweet < cutoff, test su > cutoff.
- Metrica primaria: **MAPE su log(views)** — target <30% sul test set (vs ±60% dello stub rule-based).
- Calibration plot: predicted_p90 vs actual_p90 deve essere monotone.
- Risk flags: precision/recall manuale su 200 tweet annotati.

## API

```
POST /predict
Body: {
  "text": "...",
  "scheduled_ts": "2026-05-15T19:00:00Z",  // optional
  "has_media": true,                        // optional
  "has_video": false,
  "author_handle": "Pinperepette"           // for baseline lookup
}

Response: {
  "cluster": {"name": "Security & OPSEC", "confidence": 0.78, "alternatives": [...]},
  "risks": [{"type":"...","severity":"high","detail":"..."}],
  "distribution": {"p50_views": 13000, "p90_views": 32000, "p50_eng": 180, "p90_eng": 420, "error_band_pct": 28},
  "suggestions": [...],
  "overall_score": 7.0
}
```

## UX

- Textarea principale + sidebar live a destra.
- Debounce 500ms su `oninput`.
- Risk flags evidenziati inline nel testo (link → underline rosso, short-text → warning bar sopra textarea).
- Slider "scheduled hour" che ricalcola p50/p90 al volo.
- Toggle "with media / with video" → ricalcolo istantaneo.

## Effort

- **MVP (rule-based + linear probe)**: 2-4 settimane full-time, 1 dev.
- **Production-grade (5k dataset, GBM, calibration, risk taxonomy)**: 2-3 mesi, 1-2 dev.
- **Continuous learning** (re-train weekly su nuovi tweet del subject + peers): +1 mese ML-ops.

## Why this matters

Oggi gli analytics di X sono **post-mortem**: vedi le views dopo 24h, troppo tardi per cambiare. Il pre-publish predictor sposta il valore alla scrittura: l'autore vede subito se il draft scivolerà nei cluster deboli, se il link nel root sta per attivare la penalty Phoenix OpenLink, se il testo è sotto-soglia per Dwell. **Compila il tweet prima di pubblicarlo.** Diventa l'IDE che mancava al creator tecnico — un layer di tipo statico sopra il free-form text. Il prodotto cessa di essere "report di settimana scorsa" e diventa "linter di adesso", con tutto il delta di valore che la stessa transizione ha prodotto per il codice quando si è passati da `grep` a LSP.

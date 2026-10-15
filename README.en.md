# ScamCall Shield 🛡️

> Check suspicious messages, calls, images, videos, and files — multimodal scam
> analysis that runs **100% in your browser**. Bilingual Vietnamese/English,
> private by default.

An entry for the **Vibe Coding Challenge**. No backend, no accounts, and no tracking cookies.
The content you analyze **does not automatically leave your device**.

---

## ✨ Key Features

| Input | Description |
|---|---|
| 💬 **Text** | Paste SMS, email, or Zalo messages. Highlight manipulative phrases, assign a 0–100 risk score, classify scam scenarios, and provide a prioritized response plan. |
| 🎙 **Voice** | Record up to 60 seconds and automatically transcribe speech using the Web Speech API, with manual text entry always available as a fallback. Read results aloud in Family Mode. |
| 🖼 **Images** | Vietnamese and English OCR (Tesseract.js), QR decoding (jsQR), drag-to-select regions for text extraction, and editable transcripts before analysis. |
| 🎬 **Video** | Extract keyframes, run OCR and QR scanning on each frame, and stop early when a suspicious link or QR code is detected. |
| 📄 **Files** | Static safety checks: magic-byte signatures versus file extensions, double extensions, Office macros, active-content tokens in PDFs (`/OpenAction`, `/JavaScript`, `/Launch`), and SHA-256 hashes. **No opening, execution, or uploading.** |
| 📞 **Phone Numbers** | Validate E.164 number structure (libphonenumber), suggest carriers based on prefixes, and flag 1900 prefixes. Reports only a **valid format**, never a guarantee of safety. |

Also includes: **combined ML + rule-based scoring**, a score breakdown, optional local history
with sensitive information redacted, a *Scam or Safe?* mini-game, a glossary of warning signs,
and a **Model Card**.

---

## 🚀 Getting Started

The app is static (HTML/CSS/JS). There are two ways to run it:

**1) Open directly** — double-click `web_app/index.html`.
Most features (text, phone numbers, file checks, rules, and ML) work immediately.

**2) Run a local web server (recommended for OCR and microphone access):**

```bash
cd web_app
python3 -m http.server 8080      # or: npx serve .
# Open http://localhost:8080
```

> **Why use a server?** OCR (Tesseract.js) and audio recording (getUserMedia / Web Speech API)
> require an `http(s)://` context and may not work reliably when opened via `file://`.
> For public deployment, simply publish the `web_app/` directory to **GitHub Pages**.

**Browsers:** The latest Chrome/Edge is recommended. Most features also work in Firefox/Safari;
speech-to-text availability depends on the browser's support for the Web Speech API.

**OCR note:** An Internet connection is required on first use to download language data
(a few MB) from a CDN. Worker libraries are bundled in `web_app/vendor/`
(available offline afterward).

---

## 🧠 Machine Learning Models (Trained and Reproducible)

The model is **actually trained** using scikit-learn — the reported metrics are not fabricated.
The complete pipeline is in `ml_training/` (see its separate README).

- **Algorithm:** TF-IDF (unigrams + bigrams, NFC normalization + lowercasing, bilingual)
  with two Logistic Regression heads: scam/safe detection and seven-class scenario classification.
- **Training:** scikit-learn → export weights to `web_app/data/model/model.js`.
- **Inference:** Runs entirely in JavaScript in the browser (`web_app/js/ml/`), with
  **a difference of less than 1e-6 from scikit-learn** (verified by `ml_training/parity.test.js`).
- **Base score:** `clamp(0.45·ML + 0.35·rules + 0.15·indicators + 0.05·context, 0..100)`.
- **Additional Transformer:** An XLM-R phishing/social-engineering model, exported to ONNX
  and quantized to INT8 (~279 MB), running directly in the browser with Transformers.js.
- **Guarded boost:** The Transformer does not replace the base score and can never lower it.
  Only when the base score is `>= 50` and the Transformer score is `>= 80/100` can the system
  add up to `+10` points to the final score.

**Performance (5-fold cross-validation):**

- Scam detection — Precision **0.85** · Recall **0.969** · F1 **0.905** · Accuracy **0.87**
- Scenario classification (7 classes) — Macro-F1 **0.579** · Accuracy **0.598**

These metrics apply to the base TF-IDF + Logistic Regression model.

**Transformer evaluation on the current dataset:**

- Vietnamese: Accuracy **71.71%** · Precision **92.65%** · Recall **62.38%** · F1 **74.56%**
- English: Accuracy **82.35%** · Precision **82.09%** · Recall **90.16%** · F1 **85.94%**

The Transformer produces both false positives and false negatives, so it is used as
an additional confirmation signal rather than a standalone classifier making the final decision.

The system prioritizes **recall**: missing a scam is considered more dangerous than a false alarm.
The data is **synthetic/anonymized** and contains no real OTPs or account numbers.

---

## 🏗️ Architecture

```text
web_app/
├── index.html              # Semantic SPA, skip link, scripts deferred in order
├── css/                    # tokens · base · components · views · responsive
├── js/
│   ├── app.js              # Orchestration: router, tabs, workflows, export
│   ├── i18n.js · state.js · ui.js
│   ├── ml/                 # vectorizer · model · ruleEngine · scoreFusion
│   ├── ai/                 # XLM-R Transformer inference via Transformers.js
│   ├── analyzers/          # text · phone · file · image · voice · video
│   ├── integrations/       # Phone/file adapters (Contest Strict, no API keys)
│   └── utils/              # sanitizer · extract · validators · hashing · redaction
├── data/                   # locales(vi/en) · rules(vi/en) · demoSamples · model/
├── vendor/                 # jsQR · libphonenumber · jszip · tesseract (offline)
└── assets/                 # logo · favicon
```

The **data layer** (`locales`, `rules`, `model`, `demoSamples`) consists of `.js` files
that assign data to `window.*`, allowing the app to run both via `file://` and through a server.

---

## 🔒 Security & Privacy

- User-provided content is never rendered with `innerHTML`; all text is rendered through
  `textContent` to prevent XSS. No `eval`.
- Files are read as **bytes**, without being opened, executed, or uploaded.
- Exported reports (TXT/JSON) **redact OTPs, account numbers, and phone numbers**.
- History is stored only when enabled, stays in `localStorage`, and can be cleared at any time.
- No inference APIs or API keys are used to classify content.
- First-time Transformer use requires an Internet connection to download Transformers.js
  and the XLM-R weights from Hugging Face. Once downloaded, inference runs in the browser.
- User content is not sent to Hugging Face for classification.
- Integration hooks for Twilio Lookup / VirusTotal are included in `js/integrations/`
  for transparency.

---

## ⚠️ Limitations

- Scams using new slang or lacking recognizable keywords may go undetected.
- OCR and speech recognition can make mistakes → review the extracted text before analysis.
- **“Low risk” does not mean completely safe.**
- File checks examine static indicators; they are not a substitute for antivirus software.

---

## 🗺️ Roadmap

- Reduce the Transformer's size or switch to a smaller model to shorten the initial download.
- Expand benchmarking with real-world data independent of the training set before increasing
  the Transformer's influence on the final score.
- Expand the rule set to cover emerging scam campaigns, with community contributions.
- Add hash and phone-reputation lookups via APIs (Demo+ mode, session-scoped keys).
- Improve scenario classification as more labeled real-world data becomes available.
- Add an installable, offline-capable PWA and direct sharing from messaging apps
  through Web Share Target.

---

## 🤖 AI-Assisted Development

The entire product was built with Claude (Anthropic), from specifications and system design
to bilingual rules, ML model training and export, the user interface, and testing.
Prompt logs are available in `prompts/`.

---

*ScamCall Shield helps identify warning signs; it does not definitively establish whether
content is safe or fraudulent. When in doubt: stop, do not share OTPs or passwords,
do not transfer money, and verify through official channels.*

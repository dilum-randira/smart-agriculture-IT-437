# Nai Miris Smart Agriculture Research

### Explainable IoT Microclimate System for Smart Irrigation and Nai Miris Yield Forecasting

An undergraduate research project exploring how **IoT field monitoring**, **machine-learning forecasting**, **irrigation optimisation**, and **explainable decision support** can support open-field Nai Miris (*Capsicum chinense*) cultivation in Sri Lanka.

**SLIIT · Research Project · 2026**

> **Development status:** The repository includes a shared FastAPI skeleton, a React + Vite frontend scaffold, and preserved earlier C4 demonstration files. Component research, live IoT integration and end-to-end field validation are **not yet complete**. Planned capabilities below are research objectives, not verified deployed features.

## Project overview

The proposed system connects four individual research components:

| Component | Research area | Planned responsibilities |
| --- | --- | --- |
| **C1 — IoT Data Acquisition & Quality** | Field sensing and trustworthy datasets | Collect timestamped field measurements, validate readings, handle missing or anomalous observations, and prepare quality-aware inputs. |
| **C2 — Predictive Intelligence** | Microclimate and fresh-yield prediction | Forecast soil moisture, air temperature and relative humidity over 24-hour, 3-day and 7-day horizons; investigate next-7-day fresh Nai Miris yield prediction. |
| **C3 — Irrigation Optimisation** | Water requirements and scheduling | Investigate crop water demand, water stress and multi-objective irrigation schedule recommendations using sensor observations and forecasts. |
| **C4 — Explainable Decision Support** | Market intelligence and harvest planning | Investigate price trends, harvest-date scenarios, trade-offs and explainability for farmer-facing decision support. |

### Proposed data flow

```text
IoT sensors and field records
             |
             v
     C1: Data acquisition
       and quality checks
             |
             v
  C2: Microclimate forecasts
     and fresh-yield estimates
             |
             v
 C3: Irrigation schedule options
             |
             v
 C4: Harvest/market decision support
             |
             v
    Farmer-facing web dashboard
```

This is a **conceptual flow**, not a claim that the complete pipeline is deployed. C3 also uses C1 observations, while C4 may combine outputs from C1, C2 and C3 with independently sourced market information.

## Technology stack

| Area | Current shared setup / planned tools |
| --- | --- |
| Frontend | **React + Vite + JavaScript (JSX) + Tailwind CSS** |
| Backend | **Python + FastAPI** |
| IoT integration | ESP32-based sensing and MQTT (**planned**, owned by C1) |
| Machine learning | Python ecosystem, with model choices evaluated by each component |
| Persistence | Shared database design **not finalised** |
| Collaboration | GitHub; automated frontend build and backend syntax checks |

**JavaScript / JSX is the agreed frontend language.** TypeScript is not required.

## Repository structure

The following reflects the **tracked shared scaffold** currently on `main`:

```text
smart-agriculture-IT-437/
├── backend/
│   ├── app/
│   │   └── main.py            # Shared FastAPI application and health endpoint
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── README.md      # Page ownership guidance
│   │   ├── components/
│   │   └── Navbar.jsx      # Shared responsive navigation
│   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.html         # React/Vite entry
│   │   └── styles.css
│   ├── index.html             # Preserved C4 HTML demo (legacy entry)
│   ├── app.js                 # Preserved C4 demo script
│   ├── style.css              # Preserved C4 demo styles
│   ├── vite.config.js
│   ├── package.json
│   └── README.md
│
├── firmware/
│   └── README.md
├── docs/
│   └── README.md
├── .github/workflows/
│   └── application-scaffold.yml
└── README.md
```

### Component folder ownership

As members start development, they can create their own component folders using these **suggested locations**:

| Area | Member-owned folders (create when needed) |
| --- | --- |
| Backend component modules | `backend/app/c1/`, `c2/`, `c3/`, `c4/` |
| Frontend component pages | `frontend/src/pages/c1/`, `c2/`, `c3/`, `c4/` |
| Device firmware | `firmware/`, with layout chosen by the IoT member |
| Shared documentation | `docs/`, when team decisions are agreed |

**Important:** Component directories are intentionally **not populated with placeholder source files**. Their owners choose the appropriate files and internal structure. Git does not track empty directories, so these paths appear on GitHub once real files are committed.

There is currently **no shared `experiments/` folder**. Members should agree on a research-experiment location before moving existing work.

## Getting started

### Prerequisites

- Git
- Node.js and npm (the current GitHub Actions job uses Node.js 22)
- Python 3.11 or another version compatible with the backend dependencies

Clone the repository:

```bash
git clone https://github.com/dilum-randira/smart-agriculture-IT-437.git
cd smart-agriculture-IT-437
```

### Start the frontend

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Vite usually serves the React application at **http://localhost:5173**.

To make a production bundle:

```bash
npm run build
```

The build output is written to `frontend/dist/`.

### Start the backend

In a separate terminal, from the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- macOS / Linux: `source .venv/bin/activate`

Then install the dependencies and start FastAPI:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Available shared endpoints:

- **Health check:** http://localhost:8000/health
- **Interactive API docs:** http://localhost:8000/docs

**Note:** Component-specific prediction, monitoring, irrigation and decision APIs have **not** been registered in the shared backend yet. They must be implemented and integrated by the respective members.

### Existing C4 HTML dashboard

The earlier C4 HTML/CSS/JS demonstration has been preserved as:

- `frontend/index.html`
- `frontend/app.js`
- `frontend/style.css`

The **React app runs from `frontend/src/index.html`**, because `frontend/vite.config.js` sets `src/` as the Vite root. The C4 demonstration is **not automatically included** in React and has not yet been migrated. Keep those existing files intact until the C4 owner reviews the migration.

## Team collaboration guidelines

1. **Own your component.** Members write their own component pages, backend routes, algorithms and tests; do not populate another member's folder without agreement.
2. **Keep shared files coordinated.** Changes to `backend/app/main.py`, `frontend/src/App.jsx`, navigation, common configuration and API interfaces should be reviewed as integration work.
3. **Use focused branches and pull requests.** Develop features on a branch, review changes, and coordinate integration through `dev` before promoting approved work to `main`. Existing branch history must be preserved.
4. **Write meaningful commits.** Each commit should describe real functionality, documentation, a reproducible experiment or a validated fix.
5. **Protect research integrity.** Label synthetic and practice data clearly, keep original source and unit information, avoid data leakage, and never report unverified model accuracy as a field result.
6. **Do not commit sensitive data.** Keep secrets, credentials, private farmer records, restricted datasets and large generated model artifacts out of Git.

## Research and integration notes

- C1 sensor data and on-field crop records are dependencies for fully validating downstream work.
- C2 forecast models are **planned research candidates**, not trained production models included in this shared scaffold.
- The team still needs to agree data contracts covering **plot IDs, timestamps, calibrated measurement units, growth stage, prediction horizon, data quality and model versions**.
- Dataset sources, measurement coverage, harvest labels and market information should be documented before any claims about agricultural prediction performance or economic outcomes.

## Current progress

| Item | Status |
| --- | --- |
| Shared FastAPI application and `/health` route | **Present** |
| React + Vite + JSX + Tailwind scaffold, top navigation and working routes | **Present** |
| Earlier C4 HTML demonstration | **Preserved**, not migrated |
| C1–C4 page modules and backend routes | **Member-owned; pending integration** |
| Live field-device data acquisition | **Not verified here** |
| Integrated ML predictions and full research evaluation | **Not verified here** |

## Team

- Bandara W.V.L.
- Kumara H.P.D.D.R.H
- Gayantha W.M.K
- Kumari U.S.S.S

See [frontend/README.md](frontend/README.md), [backend/README.md](backend/README.md), and [docs/README.md](docs/README.md) for focused setup and ownership details.

---

**This repository documents work in progress.** Planned research outcomes, synthetic demonstrations and experimentally verified results must remain clearly distinguished.

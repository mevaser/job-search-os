# Job Search OS - Project Blueprint (V2)
**Product Specification, Architecture, and Work Plan**
A personal Full Stack system for discovering, scoring, and managing Data / AI / Python jobs with a Web + PWA mobile experience.

**Version:** 01/06/2026 (Optimized for Agentic IDE / Anti-Gravity environment)
**Prepared for:** Mevaser Zehoray

## Executive Summary
The system will be built with a structured FastAPI Backend, SQLAlchemy Database, responsive React + TypeScript frontend, mobile PWA, future Telegram alerts, and a transparent, documented classification and scoring engine. The focus is not just on finding jobs, but on managing the entire job search process in a measurable, convenient, and iterative manner.

## 3. Core Product Principles
* **Backend First:** The core will be a structured API. A single source of truth.
* **Explainability:** Every fit score must include an explanation, matched keywords, penalties, and a detailed score breakdown.
* **Mobile First Review:** Responsive PWA for quick mobile reviews and status updates.
* **Rule-Based before LLM:** Build a deterministic engine first. LLMs will be integrated only in advanced stages.

## 5. End-to-End Architecture
Job Sources -> Scraping Workers (Mock CSV at first) -> Raw Storage -> Normalize & Dedup -> Classification (Role/Experience) -> Scoring Engine -> FastAPI Backend -> SQLite (in-memory for testing) -> React Web App / PWA

## 6. Tech Stack (Anti-Gravity Optimized)
* **Backend:** FastAPI + SQLAlchemy.
* **Database:** SQLite (MVP). **CRITICAL:** When running automated agent tests, configure SQLAlchemy to use `sqlite:///:memory:` to prevent database locking issues.
* **Frontend:** React + Vite + Tailwind CSS. (Using Tailwind ensures agents generate clean, consistent UI without breaking CSS files).
* **Scraping:** Initial development will use Mock Data (CSV/JSON) to prevent AI agents from getting blocked by LinkedIn during testing loops.

## 8. Data Model
* **jobs:** id, source, title, company, location, url, description, date_posted.
* **job_analysis:** job_id, role_family, seniority_level, experience_requirement, fit_score, decision (KEEP/REVIEW/REJECT), score_breakdown, evidence.
* **applications:** job_id, status, applied_via, cv_version.

## 16. Anti-Gravity Work Plan (Micro-Missions)
| Mission | Scope | Acceptance Criteria (DoD) |
| :--- | :--- | :--- |
| **1. Skeleton** | Create directory structure: `backend`, `frontend`, `config`, `docs`, `tests`. Create a `README.md` and an empty `main.py`. | Project opens, folders exist, no broken code. |
| **2. Backend Base** | FastAPI app, health check endpoint, config loader. | `/health` endpoint returns 200 OK. Swagger UI is accessible. |
| **3. Database Models** | SQLAlchemy models for the tables detailed in section 8. | Database is created, migrations run without errors, in-memory tests pass. |
| **4. Pipeline (Mock)** | Normalization, classification (Experience/Role), and scoring based on a predefined mock CSV/JSON file. | Jobs receive a `fit_score` and `decision` without making external network calls. |
| **5. Jobs API** | GET/PATCH endpoints for jobs from the database. | Endpoints can fetch and update job statuses via Swagger. |
| **6. Frontend Base** | Setup a job board with React and Tailwind CSS connected to the API. | The React app loads locally and displays mock jobs. |
| **7. Live Scraper** | Connect JobSpy to the pipeline (outside of automated test loops). | Manual scan fetches real jobs and saves them to the DB. |

## 19. AI Agent Development Rules
1. **Context Isolation:** Every Mission must be executed in a separate, new agent session.
2. **Strict TDD (Test-Driven Development):** After writing functional code, the agent MUST write a test script, run it, and debug itself until the test passes completely.
3. **Scope Focus:** Do not deviate from the current mission scope. Do not implement UI features when working on the backend, and do not add complex LLM features yet.
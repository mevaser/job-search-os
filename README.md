# Job Search OS

A personal Full Stack system for discovering, scoring, and managing Data / AI / Python jobs with a Web + PWA mobile experience.

## Executive Summary
Job Search OS is a structured platform built with a FastAPI Backend, SQLAlchemy Database, responsive React + TypeScript frontend, mobile PWA, and a transparent, documented classification and scoring engine. The system manages the entire job search process in a measurable, convenient, and iterative manner, rather than just finding jobs.

## Core Product Principles
* **Backend First:** The core is a structured API, acting as a single source of truth.
* **Explainability:** Every fit score includes an explanation, matched keywords, penalties, and a detailed score breakdown.
* **Mobile First Review:** Responsive PWA for quick mobile reviews and status updates.
* **Rule-Based before LLM:** A deterministic engine serves as the foundation, with LLMs integrated only in advanced stages.

## End-to-End Architecture
Job Sources -> Scraping Workers -> Raw Storage -> Normalize & Dedup -> Classification (Role/Experience) -> Scoring Engine -> FastAPI Backend -> SQLite -> React Web App / PWA

## Tech Stack
* **Backend:** FastAPI + SQLAlchemy
* **Database:** SQLite
* **Frontend:** React + Vite + Tailwind CSS

## Directory Structure
* `/backend` - FastAPI application and API routes
* `/frontend` - React + Vite frontend application
* `/config` - System configuration files
* `/docs` - Project documentation
* `/tests` - Automated tests

## Data Model
* **jobs:** id, source, title, company, location, url, description, date_posted.
* **job_analysis:** job_id, role_family, seniority_level, experience_requirement, fit_score, decision, score_breakdown, evidence.
* **applications:** job_id, status, applied_via, cv_version.

# DataCleaner AI

An intelligent, AI-powered data cleaning and preprocessing web application designed for data analysts and engineers. It empowers users to clean, transform, and analyze datasets using natural language commands in Arabic or English, eliminating the need for manual coding.

---

## Key Features

### Natural Language Cleaning
Users input plain text commands (e.g., "Remove duplicate rows", "Fill missing salaries with the average"), and the AI instantly generates and executes the corresponding Python code against the dataset.

### Multilingual Support
The AI engine accepts commands in both Arabic and English and was specifically trained via prompt engineering to handle Arabic-language datasets, including detecting Arabic Eastern numerals (١٢٣) and mixed-language text within the same column.

### Bring Your Own Key Gateway (BYOK)
A secure entry screen validates the user's personal Gemini API key against the live API before granting access. Invalid keys, revoked keys, and zero-quota keys are detected immediately with clear Arabic-language error messages. This ensures each user operates within their own free tier quota and the service incurs no AI cost from the host.

### AI Model Fallback Chain
The backend does not depend on a single AI model. If one model is unavailable or over quota, the system silently falls back to the next in a prioritized list including gemini-2.0-flash, gemini-2.0-flash-lite, and gemini-2.5-flash. This guarantees maximum uptime.

### Metadata-Only Prompt Architecture
The AI is never shown the actual data. The prompt sent to Gemini contains only: column names, data types, a 3-row sample, and up to 15 unique values per text column for mapping purposes. This design ensures sensitive data rows are never transmitted to any external API.

### Smart Data Profiling (Smart Scan)
Automatically scans uploaded datasets on upload to generate a full health report. The scanner detects the following categories of issues:

- Duplicate rows (exact duplicates)
- Missing values per column with severity rating
- Mixed date formats within a single column (e.g., "12/03/2023" vs "2023-03-12")
- Arabic Eastern numerals (١٢٣) within numeric or text columns
- Mixed Arabic and English text within the same column
- Leading, trailing, or double whitespace within text cells
- Inconsistent letter casing (e.g., "Cairo" vs "cairo" vs "CAIRO")
- Fuzzy / near-duplicate text values using Levenshtein distance similarity (e.g., "Microsoft" vs "Micosoft"), with temporal columns such as date, timestamp deliberately excluded from fuzzy matching to avoid false positives

Each detected issue includes a severity level (high, medium, low), a descriptive message in Arabic, a suggested fix, and a one-click "Fix with AI" action button that auto-populates the chat.

### Interactive Chat Interface
A continuous conversational interface allows users to apply sequential data transformations. Each command is tracked in an Audit Log that records what was changed, by what code, and in which order.

### Before / After Live Preview
An interactive sortable and searchable data grid allows users to compare the dataset before and after any cleaning command, with tab-based switching between the two states.

### Advanced Export System
- CSV: cleaned data in plain comma-separated format
- Excel (.xlsx): cleaned data with Excel formatting preserved
- Python Script (.py): the full cleaning code used across the session, ready to run independently
- PDF Audit Report: a formal PDF document listing every transformation applied during the session
- Jupyter Notebook (.ipynb): a structured notebook with all cleaning steps as executable cells, for integration into an existing data science workflow

### Case-Sensitive Column Handling
The AI is explicitly instructed via prompt constraints to use column names exactly as they appear in the dataset, including case. This prevents CodeErrorExceptions from column-not-found mismatches that commonly occur with LLM-generated Pandas code.

---

## Data Privacy and Security

DataCleaner AI implements a Metadata-Only Architecture to ensure that sensitive data is never exposed to external AI providers.

- Zero Data Leakage: Raw dataset rows and actual cell values are never transmitted to the AI model.
- Metadata Exchange Only: The system transmits only structural metadata (column names, data types, a 3-row sample, up to 15 unique values) alongside the user's natural language request.
- In-Memory Execution: The AI returns Python code only. That code is executed locally on the server's RAM using Pandas, against the data stored within the session.
- Stateless Sessions: No external database stores user data. Sessions exist only in server memory during the active request. Data is not persisted after the session ends.
- Key Not Stored: The user's personal Gemini API key is never saved to disk, database, or logs. It exists only in memory for the duration of the session.

---

## Architecture Overview

The application is split into two fully independent deployments:

- Frontend hosted on Vercel (auto-deployed from GitHub)
- Backend hosted on Hugging Face Spaces (FastAPI with Python runtime)

This separation allows the frontend to be updated independently without affecting the backend and vice versa.

---

## Technology Stack

### Frontend

- HTML5 and CSS3: Custom-built, fully responsive UI using Vanilla CSS only. No CSS frameworks such as Bootstrap or Tailwind were used, demonstrating native styling capability. Includes dark mode, glassmorphism card effects, and smooth transitions.
- Vanilla JavaScript (app.js): Manages all application state, drag-and-drop file uploads, API key gateway flow, asynchronous fetch requests to the backend, real-time chat updates, and Before/After grid rendering.

### Backend

- FastAPI: High-performance Python API framework. Handles file upload, session management, the /verify-key endpoint for API key validation, the /clean endpoint for AI-powered transformation, and all export endpoints.
- Pandas: Core data manipulation engine. Loads CSV and Excel files, executes AI-generated cleaning code within a sandboxed exec() environment, and manages dataframe state per session.
- NumPy: Used internally by the Scanner module for statistical outlier detection and numeric analysis.
- Google GenAI SDK (google-genai): Official Google library for interfacing with the Gemini API. Used in both the test_api_key() validation function and the get_cleaning_code() AI generation function.
- python-dotenv: Manages environment variable loading for the fallback API key in development mode.
- FPDF: Generates structured PDF audit reports from the session's audit log.
- Nbformat: Generates Jupyter Notebook files (.ipynb) from the session's cleaning code history.
- difflib / Levenshtein-based comparison: Used by the Scanner module to detect fuzzy near-duplicate string values within text columns.

---

## Module Breakdown

| File | Purpose |
|---|---|
| backend/main.py | FastAPI application entry point. Defines all API endpoints and manages in-memory session state. |
| backend/ai_engine.py | Builds the metadata-only prompt, calls Gemini with multi-model fallback, validates API keys via test_api_key(), and extracts Python code from AI responses. |
| backend/scanner.py | Performs the full dataset health scan. Detects 8 categories of data quality issues and generates the structured issue report with severity ratings and auto-fix prompts. |
| backend/cleaner.py | Provides a sandboxed Python code execution environment (exec-based) for safely running AI-generated Pandas code. |
| backend/exporter.py | Handles all export formats: CSV, Excel, Python script, PDF report, and Jupyter Notebook. |
| frontend/index.html | Structure of the full application UI including the API Key Gateway welcome screen and all workspace sections. |
| frontend/app.js | Client-side logic for the API gateway, file upload, chat, preview grid, sorting, search, and export flows. |
| frontend/style.css | Complete custom CSS design system including variables, dark theme, card styles, chat bubbles, and responsive grid layout. |

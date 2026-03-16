# DataCleaner AI

An intelligent, AI-powered data cleaning and preprocessing web application designed for data analysts and engineers. It empowers users to clean, transform, and analyze datasets using natural language commands, eliminating the need for manual coding.

## Key Features

* Natural Language Cleaning: Users can input plain text commands (e.g., "Remove duplicate rows", "Fill missing salaries with the average"), and the AI instantly generates and executes the corresponding Python code.
* Smart Data Profiling (Smart Scan): Automatically scans uploaded datasets to identify missing values, duplicate records, and data anomalies, generating a comprehensive health score and summary.
* Interactive Chat Interface: A continuous conversational interface allowing users to apply sequential data transformations and see real-time updates.
* Before/After Live Preview: An interactive data grid that provides an immediate visual comparison of the dataset before and after the execution of any cleaning command.
* Advanced Export System: Users can download their processed data in CSV or Excel formats. Additionally, the app exports the exact Python script used for cleaning, a detailed PDF Audit Report, and an interactive Jupyter Notebook (.ipynb).
* Bring Your Own Key (BYOK): A secure entrance gateway that requires users to provide their own Gemini API key, ensuring personalized rate limits and quota management.

## Data Privacy & Security (Metadata-Only Architecture)

DataCleaner AI is built with enterprise-grade privacy at its core. It operates on a "Metadata-Only" architecture, guaranteeing that sensitive information is never exposed to external AI models.

* Zero Data Leakage: Raw dataset rows, personal information, and actual file contents are NEVER sent to the AI provider.
* Metadata Exchange: The system only transmits structural metadata (column names, data types) alongside the user's natural language request to the AI model. 
* Localized In-Memory Execution: The AI model returns Python code, which is then safely executed directly on the server's RAM using Pandas. 
* Stateless Environment: The application does not use external databases to store user data. Once the session ends, all uploaded files and in-memory data structures are completely purged.

## Technology Stack

### Frontend
* HTML5 & CSS3: A custom-built, responsive user interface featuring modern design principles. Built strictly with Vanilla CSS to demonstrate core styling proficiency without relying on frameworks like Bootstrap or Tailwind.
* Vanilla JavaScript: Manages complex state transitions, drag-and-drop file uploads, asynchronous API communication, and dynamic DOM updates.

### Backend
* FastAPI: A modern, high-performance web framework for building APIs with Python, handling file uploads, and routing API gateway requests.
* Pandas: The core analytical engine executing the programmatic data transformations and managing dataframe states.
* Google GenAI SDK (Gemini): The designated Large Language Model integration used exclusively to translate human instructions into precise Pandas code.
* FPDF & Nbformat: Specialized Python libraries utilized to compile and generate robust PDF audit trails and structured Jupyter Notebook files for data science workflows.

import os
import uuid
import json
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import shutil

from scanner import scan_dataframe
from ai_engine import get_cleaning_code
from cleaner import execute_cleaning_code
from exporter import export_csv, export_excel, export_python_code, export_pdf_report, export_jupyter_notebook

load_dotenv()

app = FastAPI(title="DataCleaner AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (for local use)
sessions: dict = {}

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_file(filepath: str) -> pd.DataFrame:
    """Load CSV or Excel file into a DataFrame."""
    if filepath.endswith(".csv"):
        try:
            return pd.read_csv(filepath, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(filepath, encoding="latin-1")
    elif filepath.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    else:
        raise ValueError("Unsupported file type. Use CSV or Excel.")


@app.get("/")
async def root():
    return {"message": "DataCleaner AI is running! 🚀"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV or Excel file and return a scan report."""
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported.")

    session_id = str(uuid.uuid4())
    filename = f"{session_id}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        df = load_file(filepath)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    scan_report = scan_dataframe(df)

    sessions[session_id] = {
        "filepath": filepath,
        "filename": file.filename,
        "df_original": df,
        "df_current": df.copy(),
        "scan_report": scan_report,
        "audit_log": [],
        "cleaning_code": "",
        "chat_history": [],
        "history": []
    }

    return {
        "session_id": session_id,
        "filename": file.filename,
        "scan_report": scan_report,
        "preview": {
            "columns": list(df.columns),
            "data": df.head(10).fillna("").to_dict(orient="records")
        }
    }


@app.post("/clean")
async def clean_data(
    session_id: str = Form(...),
    user_request: str = Form(...)
):
    """Process a natural language cleaning request."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a file first.")

    session = sessions[session_id]
    df = session["df_current"]

    # Get cleaning code from Gemini (sends only metadata, NOT real data)
    ai_result = get_cleaning_code(df, user_request)

    if not ai_result["success"]:
        raise HTTPException(status_code=500, detail=f"AI Error: {ai_result.get('error', 'Unknown error')}")

    code = ai_result["code"]

    # Save state to history before executing
    session["history"].append({
        "df_current": df.copy(),
        "audit_log": list(session["audit_log"]),
        "cleaning_code": session["cleaning_code"],
        "chat_history": list(session["chat_history"])
    })

    # Execute the code safely
    exec_result = execute_cleaning_code(df, code)

    if not exec_result["success"]:
        raise HTTPException(status_code=400, detail=f"Code execution error: {exec_result.get('error', 'Unknown')}")

    df_cleaned = exec_result["df_cleaned"]

    # Update session
    session["df_current"] = df_cleaned
    session["cleaning_code"] += f"\n# --- طلب: {user_request} ---\n{code}\n"
    session["audit_log"].extend(exec_result["audit_log"])
    session["chat_history"].append({
        "role": "user",
        "content": user_request
    })
    session["chat_history"].append({
        "role": "assistant",
        "content": f"✅ تم التنفيذ! {'. '.join([e['detail'] for e in exec_result['audit_log']])}"
    })

    # Re-run scan on cleaned data so the report stays accurate
    fresh_scan = scan_dataframe(df_cleaned)
    session["scan_report"] = fresh_scan

    return {
        "success": True,
        "code_used": code,
        "audit_log": exec_result["audit_log"],
        "rows_before": exec_result["rows_before"],
        "rows_after": exec_result["rows_after"],
        "scan_report": fresh_scan,
        "preview_before": {
            "columns": list(df.columns),
            "data": df.head(10).fillna("").to_dict(orient="records")
        },
        "preview_after": {
            "columns": list(df_cleaned.columns),
            "data": df_cleaned.head(10).fillna("").to_dict(orient="records")
        },
        "chat_history": session["chat_history"],
        "can_undo": len(session["history"]) > 0
    }

@app.post("/undo")
async def undo_last_action(session_id: str = Form(...)):
    """Revert the last cleaning action."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    session = sessions[session_id]
    if not session.get("history"):
        raise HTTPException(status_code=400, detail="لا يوجد عمليات سابقة للتراجع عنها.")
    
    last_state = session["history"].pop()
    
    session["df_current"] = last_state["df_current"]
    session["audit_log"] = last_state["audit_log"]
    session["cleaning_code"] = last_state["cleaning_code"]
    session["chat_history"] = last_state["chat_history"]
    
    df = session["df_current"]
    
    return {
        "success": True,
        "message": "تم التراجع عن الخطوة الأخيرة.",
        "audit_log": session["audit_log"],
        "rows_after": len(df),
        "preview_after": {
            "columns": list(df.columns),
            "data": df.head(10).fillna("").to_dict(orient="records")
        },
        "chat_history": session["chat_history"],
        "can_undo": len(session["history"]) > 0
    }



@app.get("/export/{session_id}/{export_type}")
async def export_data(session_id: str, export_type: str):
    """Export cleaned data as CSV, Excel, Python script, or PDF report."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    session = sessions[session_id]
    df = session["df_current"]
    base_name = session["filename"].rsplit(".", 1)[0]
    out_base = os.path.join(OUTPUT_DIR, f"{session_id}_{base_name}")

    if export_type == "csv":
        path = export_csv(df, f"{out_base}_cleaned.csv")
        return FileResponse(path, filename=f"{base_name}_cleaned.csv", media_type="text/csv")

    elif export_type == "excel":
        path = export_excel(df, f"{out_base}_cleaned.xlsx")
        return FileResponse(path, filename=f"{base_name}_cleaned.xlsx",
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif export_type == "python":
        path = export_python_code(
            session["cleaning_code"],
            session["audit_log"],
            f"{out_base}_cleaning_script.py"
        )
        return FileResponse(path, filename=f"{base_name}_cleaning_script.py", media_type="text/plain")

    elif export_type == "pdf":
        path = export_pdf_report(
            session["audit_log"],
            session["scan_report"],
            len(session["df_original"]),
            len(df),
            f"{out_base}_report.pdf"
        )
        return FileResponse(path, filename=f"{base_name}_report.pdf", media_type="application/pdf")

    elif export_type == "ipynb":
        path = export_jupyter_notebook(
            session["cleaning_code"],
            session["audit_log"],
            f"{out_base}_notebook.ipynb"
        )
        return FileResponse(path, filename=f"{base_name}_notebook.ipynb", media_type="application/x-ipynb+json")

    else:
        raise HTTPException(status_code=400, detail="Invalid export type. Use: csv, excel, python, pdf, ipynb")


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = sessions[session_id]
    df = session["df_current"]
    return {
        "filename": session["filename"],
        "rows": len(df),
        "columns": list(df.columns),
        "chat_history": session["chat_history"],
        "audit_log": session["audit_log"],
        "preview": {
            "columns": list(df.columns),
            "data": df.head(10).fillna("").to_dict(orient="records")
        }
    }


# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

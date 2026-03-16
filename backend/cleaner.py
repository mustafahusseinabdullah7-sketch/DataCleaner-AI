import pandas as pd
import numpy as np
import traceback
import io
import sys
from copy import deepcopy


def execute_cleaning_code(df_original: pd.DataFrame, code: str) -> dict:
    """
    Safely execute AI-generated cleaning code on a copy of the dataframe.
    Returns the cleaned dataframe and an audit log of changes.
    """
    df_before = df_original.copy()
    df = df_original.copy()

    audit_log = []

    # Capture stdout from the code execution
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        # Execute the code in a restricted namespace
        namespace = {
            "df": df,
            "pd": pd,
            "np": np,
        }
        exec(code, namespace)
        df_after = namespace["df"]

        # Safety check: if df is unchanged, look for any other DataFrame in namespace
        # that the AI might have accidentally written results to (e.g., df_temp, df_clean)
        if df_after.equals(df_before):
            for var_name, var_val in namespace.items():
                if (
                    var_name not in ("df", "pd", "np", "__builtins__")
                    and isinstance(var_val, pd.DataFrame)
                    and not var_val.equals(df_before)
                ):
                    df_after = var_val
                    break  # Use the first changed DataFrame we find

        sys.stdout = old_stdout

        # Generate audit log by comparing before/after
        audit_log = _generate_audit_log(df_before, df_after)

        return {
            "success": True,
            "df_cleaned": df_after,
            "audit_log": audit_log,
            "rows_before": len(df_before),
            "rows_after": len(df_after),
            "cols_before": len(df_before.columns),
            "cols_after": len(df_after.columns),
        }

    except Exception as e:
        sys.stdout = old_stdout
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "df_cleaned": df_before,
            "audit_log": [],
        }


def _generate_audit_log(df_before: pd.DataFrame, df_after: pd.DataFrame) -> list:
    """Compare two dataframes and produce a human-readable audit log."""
    log = []

    # Row count change
    row_diff = len(df_before) - len(df_after)
    if row_diff > 0:
        log.append({
            "action": "حذف صفوف",
            "detail": f"تم حذف {row_diff} صف",
            "impact": f"{len(df_before)} صف → {len(df_after)} صف"
        })
    elif row_diff < 0:
        log.append({
            "action": "إضافة صفوف",
            "detail": f"تم إضافة {abs(row_diff)} صف",
            "impact": f"{len(df_before)} صف → {len(df_after)} صف"
        })

    # Column changes
    added_cols = set(df_after.columns) - set(df_before.columns)
    removed_cols = set(df_before.columns) - set(df_after.columns)

    for col in added_cols:
        log.append({"action": "إضافة عمود", "detail": f"تم إضافة عمود: '{col}'", "impact": ""})
    for col in removed_cols:
        log.append({"action": "حذف عمود", "detail": f"تم حذف عمود: '{col}'", "impact": ""})

    # Check missing values changes per column
    common_cols = [c for c in df_before.columns if c in df_after.columns]
    for col in common_cols:
        missing_before = df_before[col].isnull().sum()
        # Align indices for fair comparison
        try:
            aligned_after = df_after[col].reset_index(drop=True)
            missing_after = aligned_after.isnull().sum()
            if missing_before > missing_after:
                filled = int(missing_before - missing_after)
                log.append({
                    "action": "ملء قيم مفقودة",
                    "detail": f"عمود '{col}': تم ملء {filled} قيمة مفقودة",
                    "impact": f"{missing_before} قيمة مفقودة → {missing_after}"
                })
        except Exception:
            pass

    if not log:
        log.append({"action": "لا توجد تغييرات", "detail": "لم يتم اكتشاف أي تغييرات هيكلية", "impact": ""})

    return log

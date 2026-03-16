import pandas as pd
import numpy as np
import re
from typing import Any

def scan_dataframe(df: pd.DataFrame) -> dict:
    """Perform a comprehensive scan of a dataframe and return a report."""
    report = {
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "issues": [],
        "columns_info": []
    }

    # Duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        report["issues"].append({
            "type": "duplicates",
            "severity": "high",
            "message": f"وجدنا {dup_count} صف مكرر",
            "count": dup_count,
            "suggestion": "حذف الصفوف المكررة الزائدة.",
            "action_prompt": "احذف جميع الصفوف المكررة من البيانات"
        })

    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "issues": []
        }

        # Missing values
        missing = int(df[col].isnull().sum())
        if missing > 0:
            pct = round(missing / len(df) * 100, 1)
            col_info["issues"].append({
                "type": "missing",
                "count": missing,
                "percentage": pct,
                "message": f"وجدنا {missing} قيمة مفقودة في عمود '{col}'"
            })
            report["issues"].append({
                "type": "missing_values",
                "severity": "medium" if pct < 30 else "high",
                "message": f"وجدنا {missing} قيمة مفقودة في عمود '{col}'",
                "column": col,
                "count": missing,
                "suggestion": "ملء القيم المفقودة أو حذف صفوفها.",
                "action_prompt": f"في عمود '{col}'، املأ القيم المفقودة بأكثر قيمة متكررة أو احذف صفوفها إذا كانت كثيرة" if df[col].dtype == object else f"في عمود '{col}'، املأ القيم المفقودة بالمتوسط الحسابي"
            })

        # Date format inconsistency (for object columns)
        if df[col].dtype == object:
            sample = df[col].dropna().head(100)
            date_formats_found = _detect_date_formats(sample)
            if len(date_formats_found) > 1:
                col_info["issues"].append({
                    "type": "mixed_date_formats",
                    "formats": date_formats_found,
                    "message": f"وجدنا {len(date_formats_found)} تنسيقات تاريخ مختلفة في عمود '{col}'"
                })
                report["issues"].append({
                    "type": "mixed_date_formats",
                    "severity": "medium",
                    "message": f"وجدنا {len(date_formats_found)} تنسيقات تاريخ مختلفة في عمود '{col}'",
                    "column": col,
                    "count": len(date_formats_found),
                    "suggestion": "توحيد تنسيق التاريخ (مثال: YYYY-MM-DD).",
                    "action_prompt": f"قم بتوحيد تنسيق جميع التواريخ في عمود '{col}' لتكون بصيغة YYYY-MM-DD"
                })

            # Arabic numbers
            arabic_count = int(sample.apply(lambda x: any('\u0660' <= c <= '\u0669' for c in str(x)) if pd.notna(x) else False).sum())
            if arabic_count > 0:
                col_info["issues"].append({
                    "type": "arabic_numbers",
                    "count": arabic_count,
                    "message": f"وجدنا {arabic_count} خلية تحتوي أرقام عربية في عمود '{col}'"
                })
                report["issues"].append({
                    "type": "arabic_numbers",
                    "severity": "low",
                    "message": f"وجدنا {arabic_count} خلية تحتوي أرقام عربية (١٢٣...) في عمود '{col}'",
                    "column": col,
                    "count": arabic_count,
                    "suggestion": "تحويل الأرقام العربية المشرقية إلى أرقام إنجليزية 표준 (123).",
                    "action_prompt": f"في عمود '{col}'، حول أي أرقام مكتوبة بالشكل المشرقي (١٢٣) إلى أرقام إنجليزية (123)"
                })

            # Mixed Language (Arabic + English)
            mixed_count = int(sample.apply(lambda x: bool(re.search(r'[a-zA-Z]', str(x)) and re.search(r'[\u0600-\u06FF]', str(x))) if pd.notna(x) else False).sum())
            if mixed_count > 0:
                col_info["issues"].append({
                    "type": "mixed_language",
                    "count": mixed_count,
                    "message": f"وجدنا {mixed_count} قيمة تدمج بين نصوص عربية وإنجليزية في عمود '{col}'"
                })
                report["issues"].append({
                    "type": "mixed_language",
                    "severity": "medium",
                    "message": f"وجدنا {mixed_count} خلية تحتوي مزيجاً من العربية والإنجليزية في عمود '{col}'",
                    "column": col,
                    "count": mixed_count,
                    "suggestion": "ترجمة الكلمات العربية إلى الإنجليزية لتوحيد لغة العمود.",
                    "action_prompt": f"في عمود '{col}'، قم بترجمة أي كلمات أو نصوص عربية إلى اللغة الإنجليزية لتوحيد البيانات"
                })

            # Whitespace issues
            whitespace_count = int(sample.apply(lambda x: bool(re.search(r'^\s+|\s+$|\s{2,}', str(x))) if pd.notna(x) else False).sum())
            if whitespace_count > 0:
                col_info["issues"].append({
                    "type": "whitespace_issues",
                    "count": whitespace_count,
                    "message": f"وجدنا {whitespace_count} مسافات زائدة في عمود '{col}'"
                })
                report["issues"].append({
                    "type": "whitespace_issues",
                    "severity": "medium",
                    "message": f"وجدنا {whitespace_count} خلية بها مسافات زائدة (في الأول/الآخر أو مزدوجة) في عمود '{col}'",
                    "column": col,
                    "count": whitespace_count,
                    "suggestion": "تنظيف النصوص من المسافات الزائدة.",
                    "action_prompt": f"في عمود '{col}'، احذف المسافات البيضاء الزائدة من بداية ونهاية الكلام، واستبدل المسافات المزدوجة بمسافة واحدة"
                })

            # Inconsistent Casing
            valid_col = df[col].dropna().astype(str)
            if valid_col.nunique() != valid_col.str.lower().nunique() and valid_col.str.contains(r'[a-zA-Z]', regex=True).any():
                col_info["issues"].append({
                    "type": "inconsistent_casing",
                    "message": f"تضارب متوقع في حالة الأحرف في عمود '{col}'"
                })
                report["issues"].append({
                    "type": "inconsistent_casing",
                    "severity": "medium",
                    "message": f"تضارب في حالة الأحرف (كلمات متطابقة كابيتال/سمول) في عمود '{col}'",
                    "column": col,
                    "count": 0,
                    "suggestion": "توحيد حالة الأحرف (Title Case أو Capitalize).",
                    "action_prompt": f"قم بتوحيد المسافات وحالة الأحرف في عمود '{col}' لتكون جميع الكلمات الإنجليزية Title Case"
                })

            # Fuzzy Duplicates — skip date/time columns by name convention
            _date_keywords = ("date", "time", "_at", "published", "created", "updated", "timestamp")
            _is_temporal_col = any(kw in col.lower() for kw in _date_keywords)
            if not _is_temporal_col:
                fuzzy_groups = _detect_fuzzy_duplicates(df[col].dropna().astype(str))
            else:
                fuzzy_groups = []
            if fuzzy_groups:
                examples = ", ".join([f"'{a}' / '{b}'" for a, b, _ in fuzzy_groups[:2]])
                col_info["issues"].append({
                    "type": "fuzzy_duplicates",
                    "count": len(fuzzy_groups),
                    "message": f"وجدنا {len(fuzzy_groups)} زوج من القيم المتشابهة في عمود '{col}' (مثال: {examples})"
                })
                report["issues"].append({
                    "type": "fuzzy_duplicates",
                    "severity": "medium",
                    "message": f"وجدنا {len(fuzzy_groups)} زوج قيم متشابهة جداً في عمود '{col}' يمكن توحيدها (مثال: {examples})",
                    "column": col,
                    "count": len(fuzzy_groups),
                    "suggestion": "توحيد القيم المتشابهة في إملاء واحد لإزالة الازدواجية.",
                    "action_prompt": f"في عمود '{col}'، وحّد القيم المتشابهة جداً في الكتابة (مثل: {examples}) تحت قيمة واحدة موحدة. استخدم الأكثر شيوعاً كقيمة مرجعية."
                })

            # Column Splitting Detection
            split_sep = _detect_splittable_column(df[col].dropna().astype(str))
            if split_sep:
                col_info["issues"].append({
                    "type": "splittable_column",
                    "separator": split_sep,
                    "message": f"يمكن تقسيم عمود '{col}' باستخدام 'الفاصل: {split_sep}'"
                })
                report["issues"].append({
                    "type": "splittable_column",
                    "severity": "low",
                    "message": f"عمود '{col}' يحتوي بيانات يمكن تقسيمها بالفاصل '{split_sep}' إلى عدة أعمدة",
                    "column": col,
                    "count": 0,
                    "suggestion": f"تقسيم عمود '{col}' بالفاصل '{split_sep}' للحصول على بيانات أكثر نظاماً.",
                    "action_prompt": f"في عمود '{col}'، قسّم العمود باستخدام الفاصل '{split_sep}' واحفظ كل جزء في عمود جديد مستقل"
                })


        # Numeric outliers + Domain Validation
        if pd.api.types.is_numeric_dtype(df[col]):
            outliers = _detect_outliers(df[col].dropna())
            if outliers > 0:
                col_info["issues"].append({
                    "type": "outliers",
                    "count": outliers,
                    "message": f"وجدنا {outliers} قيمة شاذة محتملة في عمود '{col}'"
                })
                report["issues"].append({
                    "type": "outliers",
                    "severity": "low",
                    "message": f"وجدنا {outliers} قيمة شاذة محتملة (خارج نطاق IQR) في عمود '{col}'",
                    "column": col,
                    "count": outliers,
                    "suggestion": "التعامل مع القيم الشاذة المتطرفة.",
                    "action_prompt": f"في عمود '{col}'، قم بمعالجة القيم الشاذة رقمياً إما بحذفها أو استبدالها بحدود معقولة"
                })

            # Domain Validation
            domain_issue = _check_domain_values(df[col].dropna(), col)
            if domain_issue:
                col_info["issues"].append({
                    "type": "domain_violation",
                    "count": domain_issue["count"],
                    "message": domain_issue["message"]
                })
                report["issues"].append({
                    "type": "domain_violation",
                    "severity": "high",
                    "message": domain_issue["message"],
                    "column": col,
                    "count": domain_issue["count"],
                    "suggestion": domain_issue["suggestion"],
                    "action_prompt": domain_issue["action_prompt"]
                })

        report["columns_info"].append(col_info)

    # Cross-Column Consistency Check (runs once on the full DataFrame)
    cross_issues = _check_cross_column_consistency(df)
    for issue in cross_issues:
        report["issues"].append(issue)

    report["total_issues"] = len(report["issues"])
    report["health_score"] = max(0, 100 - (report["total_issues"] * 8))

    return report


def _detect_date_formats(series: pd.Series) -> list:
    """Detect different date-like formats in a string series."""
    import re
    formats_found = set()
    patterns = {
        "DD/MM/YYYY": r'\b\d{1,2}/\d{1,2}/\d{4}\b',
        "MM-DD-YYYY": r'\b\d{1,2}-\d{1,2}-\d{4}\b',
        "YYYY-MM-DD": r'\b\d{4}-\d{1,2}-\d{1,2}\b',
        "DD.MM.YYYY": r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',
    }
    for val in series:
        val_str = str(val)
        for fmt_name, pattern in patterns.items():
            if re.search(pattern, val_str):
                formats_found.add(fmt_name)
    return list(formats_found)


def _detect_outliers(series: pd.Series) -> int:
    """Detect outliers using IQR method."""
    if len(series) < 10:
        return 0
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return int(((series < lower) | (series > upper)).sum())


def _detect_fuzzy_duplicates(series: pd.Series, threshold: int = 88) -> list:
    """
    Detect pairs of values that are very similar but not identical using rapidfuzz.
    Returns a list of tuples: (val_a, val_b, score).
    Only checks columns with a reasonable number of unique values to stay performant.
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return []

    unique_vals = series.unique().tolist()

    # For very large unique sets, take a random sample to stay performant
    # (still catches the most common fuzzy duplicate issues)
    import random
    MAX_UNIQUE = 80
    if len(unique_vals) < 2:
        return []
    if len(unique_vals) > MAX_UNIQUE:
        unique_vals = random.sample(unique_vals, MAX_UNIQUE)

    # Filter out very short strings (< 3 chars) to avoid false positives like 'A' vs 'B'
    unique_vals = [v for v in unique_vals if isinstance(v, str) and len(v.strip()) >= 3]

    fuzzy_pairs = []
    seen = set()

    for i in range(len(unique_vals)):
        for j in range(i + 1, len(unique_vals)):
            a = unique_vals[i]
            b = unique_vals[j]

            # Skip exact duplicates (case-insensitive) — caught by casing check
            if a.lower().strip() == b.lower().strip():
                continue

            # Number Filter: if both strings have numbers and those numbers differ,
            # they are semantically different (e.g. '5 to 10 years' vs '10 to 15 years')
            import re as _re
            nums_a = set(_re.findall(r'\d+', a))
            nums_b = set(_re.findall(r'\d+', b))
            if nums_a and nums_b and nums_a != nums_b:
                continue

            score = fuzz.token_sort_ratio(a, b)
            pair_key = (min(a, b), max(a, b))

            if score >= threshold and pair_key not in seen:
                seen.add(pair_key)
                fuzzy_pairs.append((a, b, score))

    # Sort by score descending, return top 10 to avoid noise
    fuzzy_pairs.sort(key=lambda x: -x[2])
    return fuzzy_pairs[:10]


def _check_domain_values(series: pd.Series, col_name: str) -> dict | None:
    """
    Check numeric columns for domain violations based on column name keywords.
    Returns an issue dict if violations are found, else None.
    """
    col_lower = col_name.lower()

    rules = []
    if any(k in col_lower for k in ("age", "عمر", "seniority")):
        rules.append(("age", 0, 120))
    if any(k in col_lower for k in ("percentage", "rate", "pct", "percent", "discount", "ratio")):
        rules.append(("percentage", 0, 100))
    if any(k in col_lower for k in ("salary", "price", "amount", "cost", "revenue", "راتب", "سعر")):
        rules.append(("positive", 0, None))
    if any(k in col_lower for k in ("year", "سنة", "yr")):
        rules.append(("year", 1900, 2100))

    for rule_type, lo, hi in rules:
        if lo is not None and hi is not None:
            bad_mask = (series < lo) | (series > hi)
        elif lo is not None:
            bad_mask = series < lo
        else:
            bad_mask = series > hi

        bad_count = int(bad_mask.sum())
        if bad_count > 0:
            label_map = {
                "age": f"قيم عمر خارج النطاق المعقول (0–120)",
                "percentage": f"قيم نسبة مئوية خارج (0–100)",
                "positive": f"قيم سالبة في عمود مفترض أن يكون موجباً دائماً",
                "year": f"قيم سنة خارج النطاق (1900–2100)"
            }
            msg = f"وجدنا {bad_count} قيمة مستحيلة في عمود '{col_name}': {label_map.get(rule_type, 'خارج النطاق المنطقي')}"
            return {
                "count": bad_count,
                "message": msg,
                "suggestion": f"تصحيح أو حذف القيم المستحيلة في عمود '{col_name}'.",
                "action_prompt": f"في عمود '{col_name}'، احذف أو صحح الصفوف التي تحتوي قيم مستحيلة منطقياً ({label_map.get(rule_type, 'خارج النطاق')})"
            }
    return None


def _detect_splittable_column(series: pd.Series, min_coverage: float = 0.70) -> str | None:
    """
    Detect if a text column consistently uses a separator that could split it into
    multiple structured columns. Returns the separator string if found, else None.
    """
    sample = series.head(50)
    if len(sample) == 0:
        return None

    # Skip if values are too short to be worth splitting (avg < 8 chars)
    if sample.str.len().mean() < 8:
        return None

    # Ordered by most specific/safest to most generic
    candidates = [" | ", " - ", " / ", "; ", ", ", ",", "-"]
    for sep in candidates:
        count = sample.apply(lambda x: sep in str(x)).sum()
        if count / len(sample) >= min_coverage:
            return sep

    return None


def _check_cross_column_consistency(df: pd.DataFrame) -> list:
    """
    Detect logical inconsistencies between pairs of related columns.
    Covers: date ordering (start/end, order/ship etc.) and numeric ranges (min/max).
    """
    import re as _re
    issues = []

    # ── Date ordering logic ──────────────────────────────────────────────────
    # Define a priority order for common date column name prefixes
    DATE_ORDER = ["order", "purchase", "created", "start", "invoice",
                  "ship", "dispatch", "delivery", "end", "close", "due"]

    date_keywords = ("date", "time", "_at", "published", "timestamp")
    date_cols = [c for c in df.columns if any(k in c.lower() for k in date_keywords)]

    # Convert candidate date columns to datetime for comparison
    parsed = {}
    for c in date_cols:
        try:
            parsed[c] = pd.to_datetime(df[c], errors="coerce")
        except Exception:
            pass

    # Compare each pair where we can infer ordering from the name prefix
    def _prefix_rank(col):
        col_l = col.lower()
        for i, kw in enumerate(DATE_ORDER):
            if kw in col_l:
                return i
        return len(DATE_ORDER)

    checked_pairs = set()
    sorted_date_cols = sorted(parsed.keys(), key=_prefix_rank)
    for i, col_a in enumerate(sorted_date_cols):
        for col_b in sorted_date_cols[i + 1:]:
            pair_key = (col_a, col_b)
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            series_a = parsed[col_a]
            series_b = parsed[col_b]
            both_valid = series_a.notna() & series_b.notna()
            if both_valid.sum() < 5:
                continue  # Not enough data to judge

            violations = int((series_a[both_valid] > series_b[both_valid]).sum())
            if violations > 0:
                pct = round(violations / both_valid.sum() * 100, 1)
                issues.append({
                    "type": "date_order_violation",
                    "severity": "high",
                    "message": f"وجدنا {violations} صف ({pct}%) حيث '{col_a}' أحدث من '{col_b}' وهذا غير منطقي",
                    "column": f"{col_a} + {col_b}",
                    "count": violations,
                    "suggestion": f"تحقق من صحة البيانات في عمودَي '{col_a}' و '{col_b}'.",
                    "action_prompt": f"احذف أو صحح الصفوف التي يكون فيها '{col_a}' أكبر من '{col_b}' لأن هذا يعني ترتيباً زمنياً مستحيلاً"
                })

    # ── Numeric min/max logic ────────────────────────────────────────────────
    for col_a in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col_a]):
            continue
        col_a_base = _re.sub(r'(min|minimum|from|lo|low)$', '', col_a.lower(), flags=_re.I).strip("_")
        for col_b in df.columns:
            if col_a == col_b or not pd.api.types.is_numeric_dtype(df[col_b]):
                continue
            col_b_base = _re.sub(r'(max|maximum|to|hi|high)$', '', col_b.lower(), flags=_re.I).strip("_")
            if col_a_base != col_b_base or col_a_base == col_a.lower():
                continue  # Not a recognizable min/max pair

            both = df[[col_a, col_b]].dropna()
            if len(both) < 5:
                continue
            violations = int((both[col_a] > both[col_b]).sum())
            if violations > 0:
                issues.append({
                    "type": "minmax_violation",
                    "severity": "high",
                    "message": f"وجدنا {violations} صف حيث '{col_a}' أكبر من '{col_b}' وهذا يعكس خطأً في البيانات",
                    "column": f"{col_a} + {col_b}",
                    "count": violations,
                    "suggestion": f"تصحيح الصفوف التي تكون فيها قيمة الحد الأدنى أكبر من الحد الأقصى.",
                    "action_prompt": f"في الصفوف التي يكون فيها '{col_a}' أكبر من '{col_b}'، أعد ترتيب القيمتين أو احذف الصف"
                })

    return issues

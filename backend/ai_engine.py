import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pandas as pd
import json

load_dotenv()

def build_prompt(df: pd.DataFrame, user_request: str) -> str:
    """Build a smart prompt that sends metadata, 3 rows, and categorical samples to Gemini."""
    columns = list(df.columns)
    sample_rows = df.head(3).to_dict(orient="records")
    dtypes = {col: str(df[col].dtype) for col in df.columns}
    
    # Extract unique values for string columns to help AI with translation/mapping
    unique_values = {}
    for col in df.columns:
        if df[col].dtype == 'object' or str(df[col].dtype) == 'string':
            vals = df[col].dropna().unique()
            if len(vals) > 0:
                unique_values[col] = list(vals)[:15] # Max 15 unique values per column

    prompt = f"""
أنت خبير في تنظيف البيانات باستخدام Python وPandas.

المعلومات المتاحة عن الملف:
- أسماء الأعمدة: {json.dumps(columns, ensure_ascii=False)}
- أنواع البيانات: {json.dumps(dtypes, ensure_ascii=False)}
- عينة من أول 3 صفوف: {json.dumps(sample_rows, ensure_ascii=False, default=str)}
- قيم فريدة من الأعمدة النصية (للمساعدة في الترجمة والتوحيد): {json.dumps(unique_values, ensure_ascii=False, default=str)}

طلب المستخدم:
"{user_request}"

المطلوب منك:
1. اكتب كود Python يستخدم Pandas فقط لتنفيذ طلب المستخدم.
2. الكود يفترض أن DataFrame موجود بالاسم `df`.
3. النتيجة النهائية يجب أن تكون في متغير اسمه `df` أيضاً.
4. أضف تعليقات بالعربية على كل خطوة مهمة.
5. لا تستخدم أي مكتبات خارجية غير Pandas وNumPy والمكتبات القياسية.
6. أرجع الكود فقط بدون أي شرح خارجه، ملفوفاً في ```python ... ```
7. إذا طُلب منك ترجمة أو توحيد نصوص، استخدم "القيم الفريدة" المرفقة لإنشاء قاموس استبدال (map / replace) دقيق يشمل كل الحالات.
8. ⚠️ مهم جداً: استخدم أسماء الأعمدة كما هي تماماً بنفس حالة الأحرف (Case-Sensitive). مثلاً إذا الاسم `Company_Name` لا تكتب `company_name` أو `COMPANY_NAME`. الأعمدة المتاحة هي: {columns}

مثال على الشكل المطلوب:
```python
# حذف الصفوف المكررة
df = df.drop_duplicates()
```
"""
    return prompt


def test_api_key(api_key: str) -> dict:
    """Verify if the provided API key is valid and has quota."""
    if not api_key or not api_key.strip():
        return {"valid": False, "error": "المفتاح فارغ"}
        
    try:
        current_client = genai.Client(api_key=api_key)
        # Try a very cheap request to verify quota
        models_to_try = [
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-2.5-flash",
            "models/gemini-flash-latest",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]
        
        last_error = ""
        for model in models_to_try:
            try:
                current_client.models.generate_content(
                    model=model,
                    contents="Reply with OK"
                )
                return {"valid": True, "error": None}
            except Exception as e:
                err = str(e)
                last_error = err
                if "429" in err:  # Quota problem, definitely bad for this model
                    continue
                if "404" in err or "NOT_FOUND" in err:
                    continue
                # If it's a 400 API_KEY_INVALID, return immediately
                if "400" in err:
                    return {"valid": False, "error": "مفتاح API غير صحيح أو ممسوخ. يرجى التأكد من نسخه بالكامل."}
                    
        return {"valid": False, "error": f"المفتاح سليم لكن باقتك المجانية (Quota) مستنفدة أو غير متاحة في منطقتك. يرجى إنشاء مفتاح جديد من aistudio.google.com"}
        
    except Exception as e:
        return {"valid": False, "error": f"فشل الاتصال: {str(e)}"}


def get_cleaning_code(df: pd.DataFrame, user_request: str, api_key: str = None) -> dict:
    """Send metadata to Gemini and get back Python cleaning code."""
    prompt = build_prompt(df, user_request)

    import time

    key_to_use = api_key if api_key and api_key.strip() else os.getenv("GEMINI_API_KEY")
    if not key_to_use:
        return {"success": False, "error": "مفتاح API غير موجود. الرجاء إدخال مفتاح Gemini الخاص بك من aistudio.google.com/apikey", "code": ""}

    try:
        current_client = genai.Client(api_key=key_to_use)
    except Exception as e:
        return {"success": False, "error": f"مفتاح API غير صالح: {str(e)}", "code": ""}

    # Try models in order of preference
    models_to_try = [
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.5-flash",
        "models/gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    last_error = ""
    for model in models_to_try:
        try:
            response = current_client.models.generate_content(
                model=model,
                contents=prompt
            )
            raw_text = response.text
            code = _extract_code(raw_text)
            return {
                "success": True,
                "code": code,
                "raw_response": raw_text,
                "model_used": model
            }
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            # If quota error, skip to next model immediately
            if "429" in error_msg:
                continue
            # If model not found, skip silently
            if "404" in error_msg or "NOT_FOUND" in error_msg:
                continue
            # Any other error, return immediately
            return {"success": False, "error": error_msg, "code": ""}

    # If all models failed
    return {
        "success": False,
        "error": f"كل الموديلات المتاحة وصلت للحد الأقصى أو غير مدعومة. تأكد من أن مفتاح API الخاص بك قادم من: aistudio.google.com/apikey - الخطأ الأخير: {last_error[:200]}",
        "code": ""
    }



def _extract_code(text: str) -> str:
    """Extract Python code from markdown code block."""
    import re
    pattern = r"```python\s*([\s\S]*?)```"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0].strip()
    # If no code block found, return the text as-is
    return text.strip()

import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pandas as pd
import json

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


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


def get_cleaning_code(df: pd.DataFrame, user_request: str) -> dict:
    """Send metadata to Gemini and get back Python cleaning code."""
    prompt = build_prompt(df, user_request)

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw_text = response.text

            # Extract code block
            code = _extract_code(raw_text)

            return {
                "success": True,
                "code": code,
                "raw_response": raw_text
            }
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and attempt < max_retries - 1:
                time.sleep(15)  # Wait 15 seconds before retrying
                continue
            return {
                "success": False,
                "error": error_msg,
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

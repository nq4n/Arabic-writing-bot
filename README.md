# منصّة التعبير (نموذج بسيط)

## التشغيل
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```
افتح: http://127.0.0.1:5000

## حساب المدير
- اسم المستخدم: `admin`
- كلمة المرور: `admin123`

## إعدادات الذكاء الاصطناعي (اختياري)
لتفعيل الربط مع نموذج لغوي حقيقي (مثل OpenAI):
1. أضف `openai` إلى ملف `requirements.txt`.
2. قم بتثبيت المكتبة: `pip install openai`.
3. قم بتعيين مفتاح API الخاص بك كمتغير بيئة.
   - في Windows (Command Prompt): `set AI_API_KEY="sk-..."`
   - في macOS/Linux: `export AI_API_KEY="sk-..."`
4. في ملف `app.py`، قم بإلغاء التعليق عن الجزء الخاص بالمعالجة الحقيقية داخل دالة `get_ai_analysis`.

## النشر على Render (GitHub → Render)

نُوصي باستخدام Postgres على Render لأن نظام الملفات في Render غير دائم، وبالتالي SQLite غير مناسب للإنتاج.

خطوات مختصرة:

1. تأكد من أن `requirements.txt` يحتوي على الحزم التالية: `gunicorn`, `psycopg2-binary`, `python-dotenv`, `openpyxl`, `openai` (إن استخدمت).
2. قم بإنشاء خدمة Web على Render واربطها بمستودع GitHub.
3. إعداد Build Command: `pip install -r requirements.txt`.
4. إعداد Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`.
5. في صفحة Environment المتوفرة بخدمة Render، أضف المتغيرات:
   - `FLASK_SECRET_KEY` = قيمة سرية طويلة.
   - `AI_API_KEY` = مفتاح OpenAI (اختياري).
   - `SUBBASE_PG_URL` = عنوان قاعدة بيانات Postgres التي أنشأتها في Render (مثال: `postgres://user:pass@host:5432/dbname`).

تهيئة قاعدة البيانات (مرة واحدة):

بعد إنشاء Render Postgres، يمكنك تهيئتها بتشغيل الأمر التالي محليًا أو عبر واجهة Render (one-off):

```powershell
# محليًا (باستخدام سكربت البايثون المضاف)
python .\scripts\init_subbase.py

# أو باستخدام psql إذا كان متاحًا
psql $SUBBASE_PG_URL -f sql/subbase_schema_postgres.sql
```

ملاحظة: لا تقم بدفع ملف `.env` إلى GitHub. اترك فقط `.env.example` في المستودع.

## الميزات
- واجهة RTL عربية، صفحة دخول وتسجيل.
- صفحة محادثة بسيطة مع سجل رسائل ورفع ملف (غير مفعل حالياً للتطوير لاحقاً).
- تسليم "التعبير" وتقييم عام.
- لوحة تحكم للمدير: إحصائيات، معاينة التسليمات والتقييمات، تعديل الدرجات، وتصدير درجات CSV المتوافق مع Excel.

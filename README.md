# GbSA Community Detection

Community Detection با الگوریتم Galaxy-based Search Algorithm (GbSA) — یک متاهیوریستیک مبتنی بر طبیعت که از حرکت مارپیچی کهکشان‌ها و رفتار آشوبناک الهام گرفته است. همراه با **داشبورد وب تعاملی**، **دستیار هوشمند LLM** و **دو تم روشن/تاریک**.

---

## امکانات

- 🌌 پیاده‌سازی کامل الگوریتم GbSA برای شناسایی اجتماعات
- 🖥 داشبورد وب با FastAPI + فرانت بدون build (vis-network + Chart.js)
- 🎨 دو تم: روشن (پاستیلی) و تاریک — با ذخیره انتخاب کاربر
- 🤖 دستیار هوشمند LLM (سازگار با OpenAI API و Ollama لوکال):
  - تحلیل و تفسیر خودکار نتایج به فارسی
  - پیشنهاد پارامتر بهینه بر اساس مشخصات گراف
  - چت‌بات متصل (Docked) برای پرسش و پاسخ درباره نتایج
  - حلقه خودتنظیم چندعاملی (`/api/llm/autotune`)
- 📊 رسم تعاملی گراف با رنگ‌بندی اجتماعات + نمودار همگرایی Q
- 📁 آپلود گراف دلخواه (edge list) از طریق مرورگر

---

## الگوریتم GbSA چیست؟

Galaxy-based Search Algorithm (GbSA) یک الگوریتم بهینه‌سازی تکامل‌محور است که توسط **Hamed Shah-Hosseini** در سال ۲۰۱۱ معرفی شد. این الگوریتم از دو ویژگی فیزیکی کهکشان‌ها الهام گرفته است:

1. **حرکت مارپیچی (Spiral Move):** ستاره‌ها (راه‌حل‌ها) در بازوهای مارپیچی کهکشان حرکت می‌کنند و فضای جستجو را به صورت مارپیچی کاوش می‌کنند.
2. **حرکت آشوبناک (Chaotic Move):** رفتار آشوبناک و غیرخطی در طبیعت، برای فرار از بهینه محلی به کار می‌رود.

### اجزای اصلی الگوریتم

| مؤلفه | توضیح |
|------|--------|
| **Star (ستاره)** | یک راه‌حل کاندید؛ در این پروژه: یک partition از گراف (تخصیص هر نود به یک community) |
| **Galaxy (کهکشان)** | جمعیت ستاره‌ها (population) |
| **Spiral Chaotic Move** | اکتشاف (exploration): تولید partition جدید با جابه‌جایی چند نود به communityهای دیگر به‌صورت تصادفی/آشوبناک |
| **Local Search** | بهره‌برداری (exploitation): جابه‌جایی یک نود بین دو community برای بهبود محلی Modularity |
| **Fitness** | تابع Modularity (Q) که کیفیت partition را ارزیابی می‌کند |
| **Elitism** | نگه‌داشتن بهترین ستاره در هر iteration برای جلوگیری از افت کیفیت |

### مراحل اجرا

```
1. تولید جمعیت اولیه ( galaxy از starهای تصادفی )
2. ارزیابی هر star با Modularity
3. تکرار تا رسیدن به iterations:
   a. برای هر star:
      - Spiral Chaotic Move → partition جدید
      - Local Search → بهبود partition
      - اگر بهتر بود → جایگزینی star
   b. Elitism: بهترین star را در جمعیت نگه دار
4. بازگشت بهترین partition و تاریخچه Q
```

### تابع هدف: Modularity (Q)

Modularity کیفیت تقسیم‌بندی را با مقایسه چگالی یال‌های داخل community با آنچه تصادفی انتظار می‌رود، می‌سنجد:

```
Q = (1/2m) * Σ_ij [ A_ij - (k_i * k_j / 2m) ] * δ(c_i, c_j)
```

- `A_ij`: وزن یال بین نود i و j
- `k_i, k_j`: درجه نودها
- `m`: تعداد کل یال‌ها
- `δ(c_i, c_j)`: برابر ۱ اگر i و j در یک community باشند، وگرنه ۰

مقدار Q در بازه `[-0.5, 1)` قرار دارد؛ هرچه به ۱ نزدیک‌تر، تقسیم‌بندی بهتر.

---

## ساختار پروژه

```
gbsa_community/
├── config.py            # پیکربندی (بارگذاری از .env)
├── graph_loader.py      # load_graph(path) -> networkx.Graph
├── modularity.py        # calculate_modularity(graph, partition) -> float
├── gbsa.py              # کلاس GbSA (spiral_chaotic_move, local_search, run)
├── llm.py               # دستیار هوشمند (تحلیل، پیشنهاد پارامتر، چت)
├── autotune.py          # حلقه خودتنظیم Executor + Critic
├── main.py              # اجرای CLI + پرینت/رسم نتیجه
├── app.py               # سرور FastAPI (API + سرو فرانت)
├── static/              # فرانت‌اند (بدون build)
│   ├── index.html       # داشبورد (vis-network + Chart.js از CDN)
│   ├── style.css        # دو تم روشن/تاریک با CSS variables
│   └── app.js           # منطق فرانت + تعویض تم + چت
├── .env                 # تنظیمات LLM و الگوریتم (کلید API اینجا)
├── pyproject.toml       # وابستگی‌ها و تنظیمات uv
├── uv.lock              # فایل قفل وابستگی‌ها
└── data/
    ├── karate.gml       # دیتاست نمونه: Zachary's Karate Club
    └── test_graph.txt   # گراف تست: 40 نود، 4 اجتماع واضح (Q≈0.63)
```

---

## نصب و اجرا

### پیش‌نیاز

- [uv](https://docs.astral.sh/uv/) (مدیر بسته و محیط مجازی)

### نصب وابستگی‌ها

```bash
cd gbsa_community
uv sync
```

### تنظیمات (.env)

فایل `.env` را ویرایش کنید:

```bash
# LLM — OpenAI-compatible API
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-...              # your key
OPENAI_MODEL=gpt-4o-mini
OPENAI_REQUEST_TIMEOUT=60
OPENAI_ENABLED=true

# Algorithm
GBSA_POPULATION_SIZE=20
GBSA_ITERATIONS=50
GBSA_DATASET_PATH=data/karate.gml
```

**Local Ollama** (without changing `.env`):

```powershell
$env:GBSA_LLM_PROVIDER = "ollama"      # default model: llama3.2
$env:GBSA_LLM_MODEL = "mistral"        # optional
```

Priority: `GBSA_LLM_*` (OS env) ← `OPENAI_*` (`.env`) ← defaults

### اجرای CLI

```bash
uv run python main.py
```

خروجی: بهترین partition + مقدار Q + نمودار همگرایی → `convergence.png`

### اجرای داشبورد وب

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

سپس در مرورگر: **http://127.0.0.1:8000**

---

## داشبورد وب

- **پیکربندی:** آپلود گراف (edge list)، تنظیم population و iterations، پیشنهاد پارامتر با AI
- **آمار:** نودها، یال‌ها، تعداد اجتماعات، Modularity در یک پنل یکپارچه
- **گراف تعاملی:** رنگ‌بندی پاستیلی اجتماعات با vis-network
- **نمودار همگرایی:** روند بهبود Q با Chart.js
- **تحلیل هوشمند:** گزارش فارسی LLM درباره کیفیت خوشه‌بندی
- **چت‌بات متصل:** پنل شیشه‌ای (Glassmorphism) گوشه پایین — سوال بپرسید، AI با آگاهی از داده‌ها جواب می‌دهد
- **تم روشن/تاریک:** دکمه ☀️/🌙 در هدر — انتخاب در localStorage ذخیره می‌شود

### API Endpoints

| متد | مسیر | توضیح |
|-----|------|--------|
| `GET` | `/` | داشبورد وب |
| `POST` | `/api/run` | اجرای GbSA (multipart: file, population_size, iterations) |
| `POST` | `/api/llm/analyze` | تحلیل نتایج با LLM |
| `POST` | `/api/llm/suggest` | پیشنهاد پارامتر بهینه |
| `POST` | `/api/llm/chat` | چت درباره نتایج |
| `POST` | `/api/llm/autotune` | حلقه خودتنظیم Executor + Critic |
| `GET` | `/api/health` | بررسی سلامت سرور |

#### مثال `/api/run`

```bash
curl -X POST http://127.0.0.1:8000/api/run \
  -F "population_size=20" \
  -F "iterations=50" \
  -F "file=@data/test_graph.txt"
```

پاسخ (JSON):

```json
{
  "source": "test_graph.txt",
  "num_nodes": 40,
  "num_edges": 95,
  "num_communities": 4,
  "modularity": 0.6358,
  "history": [0.24, 0.33, ...],
  "nodes": [{"id": 0}, ...],
  "edges": [{"source": 0, "target": 1}, ...],
  "partition": [0, 0, 1, ...]
}
```

---

## دیتاست‌ها

| فایل | توضیح | Q تقریبی |
|------|--------|----------|
| `data/karate.gml` | Zachary's Karate Club — ۳۴ نود، ۷۸ یال | ~0.42 |
| `data/test_graph.txt` | گراف مصنوعی — ۴۰ نود، ۴ اجتماع واضح | ~0.63 |

### استفاده از دیتاست دیگر

فایل edge list (هر خط: `node1 node2`) را از داشبورد آپلود کنید، یا `GBSA_DATASET_PATH` را در `.env` تغییر دهید.

---

## رفرنس‌ها

۱. **مقاله اصلی (الگوریتم GbSA):**

   Shah-Hosseini, H. (2011).
   *The Galaxy-based Search Algorithm: A Novel Metaheuristic for Optimization.*
   International Journal of Applied Evolutionary Computation (IJAEC), 2(2), 19–35.
   DOI: [10.4018/jaec.2011040102](https://doi.org/10.4018/jaec.2011040102)

۲. **تابع Modularity:**

   Newman, M. E. J., & Girvan, M. (2004).
   *Finding and evaluating community structure in networks.*
   Physical Review E, 69(2), 026113.
   DOI: [10.1103/PhysRevE.69.026113](https://doi.org/10.1103/PhysRevE.69.026113)

۳. **دیتاست Karate Club:**

   Zachary, W. W. (1977).
   *An information flow model for conflict and fission in small groups.*
   Journal of Anthropological Research, 33(4), 452–473.
   DOI: [10.1086/jar.33.4.3629752](https://doi.org/10.1086/jar.33.4.3629752)

۴. **کتابخانه NetworkX (محاسبه Modularity):**

   Hagberg, A., Schult, D., & Swart, P. (2008).
   *Exploring network structure, dynamics, and function using NetworkX.*
   Proceedings of the Python in Science Conference (SciPy), 11–15.

---

## لیسانس

MIT

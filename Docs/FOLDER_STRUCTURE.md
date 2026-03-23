# 📁 Airco Insights — Clean Folder Structure

## 🎯 Root Directory
```
FinTech SAAS/
├── 📄 README.md                    # Main project documentation
├── 📄 FOLDER_STRUCTURE.md         # This file
├── 📄 .env                        # Environment variables (DO NOT COMMIT)
├── 📄 .env.example                # Environment template
├── 📄 docker-compose.yml          # Docker orchestration
├── 📄 package.json                # Root package config
│
├── 📂 backend/                    # ⭐ Processing Engine (Python/FastAPI)
├── 📂 frontend/                   # 🎨 User Interface (Next.js/React)
├── 📂 database/                   # 🗄️ Database setup & migrations
├── 📂 Docs/                       # 📚 System documentation
├── 📂 HDFC DATA/                  # 🧪 Test data (HDFC statements)
├── 📂 scripts/                    # 🔧 Utility scripts
└── 📂 legacy/                     # 🗄️ Archived old files
```

---

## 🚀 Backend (Core Processing Engine)

```
backend/
├── 📄 README.md                   # Backend documentation
├── 📄 requirements.txt            # Python dependencies
├── 📄 Dockerfile                  # Container configuration
│
├── 📂 app/                        # Main application
│   ├── 📄 main.py                 # FastAPI entry point
│   │
│   ├── 📂 services/               # ⭐ Core Processing Services
│   │   ├── 📂 banks/              # 🏦 Bank-Specific Processors (V2)
│   │   │   ├── 📄 README.md      # Bank module documentation
│   │   │   └── 📂 hdfc/          # ✅ HDFC Bank (Complete)
│   │   │       ├── processor.py           # Master controller
│   │   │       ├── structure_validator.py # Format validation
│   │   │       ├── parser.py              # Transaction extraction
│   │   │       ├── transaction_validator.py # Field validation
│   │   │       ├── reconciliation.py      # Balance verification
│   │   │       ├── rule_engine.py         # Classification (500+ rules)
│   │   │       ├── ai_fallback.py         # Claude AI integration
│   │   │       ├── recurring_engine.py    # Pattern detection
│   │   │       ├── aggregation_engine.py  # Financial analytics
│   │   │       └── excel_generator.py     # Report generation
│   │   │
│   │   ├── 📂 core/               # 🔒 Core Validators
│   │   │   ├── pdf_integrity_validator.py # PDF validation
│   │   │   └── data_integrity_guard.py    # Final integrity check
│   │   │
│   │   ├── 📄 pipeline_orchestrator_v2.py # ⭐ V2 Pipeline (Bank-Specific)
│   │   └── 📂 legacy_v1/          # 📦 Old Architecture (Archived)
│   │       └── (deprecated files...)
│   │
│   ├── 📂 routers/                # 🛣️ API Endpoints
│   │   ├── upload_v2.py          # ⭐ V2 Accuracy-First Endpoint
│   │   ├── upload.py             # Legacy V1 endpoint
│   │   └── download.py           # File downloads
│   │
│   ├── 📂 api/                    # 📡 Additional APIs
│   │   └── routes/
│   │       └── feedback.py       # User feedback collection
│   │
│   ├── 📂 core/                   # ⚙️ Core Config
│   │   ├── config.py             # Settings & environment
│   │   └── security.py           # Upload validation
│   │
│   ├── 📂 database/               # 🗄️ Database Layer
│   │   ├── session.py            # DB connection
│   │   └── models.py             # SQLAlchemy models
│   │
│   └── 📂 utils/                  # 🛠️ Utilities
│       └── file_handler.py       # File operations
│
├── 📂 scripts/                    # 🧪 Testing & Analysis Scripts
│   ├── test_hdfc_v2.py           # ⭐ HDFC V2 test suite
│   ├── analyze_all_pdfs.py       # Bulk PDF analysis
│   └── find_unclassified_patterns.py # Pattern discovery
│
├── 📂 tests/                      # ✅ Unit & Integration Tests
├── 📂 temp/                       # 📁 Temporary files (auto-cleanup)
└── 📂 legacy/                     # 📦 Archived scripts
```

---

## 🎨 Frontend (User Interface)

```
frontend/
├── 📄 README.md                   # Frontend documentation
├── 📄 package.json                # Dependencies
├── 📄 next.config.js              # Next.js config
├── 📄 Dockerfile                  # Container config
│
├── 📂 app/                        # Next.js 13+ App Router
│   ├── page.tsx                   # Main upload page
│   ├── layout.tsx                 # Root layout
│   ├── globals.css                # Global styles
│   │
│   ├── 📂 components/             # React components
│   │   ├── UploadForm.tsx        # File upload component
│   │   ├── ProcessingStatus.tsx  # Status display
│   │   └── ResultsPreview.tsx    # Results viewer
│   │
│   └── 📂 api/                    # API routes (if needed)
│
├── 📂 lib/                        # Utilities
│   ├── api.ts                     # Backend API client
│   ├── supabase.ts                # Supabase client
│   └── validation.ts              # Form validation
│
└── 📂 node_modules/               # Dependencies (auto-generated)
```

---

## 🗄️ Database

```
database/
├── 📄 init.sql                    # Initial schema
├── 📄 setup_supabase.py           # Supabase setup script
│
├── 📂 migrations/                 # Schema migrations
│   └── version_001_init.sql      # Initial migration
│
└── 📂 docker/                     # Local PostgreSQL
    └── postgres.conf              # Configuration
```

---

## 📚 Documentation

```
Docs/
├── IMPLEMENTATION_SUMMARY.md      # System implementation guide
├── DEPLOYMENT_GUIDE.md            # Deployment instructions
├── ADAPTIVE_LEARNING_SYSTEM_DESIGN.md # Learning system design
├── FINAL_SUMMARY.md               # Project summary
└── (other documentation...)
```

---

## 🧪 Test Data

```
HDFC DATA/
├── Acct_Statement_Jan to 4 Feb 26.pdf
├── Acct_Statement_XXXXXXXX0089_27012026.pdf
├── Acct_Statement_XXXXXXXX6631 Jan 25 to Dec 25.pdf
└── (12 HDFC test PDFs total)
```

---

## 🔧 Scripts (Root Level)

```
scripts/
└── generate_hdfc_excel.py         # Legacy Excel generator (archived)
```

---

## 📦 Legacy (Archived)

```
legacy/
├── Data/                          # Old data folder
└── (other archived files...)
```

---

## 🎯 Key Files to Know

### Backend API Entry Points
- **`backend/app/main.py`** - FastAPI application (start here)
- **`backend/app/routers/upload_v2.py`** - V2 accuracy-first endpoint ⭐
- **`backend/app/services/pipeline_orchestrator_v2.py`** - V2 pipeline router

### HDFC Processing (Complete Implementation)
- **`backend/app/services/banks/hdfc/processor.py`** - HDFC master controller
- **`backend/app/services/banks/hdfc/rule_engine.py`** - 500+ classification rules

### Core Validators
- **`backend/app/services/core/pdf_integrity_validator.py`** - PDF validation
- **`backend/app/services/core/data_integrity_guard.py`** - Final integrity gate

### Testing
- **`backend/scripts/test_hdfc_v2.py`** - HDFC testing script

### Configuration
- **`.env`** - Environment variables (create from `.env.example`)
- **`docker-compose.yml`** - Docker orchestration

---

## 🚀 Quick Commands

### Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### Test HDFC
```bash
cd backend
python scripts/test_hdfc_v2.py
```

### Docker (All Services)
```bash
docker-compose up --build
```

---

## 📊 File Count Summary

| Directory | Purpose | Status |
|-----------|---------|--------|
| `backend/app/services/banks/hdfc/` | HDFC Processor | ✅ Complete (11 files) |
| `backend/app/services/core/` | Core Validators | ✅ Complete (3 files) |
| `backend/app/services/legacy_v1/` | Old Architecture | 📦 Archived |
| `backend/app/routers/` | API Endpoints | ✅ Active (3 files) |
| `backend/scripts/` | Test Scripts | ✅ Active (3 files) |

---

## 🎨 Clean Architecture Benefits

✅ **Clear Separation:** V2 (new) vs legacy_v1 (old)  
✅ **Bank-Specific:** Each bank in its own module  
✅ **Easy Navigation:** Logical folder hierarchy  
✅ **Well Documented:** README at every level  
✅ **Test Scripts:** Organized in scripts/ folder  
✅ **No Clutter:** Legacy files archived  

---

**Last Updated:** February 17, 2026  
**Architecture Version:** 2.0 (Accuracy-First)  
**Maintained By:** Airco Insights Team

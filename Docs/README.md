# Airco Insights

**Financial Statement Intelligence Engine**

A production-grade fintech SaaS that processes Indian bank statement PDFs, classifies transactions using a hybrid rule engine + AI, and generates structured financial reports.

## Architecture

| Layer | Technology | Port |
|-------|-----------|------|
| Frontend | Next.js + Tailwind CSS | 3000 |
| Backend | FastAPI (Python) | 8000 |
| Database | PostgreSQL (Supabase) | 5432 |

## Quick Start

```bash
# Start everything with Docker
npm run start

# Or run frontend only (development)
npm run dev:frontend
```

## Core Features

- PDF bank statement upload & parsing
- Bank-specific extraction (HDFC, ICICI, Axis, Kotak, SBI)
- Hybrid classification: Rule Engine + Claude AI fallback
- Recurring transaction detection
- Multi-sheet Excel report generation
- PDF export via LibreOffice headless
- Merchant memory database for improving accuracy over time

## Processing Pipeline

1. PDF Type Detection (digital vs scanned)
2. Bank Detection & Routing
3. Structured Transaction Extraction
4. Data Cleaning & Normalization
5. Rule-Based Categorization (65-75%)
6. AI Classification — Claude fallback (remaining 25-35%)
7. Confidence Scoring & Validation
8. Recurring Detection Engine
9. Aggregation & Analytics
10. Excel Generation (Multi-Sheet)
11. PDF Conversion (LibreOffice Headless)

## Report Sheets

- **Sheet 1** — Summary
- **Sheet 2** — Category Analysis
- **Sheet 3** — Weekly Analysis
- **Sheet 4** — Recurring Analysis
- **Sheet 5** — Raw Transactions (with confidence scores)

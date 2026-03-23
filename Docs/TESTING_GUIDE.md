# 🧪 Testing Guide - Adaptive Learning System

## 🎯 System Status: READY FOR TESTING

✅ **Docker containers built and running**
✅ **Backend API available at http://localhost:8000**
✅ **Frontend available at http://localhost:3000**
✅ **Learning endpoints deployed**
✅ **Data directories created**

---

## 🚀 Quick Test Checklist

### 1. Verify System Health
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","engine":"airco-insights","version":"1.0.0"}
```

### 2. Check Learning System
```bash
curl http://localhost:8000/feedback/learning/summary
# Expected: JSON with learning statistics (currently empty)
```

### 3. View API Documentation
Open in browser: http://localhost:8000/docs

---

## 📋 Complete Testing Workflow

### Phase 1: Basic System Tests

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

#### Test 2: Learning Summary
```bash
curl http://localhost:8000/feedback/learning/summary
```

#### Test 3: Dynamic Rules
```bash
curl http://localhost:8000/feedback/rules/dynamic
```

### Phase 2: PDF Processing Tests

#### Test 4: Upload a PDF via Frontend
1. Open http://localhost:3000 in browser
2. Click "Upload PDF"
3. Select any PDF from the `Data` folder
4. Choose the correct bank
5. Click "Process"
6. **Expected**: Transaction results displayed

#### Test 5: Check Learning Data After Upload
```bash
curl http://localhost:8000/feedback/learning/summary
# Should show increased total_samples
```

### Phase 3: Learning System Tests

#### Test 6: Submit Transaction Correction
```bash
curl -X POST http://localhost:8000/feedback/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "test_123",
    "corrected_category": "Shopping",
    "user_id": "test@example.com",
    "method": "ui"
  }'
```

#### Test 7: Trigger Learning Manually
```bash
curl -X POST http://localhost:8000/feedback/learning/trigger \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

#### Test 8: Monitor Learning Progress
```bash
curl http://localhost:8000/feedback/learning/summary
```

---

## 🎯 Expected Results

### Initial State (Before Testing)
```json
{
  "data_collection": {
    "total_samples": 0,
    "unclassified": 0,
    "total_corrections": 0,
    "ready_for_learning": false
  },
  "dynamic_rules": {
    "total_rules": 0,
    "active_rules": 0
  }
}
```

### After PDF Upload
```json
{
  "data_collection": {
    "total_samples": 1000+,  // Transactions from uploaded PDF
    "unclassified": 5-50,     // Unclassified transactions
    "total_corrections": 0,
    "ready_for_learning": false
  }
}
```

### After 5+ Corrections
```json
{
  "data_collection": {
    "total_samples": 1000+,
    "unclassified": 5-50,
    "total_corrections": 5+,   // Corrections submitted
    "ready_for_learning": true  // Learning can be triggered
  }
}
```

### After Learning Trigger
```json
{
  "dynamic_rules": {
    "total_rules": 3-5,      // New rules generated
    "active_rules": 0-3,     // Rules that passed testing
    "by_status": {
      "testing": 1-2,
      "active": 1-3
    }
  }
}
```

---

## 🔧 Advanced Testing

### Test Claude Learning Engine (Requires API Key)
1. Add `ANTHROPIC_API_KEY` to `.env` file
2. Restart Docker: `docker-compose restart backend`
3. Upload 3-4 PDFs to collect 50+ unclassified
4. Trigger learning: `curl -X POST http://localhost:8000/feedback/learning/trigger -d '{"force": true}'`
5. Check logs: `docker logs fintech_backend -f`

### Test Dynamic Rule Activation
1. Get rule ID from `/feedback/rules/dynamic`
2. Activate: `curl -X POST http://localhost:8000/feedback/rules/activate/{rule_id}`
3. Process another PDF to see rule in action

### Test Performance Monitoring
```bash
# Monitor learning activity
docker logs fintech_backend | grep "learning\|pattern\|rule"

# Expected logs:
# "Learning data collected: X transactions"
# "Discovered X patterns"
# "Generated X rule suggestions"
# "Auto-deployed rule: RuleName"
```

---

## 📱 Frontend Testing

### Upload Flow
1. Navigate to http://localhost:3000
2. Click "Upload PDF"
3. Select file from `Data` folder
4. Select bank from dropdown
5. Click "Process"
6. Wait for processing
7. Review results

### Expected UI Elements
- File upload button
- Bank selection dropdown
- Processing indicator
- Transaction results table
- Category corrections (if implemented)
- Download Excel/PDF buttons

### Test All Banks
Test with PDFs from each bank:
- HDFC (multiple PDFs available)
- ICICI
- Kotak
- Axis
- HSBC

---

## 🐛 Troubleshooting

### Issue: "Upload failed: 404"
**Solution**: Check if upload endpoint exists
```bash
curl http://localhost:8000/docs
# Look for POST /upload endpoint
```

### Issue: "Correction failed: 500"
**Solution**: Check backend logs
```bash
docker logs fintech_backend --tail 50
```

### Issue: Learning not working
**Solution**: Verify Claude API key
```bash
# Check .env file
cat .env | grep ANTHROPIC
```

### Issue: No learning data collected
**Solution**: Check if pipeline integration is working
```bash
docker logs fintech_backend | grep "Learning data collected"
```

---

## 📊 Performance Benchmarks

### Expected Performance
- **PDF Processing**: 5-30 seconds per PDF
- **Learning Trigger**: 10-60 seconds (depends on data size)
- **Rule Generation**: 5-20 seconds per rule
- **API Response**: <200ms for endpoints

### Load Testing (Optional)
```bash
# Upload 5 PDFs sequentially
for file in Data/*.pdf; do
  echo "Processing $file..."
  curl -X POST http://localhost:8000/upload \
    -F "file=@$file" \
    -F "bank_name=hdfc"
  sleep 5
done
```

---

## ✅ Success Criteria

### Minimum Viable Test
- [ ] Health endpoint returns 200
- [ ] Can upload and process a PDF
- [ ] Learning summary endpoint works
- [ ] Can submit transaction correction
- [ ] Can trigger learning manually

### Full System Test
- [ ] All 5 banks process correctly
- [ ] Learning data collected automatically
- [ ] Corrections trigger learning
- [ ] Dynamic rules generated (with Claude API)
- [ ] Rules can be activated/deactivated
- [ ] System maintains 99%+ accuracy

---

## 🎯 Next Steps After Testing

### If Tests Pass
1. Add Claude API key to enable full learning
2. Process all 17 PDFs to build learning database
3. Submit sample corrections to test learning cycle
4. Monitor rule generation and deployment

### If Tests Fail
1. Check Docker logs: `docker logs fintech_backend`
2. Verify all files are in place
3. Check environment variables
4. Review error messages

---

## 📞 Support

### Quick Commands
```bash
# Check container status
docker-compose ps

# View logs
docker logs fintech_backend -f

# Restart services
docker-compose restart

# Stop services
docker-compose down
```

### Key Files to Check
- `docker-compose.yml` - Container configuration
- `.env` - Environment variables
- `app/main.py` - FastAPI app setup
- `app/api/routes/feedback.py` - Learning endpoints

---

## 🎉 Ready to Test!

Your adaptive learning system is now:
✅ **Built and deployed**
✅ **Ready for PDF processing**
✅ **Learning infrastructure active**
✅ **API endpoints available**

**Start with Phase 1 tests and work through each phase systematically.**

Good luck! 🚀

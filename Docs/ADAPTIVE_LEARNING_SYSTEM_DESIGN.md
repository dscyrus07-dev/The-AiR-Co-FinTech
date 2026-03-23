# Adaptive Learning System - Complete Design Document

## 🎯 Goal
Achieve and maintain 100% transaction classification accuracy through continuous learning from:
- New PDF uploads
- User corrections/feedback (including WhatsApp)
- Pattern discovery via Claude API
- Automatic rule generation

## 🏗️ Architecture

### Phase 1: Learning Data Collection
```
New PDF → Extract → Classify → Track Results → Store Learning Data
                                    ↓
                            Unclassified/Low-Confidence
                                    ↓
                            Learning Database
```

### Phase 2: Claude-Powered Analysis
```
Learning Database → Pattern Discovery (Claude) → Rule Suggestions → Validation → Auto-Deploy
                           ↓
                    New Bank Detection → Parser Generation → Test → Deploy
```

### Phase 3: Feedback Loop
```
User Feedback → Correction → Update Learning DB → Retrain → Deploy Updates
     ↓
WhatsApp Integration (+91 70213 20783)
```

## 📦 Components

### 1. Learning Data Collector (`learning_data_collector.py`)
- Tracks every transaction with confidence scores
- Stores unclassified transactions
- Maintains user correction history
- Generates transaction fingerprints

### 2. Claude Learning Engine (`claude_learning_engine.py`)
- Pattern Discovery: Analyze unclassified transactions
- Rule Generation: Create new classification rules
- Parser Generation: Auto-generate parsers for new banks
- Confidence Scoring: Validate suggestions before deployment

### 3. Adaptive Rule Manager (`adaptive_rule_manager.py`)
- Dynamic Rule Injection: Add new rules without code changes
- A/B Testing: Test new rules on subset before full deployment
- Rollback: Revert bad rules automatically
- Version Control: Track all rule changes

### 4. Feedback API (`feedback_routes.py`)
- POST /api/feedback/transaction - User corrections
- POST /api/feedback/category - Category suggestions
- GET /api/learning/summary - Learning progress
- POST /api/learning/trigger - Manual learning trigger

### 5. Pipeline Integration (`pipeline_orchestrator.py` updates)
- Auto-collect learning data after each processing
- Trigger Claude analysis when threshold reached
- Apply validated rules automatically
- Log all learning activities

## 🔄 Learning Workflow

### Daily Automatic Learning:
```
1. Collect unclassified transactions (threshold: 50)
2. Call Claude API for pattern analysis
3. Generate rule suggestions
4. Validate on historical data
5. Auto-deploy if confidence > 90%
6. Send summary email/notification
```

### Real-time User Feedback:
```
1. User corrects transaction category (via UI or WhatsApp)
2. Store correction in learning database
3. If 5+ corrections for same pattern → trigger immediate learning
4. Generate and test rule
5. Deploy if validated
6. Notify user of improvement
```

## 📊 Success Metrics
- **Accuracy**: Target 100%, maintain > 99%
- **Learning Speed**: New patterns detected within 24 hours
- **Auto-Fix Rate**: 80%+ of new patterns fixed automatically
- **User Corrections**: < 10 per 1000 transactions

## 🔐 Safety Mechanisms
1. **Confidence Gating**: Only deploy rules with >90% confidence
2. **Shadow Mode**: Test new rules on historical data first
3. **Rollback**: Auto-revert if accuracy drops
4. **Human Review**: Flag low-confidence suggestions for review
5. **Audit Log**: Track all automatic changes

## 🚀 Deployment Strategy
1. **Week 1**: Deploy learning infrastructure (data collection only)
2. **Week 2**: Enable Claude analysis (manual review required)
3. **Week 3**: Enable auto-deployment for high-confidence rules
4. **Week 4**: Full autonomous learning with monitoring

## 📱 WhatsApp Integration
- Users send corrections via WhatsApp: "+91 70213 20783"
- Format: "Correct [Transaction ID] to [Category]"
- Bot responds with confirmation and learning status
- Critical for users who prefer mobile feedback

## 🛠️ Technical Stack
- **Backend**: FastAPI Python
- **Learning**: Claude API (Anthropic)
- **Storage**: JSON files + future PostgreSQL
- **Queue**: Background tasks for learning
- **Monitoring**: Logging + metrics dashboard

## 📈 Expected Impact
- **Current**: 99.4% accuracy (manual rule updates)
- **After 1 month**: 99.8% accuracy (with learning)
- **After 3 months**: 99.9%+ accuracy (mature system)
- **Maintenance**: Near-zero manual intervention

## 🎓 Learning Examples

### Example 1: New Merchant Pattern
```
Unclassified: "POS403875XXXXXX8496IBIBOWEBPRIVAT"
Claude Analysis: "IBIBO" = MakeMyTrip parent company
Suggestion: Add "IBIBOWEB" to Shopping keywords
Validation: 9/9 similar transactions correctly classified
Action: Auto-deployed ✅
```

### Example 2: New Bank Format
```
Unknown Bank: HSBC statements
Claude Analysis: Detected HSBC format from headers
Generated: hsbc_parser.py template
Validation: Successfully parsed test statement
Action: Deployed with manual review ✅
```

### Example 3: User Correction
```
User Feedback: "EPFO should be Provident Fund, not Bank Transfer"
Learning: 6 similar EPFO transactions found
Suggestion: Create new "Provident Fund" rule
Validation: 100% match on historical data
Action: Auto-deployed + user notified ✅
```

## 🔮 Future Enhancements
1. **Multi-language Support**: Hindi, regional languages
2. **Image OCR**: Handle scanned statements
3. **Predictive Learning**: Anticipate new patterns
4. **Collaborative Learning**: Learn from all users
5. **Real-time Processing**: Sub-second classification

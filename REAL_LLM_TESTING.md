# 🔥 Real LLM Testing Guide

The timepoint-daedalus project supports **both dry-run testing (fast, free)** and **real LLM testing (slow, costs money)**.

## 🚀 Quick Start

### Option 1: Dry-Run Testing (Recommended for Development)
```bash
# Fast, free, deterministic tests
pytest --cov
```

### Option 2: Real LLM Testing (When you want to test actual AI responses)
```bash
# 1. Get API key from https://openrouter.ai/keys
# 2. Set environment variable
export OPENROUTER_API_KEY="your_api_key_here"

# 3. Run tests with real LLM calls
pytest test_framework.py::test_llm_methods --verbose-tests -v

# Or use the convenience script
./test_real_llm.py
```

## 📊 Comparison

| Feature | Dry-Run Mode | Real LLM Mode |
|---------|--------------|----------------|
| **Speed** | ⚡ ~3 seconds | 🐌 ~30-60 seconds |
| **Cost** | 💰 Free | 💸 $0.01-0.05 per test run |
| **Deterministic** | ✅ Yes | ❌ No (LLM responses vary) |
| **API Required** | ❌ No | ✅ OpenRouter API key |
| **Internet Required** | ❌ No | ✅ Yes |
| **CI/CD Friendly** | ✅ Yes | ❌ No |

## 🧪 Test Coverage

- **Dry-run mode**: 76% coverage on llm.py (tests logic, not API calls)
- **Real LLM mode**: 100% coverage on llm.py (tests actual API integration)

## 🔧 API Setup

1. **Sign up** at [OpenRouter.ai](https://openrouter.ai/)
2. **Get API key** from [Keys page](https://openrouter.ai/keys)
3. **Set environment variable**:
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxx"
   ```
4. **Verify setup**:
   ```bash
   python -c "import os; print('API key set:', bool(os.getenv('OPENROUTER_API_KEY')))"
   ```

## 🏃 Running Real LLM Tests

### Individual Test
```bash
pytest test_framework.py::test_llm_methods --verbose-tests -v
```

### Full Suite with Real LLM
```bash
export OPENROUTER_API_KEY="your_key"
pytest --cov --verbose-tests
```

### Integration Tests Only
```bash
export OPENROUTER_API_KEY="your_key"
pytest -m integration --verbose-tests -v
```

## 📈 Expected Output

### Dry-Run Mode
```
🧪 USING DRY-RUN LLM CLIENT (no API key - set OPENROUTER_API_KEY for real calls)
Testing LLM methods
Cost: $0.0000, Tokens: 0
✓ Dry-run LLM test passed
✓ test_llm_methods passed
```

### Real LLM Mode
```
🔥 USING REAL LLM CLIENT (API key detected)
Testing LLM methods
Testing entity population...
Testing consistency validation...
Cost: $0.0123, Tokens: 1234
✓ Real LLM test passed (cost: $0.0123)
✓ test_llm_methods passed
```

## ⚠️ Important Notes

- **Costs add up**: Each test run costs ~$0.01-0.05
- **Rate limits**: OpenRouter has rate limits - don't run tests excessively
- **CI/CD**: Use dry-run mode for automated testing
- **Flaky tests**: Real LLM responses can vary, making tests less deterministic

## 🔄 Switching Between Modes

The tests automatically detect which mode to use:

- **API key present** → Real LLM calls
- **No API key** → Dry-run mode

You can force dry-run mode even with an API key:
```bash
pytest test_framework.py::test_llm_methods -k "dry_run" -v
```

## 🎯 When to Use Real LLM Testing

✅ **Use real LLM testing when:**
- Testing actual AI response quality
- Validating structured output parsing
- Checking API integration
- Before production deployment

❌ **Use dry-run testing when:**
- Developing new features
- Running in CI/CD
- Quick feedback during coding
- Cost-conscious testing

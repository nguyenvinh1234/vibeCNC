# AI Provider Strategy for Mach3Turn

**Created:** 2026-09-08  
**Status:** Planning phase (V0.3 preparation)  
**Related PR:** #1 (Mach3Turn implementation tracker)

---

## Executive Summary

The current V0.3 plan prioritizes **paid cloud AI providers only** (Codex CLI, OpenAI API, Anthropic API). However, adding **free-tier providers** as primary options significantly improves user onboarding and adoption without sacrificing capability.

**Recommendation:** Implement a **tiered provider strategy** with free options first, paid upgrades available for unlimited usage.

---

## Current State (V0.3 Baseline)

### Paid-Only Providers (All Require Cost)

| Provider | Cost Model | Authentication | Best For |
|---|---|---|---|
| **Codex CLI** | ChatGPT Plus subscription (~$20/mo) | Browser login via `codex` CLI | Seamless desktop CLI integration |
| **Claude Subscription** | Claude.ai Pro (~$20/mo) | Browser login or API key | Easy for non-technical users |
| **OpenAI API** | Pay-as-you-go (~$0.01-0.05 per query) | API key (credit card required) | High-volume production use |
| **Anthropic API** | Pay-as-you-go (~$0.003-0.015 per query) | API key (credit card required) | Claude reasoning capabilities |

### Adoption Friction

1. ❌ **Day 1 barrier:** New CNC operators cannot start without credit card or subscription
2. ❌ **Cost perception:** "AI = expensive" even though vibeCNC core is free
3. ❌ **Slow feedback:** Limited early users → fewer bug reports for V0.4 guardrails
4. ❌ **Geographic limits:** Some regions cannot easily access paid APIs

---

## Proposed: Free-Tier + Subscription Provider Landscape (2024-2025)

### Tier 1: Recommended Free Providers (No Card Required)

All of these have **free API tiers with no credit card**, suitable for typical CNC operator usage patterns (10-50 queries/day):

#### 🟢 **Google Gemini** (HIGHEST PRIORITY)
- **Free tier:** 1,500 requests/day
- **Model:** Gemini 2.0 Flash (reasoning) or 1.5 Pro (general)
- **Setup:** Register at https://makersuite.google.com (Google account only)
- **Why:** Enterprise-grade, most generous free tier, supports long context
- **Cost:** Free → Paid upgrade available
- **Latency:** ~2-5 seconds
- **G-code use case:** Modal validation, safety rule review

#### 🟢 **Groq** (Speed-Optimized)
- **Free tier:** 14,400 requests/day (240 req/min)
- **Model:** Llama 3.1 70B (inference engine optimized)
- **Setup:** Register at https://console.groq.com
- **Why:** Fastest inference available (~500ms), excellent for quick feedback loops
- **Cost:** Free tier → paid upgrade
- **Latency:** **~0.5-1 second** (fastest)
- **G-code use case:** Real-time validation during operator editing

#### 🟢 **OpenRouter** (Flexible Routing)
- **Free tier:** Per-model limits (100+ models available)
- **Models:** Llama 3.1, Mistral, DeepSeek, and more
- **Setup:** Register at https://openrouter.ai (free tier available)
- **Why:** Unified gateway to swap models via config; no lock-in
- **Cost:** Free tier → usage-based paid
- **Latency:** ~1-3 seconds (variable by selected model)
- **G-code use case:** Cost-conscious operators, model comparison testing

#### 🟡 **DeepSeek** (Reasoning-Focused)
- **Free tier:** Generous usage limits
- **Model:** DeepSeek-V3 (strong reasoning for complex G-code issues)
- **Setup:** Register at https://platform.deepseek.com
- **Why:** Excels at long-context reasoning, great for analyzing complex programs
- **Cost:** Free tier → paid
- **Latency:** ~3-5 seconds
- **G-code use case:** Deep analysis of tool-change sequences, complex modal states

### Tier 2: Subscription Models (Like Codex)

#### 🟡 **Claude Subscription** (Recommended Alternative to Codex)
- **Cost:** $20/mo (Claude.ai Pro)
- **Access:** Browser login or via API
- **Why:** Same reasoning power as Anthropic API, but simpler onboarding
- **Setup:** https://claude.ai → Subscribe → Get API credentials
- **Use case:** Operators who prefer "subscribe once, unlimited use" model
- **Advantage over Codex:** Works globally, no ChatGPT Plus requirement

#### 🟡 **Codex CLI / ChatGPT Plus** (Existing)
- **Cost:** ChatGPT Plus subscription (~$20/mo)
- **Setup:** Requires ChatGPT Plus account + `codex` CLI tool
- **Advantage:** Seamless for existing ChatGPT users
- **Limitation:** Requires separate ChatGPT subscription (not API-based)

---

## Proposed Provider Priority & Fallback Chain

### User Onboarding Flow

```
User starts vibeCNC
    ↓
Config has AI disabled by default
    ↓
User enables AI (checkbox in settings)
    ↓
Provider selection dropdown:
    
    1️⃣ Google Gemini (FREE, recommended)
       └─ No card needed, 1500/day
    
    2️⃣ Groq (FREE, fastest)
       └─ No card needed, ultra-fast inference
    
    3️⃣ OpenRouter (FREE, flexible)
       └─ Many models to choose from
    
    4️⃣ DeepSeek (FREE, reasoning)
       └─ Best for complex analysis
    
    5️⃣ Claude Subscription (PAID, recommended subscription)
       └─ $20/mo, unlimited use
    
    6️⃣ Codex CLI (PAID, subscription)
       └─ ChatGPT Plus login
    
    7️⃣ OpenAI API (PAID, unlimited)
       └─ API key required
    
    8️⃣ Anthropic API (PAID, best reasoning)
       └─ API key required
    
    9️⃣ Ollama (LOCAL, offline)
       └─ ⛔ Blocked on MACH3TURN_XHC_MKX_ET profile
```

### Rate Limit & Fallback Logic

```python
# vibe_cnc/ai_provider_manager.py (new)

PROVIDER_CHAIN = [
    ("google_gemini", 1500),      # 1500 req/day
    ("groq", 14400),              # 14400 req/day
    ("openrouter", 10000),        # varies by model
    ("deepseek", 5000),           # estimate
    ("claude_subscription", None), # subscription-limited
    ("codex_cli", None),          # subscription-limited
    ("openai_api", None),         # pay-as-you-go
    ("anthropic_api", None),      # pay-as-you-go
]

class AIProviderManager:
    def select_best_provider(self, user_preference=None):
        """
        Priority: Free tier first, then paid.
        If user has no preference, cycle through free options.
        """
        if user_preference and user_preference.startswith("free_"):
            return self.init_provider(user_preference)
        
        # Try free providers in order
        for provider_id, rate_limit in PROVIDER_CHAIN[:4]:
            if self.can_use(provider_id):
                return self.init_provider(provider_id)
        
        # Fall back to subscription/paid if available
        for provider_id, _ in PROVIDER_CHAIN[4:]:
            if self.can_use(provider_id):
                return self.init_provider(provider_id)
        
        return None  # No provider available
```

---

## Implementation Plan for V0.3

### V0.3.0 (Baseline - Current Plan, Nov 2026)
- [ ] Refactor `AIClient` into `AIProvider` interface
- [ ] Implement paid providers (Codex CLI, OpenAI, Anthropic)
- [ ] Add Claude Subscription as alternative
- [ ] Add UI provider selector dropdown
- [ ] Test with paid APIs (requires keys in CI secrets)

### V0.3.1 (Free Tier Enhancement, Dec 2026)
- [ ] Implement Google Gemini provider
- [ ] Implement Groq provider
- [ ] Implement OpenRouter provider (gateway abstraction)
- [ ] Implement DeepSeek provider
- [ ] Add rate-limit tracking per provider
- [ ] Add fallback chain logic
- [ ] Create `test_free_ai_providers.py` (verify no card required)
- [ ] Update `config.example.yaml` with all free providers

### V0.3.2 (Polish, Jan 2027)
- [ ] Add provider health check (connectivity test before use)
- [ ] Display provider status in UI (✅ ready / ⏳ rate-limited / ❌ error)
- [ ] Log provider usage statistics
- [ ] Document cost comparison table in README

---

## Configuration Template

```yaml
# config.example.yaml

ai:
  # Safety default: AI disabled until user explicitly chooses provider
  offline: true
  
  # Primary provider selection (user dropdown in UI)
  mode: google_gemini  # or groq, openrouter, deepseek, claude_subscription, codex_cli, openai_api, anthropic_api
  
  # FREE TIER PROVIDERS (No credit card required)
  google_gemini:
    enabled: true
    api_key_env: GOOGLE_API_KEY
    base_url: https://generativelanguage.googleapis.com/v1beta/openai/
    model: gemini-2.0-flash
    rate_limit: 1500  # requests per day
    
  groq:
    enabled: true
    api_key_env: GROQ_API_KEY
    base_url: https://api.groq.com/openai/v1
    model: llama-3.1-70b-versatile
    rate_limit: 14400  # requests per day (240/min)
    
  openrouter:
    enabled: true
    api_key_env: OPENROUTER_API_KEY
    base_url: https://openrouter.ai/api/v1
    # Models automatically detected from free tier list
    free_models:
      - meta-llama/llama-3.1-8b-instruct
      - mistralai/mistral-7b-instruct
      - deepseek/deepseek-chat
    
  deepseek:
    enabled: true
    api_key_env: DEEPSEEK_API_KEY
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    rate_limit: 5000
  
  # SUBSCRIPTION PROVIDERS
  claude_subscription:
    enabled: false
    api_key_env: CLAUDE_SUBSCRIPTION_KEY
    base_url: https://api.anthropic.com/v1/messages
    model: claude-3-5-sonnet-20241022
    # Or use browser login at https://claude.ai
  
  codex_cli:
    enabled: false
    # Uses system `codex` CLI with ChatGPT Plus login
    
  # PAID PROVIDERS (Credit card / API key required)
  anthropic:
    enabled: false
    api_key_env: ANTHROPIC_API_KEY
    base_url: https://api.anthropic.com/v1/messages
    model: claude-3-5-sonnet-20241022
    max_output_tokens: 800
  
  openai:
    enabled: false
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    model: gpt-4-turbo
    max_tokens: 2000
```

---

## Setup Instructions for Users

### Step 1: Enable AI Provider

1. Open vibeCNC settings
2. Check "Enable AI Review & Generation"
3. Select provider from dropdown

### Step 2: Get API Key (Choose One)

#### Option A: Google Gemini (Recommended - FREE)
```bash
# 1. Visit https://makersuite.google.com/app/apikey
# 2. Click "Create API Key"
# 3. Copy key to environment variable

export GOOGLE_API_KEY="your-key-here"
```

#### Option B: Groq (FREE, Fastest)
```bash
# 1. Visit https://console.groq.com/keys
# 2. Create new API key
# 3. Set environment variable

export GROQ_API_KEY="your-key-here"
```

#### Option C: Claude Subscription ($20/mo)
```bash
# 1. Visit https://claude.ai (already subscribed)
# 2. Get API key from settings
# 3. Set environment variable

export CLAUDE_SUBSCRIPTION_KEY="sk-ant-..."
```

#### Option D: OpenRouter (FREE, Flexible)
```bash
# 1. Visit https://openrouter.ai (sign up free)
# 2. API keys section
# 3. Set environment variable

export OPENROUTER_API_KEY="your-key-here"
```

---

## Security Considerations

### API Key Protection

- ✅ Keys read from environment variables only (never config file)
- ✅ No keys committed to git (enforce via `.gitignore`)
- ✅ Sensitive logs filtered before display
- ✅ Keys never passed to safety validator (untrusted code)

### Rate Limiting

- ⚠️ Free tiers have daily limits; graceful degradation when hit
- ⚠️ Show user-friendly message: "Daily limit reached, retry tomorrow or upgrade to paid"
- ✅ Track usage per session
- ✅ Warn operator 10% before limit

### Privacy

- ⚠️ G-code content sent to cloud provider (user aware)
- ✅ No machine I/O, M-code, or physical data leaves vibeCNC
- ✅ Operator can review AI suggestions before applying
- ✅ All AI review/generate MUST pass Safety Validator before export

---

## Cost Comparison (User Reference)

| Scenario | Gemini | Groq | OpenRouter* | Claude Sub | Anthropic | OpenAI |
|---|---|---|---|---|---|---|
| **5 queries/day** | 🟢 FREE | 🟢 FREE | 🟢 FREE | 🟡 $20/mo | 🔴 $0.15/mo | 🔴 $0.15/mo |
| **50 queries/day** | 🟢 FREE | 🟢 FREE | 🟢 FREE | 🟡 $20/mo | 🔴 $1.50/mo | 🔴 $1.50/mo |
| **500 queries/day** | 🟡 $5-10/mo** | 🟢 FREE | 🟡 $10-20/mo | 🟡 $20/mo | 🔴 $15/mo | 🔴 $15/mo |
| **5000+ queries/day** | 🔴 $50/mo | 🔴 $20/mo | 🔴 $50/mo | 🟡 $20/mo | 🔴 $150/mo | 🔴 $150/mo |

*OpenRouter pricing varies by selected model.  
**Gemini has per-minute rate limits; sustained usage requires paid tier.

---

## Testing Strategy

### Unit Tests
```python
# tests/test_free_ai_providers.py

def test_google_gemini_no_card_required():
    """Verify free tier works without credit card."""
    pass

def test_groq_rate_limit_tracking():
    """Verify rate limit is tracked correctly."""
    pass

def test_openrouter_model_fallback():
    """Verify fallback to next free model if primary fails."""
    pass

def test_deepseek_long_context():
    """Verify DeepSeek handles long G-code programs."""
    pass

def test_claude_subscription_works():
    """Verify Claude subscription provider is functional."""
    pass

def test_free_providers_no_local_fallback():
    """Verify production profile never falls back to Ollama."""
    pass
```

### Integration Tests
```python
def test_provider_chain_exhaustion():
    """When all free tiers exhausted, offer paid upgrade."""
    pass

def test_rate_limit_warning_at_80_percent():
    """User sees warning before hitting daily limit."""
    pass

def test_mach3turn_gcode_review_with_free_provider():
    """End-to-end: real G-code → Gemini review → Safety Validator."""
    pass
```

---

## Related Issues & PRs

- PR #1: Mach3Turn implementation tracker (baseline V0.3 plan)
- Issue TBD: "Add free AI provider support" (create this issue once approved)
- Issue TBD: "AI provider selector UI" (depends on above)

---

## Appendix: Free API Comparison Matrix

| Feature | Gemini | Groq | OpenRouter | DeepSeek | Claude Sub | Ollama |
|---|---|---|---|---|---|---|
| Free Tier | ✅ 1500/day | ✅ 14400/day | ✅ Yes | ✅ Yes | ❌ $20/mo | ✅ Unlimited |
| No Card | ✅ | ✅ | ✅ | ✅ | ❌ Card | ✅ |
| Local Only | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Reasoning | ✅✅✅ | ✅ | ✅ | ✅✅✅ | ✅✅✅ | ✅ |
| Speed | ⚡⚡ | ⚡⚡⚡ | ⚡⚡ | ⚡ | ⚡⚡ | Depends |
| Privacy | 🌐 Cloud | 🌐 Cloud | 🌐 Cloud | 🌐 Cloud | 🌐 Cloud | 🔒 Local |
| Mach3Turn Blocked | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ⛔ Policy |

---

## Questions & Feedback

This document is a working draft for V0.3 enhancement. **Feedback welcome:**

- Is this the right provider mix?
- Should DeepSeek be higher priority?
- Should we include free tier limits in the UI prominently?
- Should Claude Subscription be default over Codex?
- Are there other free providers to consider?

Comment in PR #1 or create a GitHub Discussion.
# DocuMind AI — Engineering Checklist

Derived from the Stabilize & Harden sprint, this checklist addresses three specific, project-derived failure modes. Run this checklist before declaring any major feature or sprint "done."

## 1. External API Deprecation
*In Phase 13, a hardcoded model string triggered a fire drill across multiple files when the model was deprecated. The fix (abstracting the model name to `settings.GENERATIVE_MODEL`) had to be built reactively after the incident.*

- [ ] **Are all external model names, endpoints, and API versions abstracted to environment variables or config files?** (No hardcoded strings like `"llama-3.1-8b-instant"` deep in service logic).
- [ ] **Does the service handle upstream API failures gracefully?** (e.g., using a fallback cascade, or returning a degraded health status rather than a hard crash 502 for all users).
- [ ] **Is there a startup smoke-test for critical external dependencies?** (e.g., the `lifespan()` check that pings the generative model and logs a CRITICAL warning if unreachable, allowing the server to start degraded).

## 2. Silent Prod-Only Bugs
*A previous crash-loop occurred when a schema migration was applied to the live Render database but not committed to git. Additionally, the `is_active` security gap left deactivated users with valid JWTs full access to bearer-protected endpoints because the check only lived in the login route.*

- [ ] **Are all database migrations committed to version control *before* or *simultaneously* with applying them to the production database?**
- [ ] **Is the security/authorization check enforced at the centralized dependency level?** (e.g., enforcing `is_active` in `get_current_user()` so that all endpoints receive the protection, rather than solely checking at login).
- [ ] **Does the test suite include negative controls and regression tests for auth/edge cases?** (e.g., IDOR tests across resource endpoints, JTI compare-and-swap reuse tests, and verifying 403 behavior for deactivated accounts).

## 3. Reactive Scope Creep
*The eval harness organically ballooned from 10 to 37 entries without formal review, increasing baseline run costs. Furthermore, there was a repeated pattern of leaving uncommitted WIP sitting in the working tree across parallel agent sessions, leading to lost context and collision risks.*

- [ ] **Are you committing changes incrementally in logical units rather than leaving massive uncommitted working trees?** (Run `git status` as the literal first step of any session).
- [ ] **Has any cost-incurring test or evaluation tool (e.g., the LLM judge baseline) been explicitly scoped before expanding?** (e.g., ensuring `run_eval.py --run` is kept out of standard CI to prevent spiraling API costs on every PR, relying on `--validate-golden` instead).
- [ ] **Are internal admin tools explicitly flagged and segregated?** (e.g., `JULES_ENABLED` flag for the Jules router, ensuring internal API capabilities don't become unintended user-facing attack surfaces).

# AI roadmap

SentinelAPI stays **rule-based by default**. Scans never call a model. Gemini is
on-demand only: the engineer clicks **Explain with AI** or asks a question in
**Ask AI Pentester**. If `GEMINI_API_KEY` is missing, those endpoints return a
clean “AI not configured” message and the rest of the app keeps working offline.

**Live now (Gemini Flash).** Prefers `gemini-1.5-flash`; if Google has retired
that model for the key, the client falls back to the current Flash model.

- **AI remediation / explanation (`LLMRemediationAdvisor`).** `advise(finding)`
  builds a senior-pentester prompt from the stored finding (class, endpoint,
  evidence, severity, business impact) and returns an explanation, concrete
  risk, a short remediation example, and a severity sanity-check.
  `POST /scans/{id}/findings/{finding_key}/explain`.
- **Ask AI Pentester.** `answer(question, findings, chains)` answers a free-form
  question using this scan’s findings and chains only.
  `POST /scans/{id}/ask` with `{ "question": "..." }`.

**Still future stubs (not wired).**

**Smart test-case generation (`LLMTestStrategy`).** Today `ScanEngine` defaults
to `HeuristicStrategy`, which exposes the same targeting rules the detectors
already use (BOLA object-id GETs, anonymous admin probes, login bursts, mass
assignment). `LLMTestStrategy.generate_test_cases(endpoint)` is still a stub
that will later ask a model to read the OpenAPI description and return extra
`TestCase` rows. Plug-in: pass `strategy=LLMTestStrategy()` to `ScanEngine`
instead of the default.

**Agentic multi-step exploitation (`AgenticExploitAgent`).**
`AttackChainBuilder` links known ShopAPI stories (account takeover, cross-user
theft) from vuln class + endpoint. `explore(report)` will later drive further
allow-listed `SafeClient` calls to discover chains the deterministic builder
cannot see. Plug-in: run it after `AttackChainBuilder().build` and append the
returned `AttackChain` list (it is **not** wired today).

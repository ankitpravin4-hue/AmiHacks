# AI roadmap (seams only)

SentinelAPI stays rule-based until an AI phase is explicitly built. These three
typed stubs are the only extension points — no provider SDKs, no API keys, no
network calls.

**Smart test-case generation (`LLMTestStrategy`).** Today `ScanEngine` defaults
to `HeuristicStrategy`, which exposes the same targeting rules the detectors
already use (BOLA object-id GETs, anonymous admin probes, login bursts, mass
assignment). `LLMTestStrategy.generate_test_cases(endpoint)` is a stub that
will later ask a model to read the OpenAPI description and return extra
`TestCase` rows. Plug-in: pass `strategy=LLMTestStrategy()` to `ScanEngine`
instead of the default.

**AI remediation (`LLMRemediationAdvisor`).** Detectors already attach a static
`finding.remediation` string with a small code snippet. `advise(finding)` will
later rewrite that into a richer, context-aware fix using the evidence and
PoC. Plug-in: call the advisor after `SeverityScorer.apply` (it is **not**
wired today).

**Agentic multi-step exploitation (`AgenticExploitAgent`).**
`AttackChainBuilder` links known ShopAPI stories (account takeover, cross-user
theft) from vuln class + endpoint. `explore(report)` will later drive further
allow-listed `SafeClient` calls to discover chains the deterministic builder
cannot see. Plug-in: run it after `AttackChainBuilder().build` and append the
returned `AttackChain` list (it is **not** wired today).

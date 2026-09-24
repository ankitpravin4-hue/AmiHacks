# Architecture

SentinelAPI is a local, allow-listed API vulnerability scanner. ShopAPI is the
only demo target. The rule-based engine is the default; AI modules are typed
stubs and are not on the scan path.

```mermaid
flowchart TB
  ShopAPI["ShopAPI :8000<br/>intentionally vulnerable target"]

  subgraph Core["Scanner Core — sentinel_core"]
    direction TB
    Parser["SpecParser"]
    Ident["Identity matrix<br/>alice / bob / admin / anonymous"]
    Strat["HeuristicStrategy — default"]
    Det["5 detectors<br/>BOLA · excessive data · broken auth<br/>missing rate limit · mass assignment"]
    Scorer["SeverityScorer"]
    Chains["AttackChainBuilder"]
  end

  Store[("SQLite<br/>packages/scanner/data/sentinel.db")]

  subgraph Svc["Scanner Service :8100"]
    REST["REST /scans · replay · diff"]
    WS["WS /scans/id/progress"]
  end

  Dash["Dashboard :5173"]
  CLI["CI/CD CLI — sentinel"]
  GH["GitHub code scanning<br/>SARIF"]

  subgraph Future["Future AI — stubs only, not wired"]
    LLM["LLMTestStrategy"]
    Adv["LLMRemediationAdvisor"]
    Agent["AgenticExploitAgent"]
  end

  ShopAPI -->|"GET /openapi.json"| Parser
  Parser --> Ident
  Ident --> Strat
  Strat --> Det
  Det -->|"SafeClient, allow-list only"| ShopAPI
  Det --> Scorer
  Scorer --> Chains
  Chains --> Store
  Store --> REST
  Store --> WS
  REST --> Dash
  WS --> Dash
  Store --> CLI
  CLI -->|"SARIF"| GH

  LLM -.->|"swap strategy="| Strat
  Adv -.->|"after scoring"| Scorer
  Agent -.->|"after chains"| Chains

  classDef future fill:#0b1018,stroke:#64748b,stroke-dasharray: 5 5,color:#94a3b8
  class LLM,Adv,Agent,Future future
```

The scanner never crawls the open internet. It fetches ShopAPI's OpenAPI spec,
loads the `shopapi` identity preset (alice, bob, admin, anonymous), and the
default `HeuristicStrategy` lists the same probes the five rule-based detectors
already run. Detectors talk to the target only through `SafeClient` (allow-list,
timeouts, rate cap, safe mode). Findings are scored, linked into two attack
chains (account takeover, cross-user data theft), and written to SQLite. The
service on :8100 streams progress over WebSocket and serves REST to the
dashboard and to `sentinel scan`, which can fail a CI job and emit SARIF for
GitHub. The dotted AI boxes are extension points for later — they raise
`NotImplementedError` today and do not change a scan.

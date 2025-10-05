# LicenseIQ — Sprint 0 Plan (10–14 days)

**Suggested window:** Sep 17, 2025 → Sep 30, 2025  
**Goal:** Lock non-functional baselines (SLOs, Security, API v1, DevOps/Observability, Privacy/Residency, i18n), stand up environments and the skeletal repo/CI so MVP sprints can move fast *without rework*.

## Objectives
- **SLOs & Capacity**: p95 rule-eval < 500ms; OCR < 5s; 99.99% uptime; RPO ≤ 1h / RTO ≤ 4h.
- **Security baseline**: OIDC/SAML SSO, MFA, RBAC/ABAC roles, TLS 1.3, encryption at rest (AES‑256), threat model draft.
- **API v1 contract**: OpenAPI for /determine, /rules, /masterdata, /sanctions, /webhooks; versioning, auth, rate limits, error model.
- **DevOps/IaC**: mono-repo skeleton, CI/CD (tests, SAST/DAST), Terraform + K8s manifests, logging/metrics/traces.
- **Privacy & Residency**: data map, minimization, region pinning, retention.
- **i18n/l10n**: string externalization, locale formats, RTL readiness.
- **Plugin/extension**: stub interfaces for custom rules and reports.

## Deliverables (Definition of Done)
1. **Reference Architecture** (diagram + ADRs) checked-in.  
2. **OpenAPI v1** published (HTML + JSON) & mocked endpoints up.  
3. **SSO + RBAC** working in dev; roles documented.  
4. **Environments**: Dev/Stage with CI/CD; trunk-based workflow documented.  
5. **Observability**: logs, metrics, traces visible in dashboards; error budgets defined.  
6. **Security & DR**: secrets mgmt, backup plan; RPO/RTO documented.  
7. **Risk Register & Test Strategy** (incl. load tests & pen test plan).

## Roles & Owners (example)
- **Product/Compliance**: Sprint 0 owner & acceptor
- **Architect**: NFRs, ADRs, API contract
- **Security**: SSO/RBAC, threat model, DR
- **DevOps**: CI/CD, IaC, Observability
- **Frontend/UX**: i18n scaffolding, design tokens
- **Backend**: Mock services, plugin API stubs

## Milestones
- **Day 1–2**: NFR/SLO workshop → sign-off; pick stack; repo & CI bootstrapped.  
- **Day 3–5**: OpenAPI v1 + mocks; SSO + RBAC dev-ready.  
- **Day 6–8**: Observability baseline; IaC for Dev/Stage; DR plan.  
- **Day 9–10**: Threat model; test strategy; Sprint Review + Go/No-Go for MVP.

## Risks & Mitigations
- **Integration churn** → Freeze API v1 before client builds; contract tests in CI.  
- **Perf surprises** → Load targets + JMeter/Gatling in CI, error budgets.  
- **Compliance gaps** → Data map & region pinning during Sprint 0, not after.


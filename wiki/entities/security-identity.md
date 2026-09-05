# Security & Identity (Entity ID: security-identity)

**Boundary Rationale:** This boundary owns authenticated actor context, application access control, secret access, and the technical security mechanisms that surround authority-bearing operations. It is distinct because authentication and application authorization support but do not themselves establish Investment Authority Regime powers.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Human authority boundaries require explicit authenticated actor context. (source: docs/current/platform-architecture-0.2.0.md)
* Authentication, application authorization, and Investment Authority Regime powers remain separate concerns; authenticated identity alone does not establish investment authority. (source: docs/current/platform-architecture-0.2.0.md)
* Secrets are accessed through infrastructure configuration/secret boundaries and must not be embedded in domain records, prompts, reports, logs, or durable decision history. (source: docs/current/platform-architecture-0.2.0.md)
* Untrusted Evidence or model content cannot mutate governing Policy, Formal Constraints, Mandates, or authority rules merely by appearing in text. (source: docs/current/platform-architecture-0.2.0.md)

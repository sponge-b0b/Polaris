# 0006. Typed Internal Contracts and Boundary Serialization

Status: accepted
Date: 2026-07-17

## Context and Problem Statement

Unstructured dictionaries used between services, agents, runtime components, and persistence layers hide schema changes until runtime and make replay, telemetry, attribution, and refactoring inconsistent.

## Decision Outcome

Chosen option: "Typed internal contracts with serialization only at explicit boundaries", because it makes platform schemas discoverable and refactorable while keeping unstructured dictionaries confined to external, persistence, telemetry, event, and presentation boundaries.

Internal platform communication uses strongly typed domain objects, request/result contracts, signals, runtime context, and persistence models. Immutable value objects should use frozen, slotted dataclasses where appropriate. `dict[str, Any]` is limited to untrusted external payloads and explicit serialization boundaries such as HTTP, vendor SDKs, runtime persistence, checkpoints, replay, events, telemetry, and report rendering.

Typed objects retain full numeric precision. Serialization occurs only when crossing a boundary, and deserialization validates before data re-enters the typed platform. Compatibility dictionary adapters are not permanent architecture.

## Rationale

Typed contracts provide discoverable schemas, static validation, IDE support, safer refactoring, deterministic replay, consistent telemetry, and clear ownership of boundary conversion.

## Consequences

- Application services expose typed request and result models.
- Intelligence agents consume and produce typed signals.
- Runtime nodes work with typed objects and serialize only into runtime boundary outputs.
- Presentation layers may round values; application, intelligence, analysis, calibration, and persistence layers preserve full precision.

## Affected Modules

- `application/services/base/service_request.py`
- `application/services/base/service_result.py`
- `application/services/base/service_runner.py`
- `core/runtime/contracts/runtime_node.py`
- `core/runtime/state/runtime_context.py`
- `core/runtime/state/runtime_node_output.py`
- `core/storage/persistence/serializers/`

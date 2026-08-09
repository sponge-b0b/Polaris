# Polaris Domain Context

## Score semantics

Canonical domain score ranges:

- stability: `0.0` to `1.0`, where higher is better
- risk: `0.0` to `1.0`, where higher is worse
- confidence: `0.0` to `1.0`, where higher is more certain

Convert stability to risk explicitly:

```python
risk = 1.0 - stability
```

Do not mix these semantics implicitly.

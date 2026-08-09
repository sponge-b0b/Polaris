• ## Recommendation

  Do not add llm-guard as an in-process dependency for Step 11.

  The toolkit has useful capabilities, especially its model-based prompt-injection scanner, invisible-text detection, secret/PII detection, and malicious-URL scanning. However, integrating the current package directly would
  introduce dependency, runtime, and architectural risks that outweigh the incremental Step 11 benefit.

  The existing native RagSecurityGuard should remain the canonical security boundary. LLM Guard can be reconsidered later as an isolated, optional security-classification service after a benchmark and compatibility evaluation.

  ## What LLM Guard would add

  LLM Guard covers several relevant attack classes:

  - Semantic direct and indirect prompt injection
  - Invisible Unicode characters
  - Secret and PII disclosure
  - Malicious URLs
  - Code, topic, toxicity, and sensitive-output scanning
  - Multiple ordered scanners with fail-fast behavior
  - ONNX execution for lower inference latency

  Its prompt-injection scanner uses a pinned DeBERTa classifier rather than only string patterns. This could detect paraphrased or obfuscated attacks that the deterministic Step 11 patterns may miss. Its documentation explicitly
  identifies retrieved documents and web-browsing content as significant indirect-injection risks for RAG systems. LLM Guard’s RAG guidance (https://protectai.github.io/llm-guard/tutorials/rag/) supports the general design
  already implemented in Step 11: retrieved evidence must be treated as untrusted and inspected before generation.

  ## Why I do not recommend direct integration now

  ### 1. It conflicts with the current dependency graph

  The project currently uses:

  Python >=3.12
  transformers 5.9.0
  tokenizers 0.22.2
  huggingface-hub 1.16.1
  cryptography 46.0.7

  LLM Guard 0.3.16 declares:

  Python >=3.10,<3.13
  transformers ==4.51.3

  A non-mutating uv pip install --dry-run llm-guard==0.3.16 showed that installation would:

  - Download 34 packages
  - Install 34 packages
  - Remove or downgrade 5 existing packages
  - Downgrade transformers from 5.9.0 to 4.51.3
  - Downgrade tokenizers from 0.22.2 to 0.21.4
  - Downgrade huggingface-hub from 1.16.1 to 0.36.2
  - Downgrade cryptography from 46.0.7 to 44.0.3
  - Downgrade regex from 2026.5.9 to 2024.11.6

  That creates unnecessary regression risk for the embedding, reranking, and model infrastructure.

  The package’s Python upper bound would also conflict if this project moves to Python 3.13 while its own project declaration continues to allow newer Python versions.

  ### 2. The scanner API is synchronous

  The prompt-injection scanner exposes a synchronous call:

  sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

  Model loading and classification occur through Transformers. Calling this directly from RagSecurityGuard.inspect_input() or sanitize_contexts() would block the asynchronous workflow execution path.

  We would therefore need one of the following:

  - A dedicated thread pool
  - A process pool
  - A locally hosted LLM Guard API
  - A separately deployed security scanner service

  Adding one of those mechanisms solely for Step 11 would be disproportionate and would complicate deterministic workflow execution, cancellation, telemetry, deployment, and test setup.

  ### 3. The package is operationally heavy

  The base package includes or requires substantial dependencies such as:

  - PyTorch
  - Transformers
  - Presidio
  - spaCy
  - NLTK
  - Faker
  - Detect Secrets
  - Tiktoken

  The project already has PyTorch and Transformers, but the exact-version conflicts prevent straightforward reuse. Several scanners also initialize or download separate Hugging Face models.

  This would increase:

  - Startup time
  - Model warm-up requirements
  - Memory consumption
  - Container size
  - Model-cache management
  - Offline deployment requirements
  - Security model version governance

  LLM Guard recommends ONNX for production CPU inference, but that requires another optional runtime and its own model artifacts. Its published prompt-injection benchmarks show that ordinary CPU inference can add roughly 100–400
  milliseconds or more, depending on the environment. Its optimization guidance (https://protectai.github.io/llm-guard/tutorials/optimization/) also recommends careful scanner selection, fail-fast execution, sampling, and
  asynchronous execution rather than running every scanner synchronously.

  ### 4. The injection classifier is not an absolute security decision-maker

  The LLM Guard documentation says that the DeBERTa v2 prompt-injection classifier is still being tested. It also warns that the scanner is intended for user input rather than system prompts. The classifier returns a
  probabilistic risk score controlled by a configurable threshold.

  This makes it valuable as a secondary signal, but not as the sole fail-closed security authority.

  The current native guard provides:

  - Reproducible decisions
  - Explicit security signals
  - No model dependency
  - No model download
  - No additional service
  - Deterministic replay behavior
  - Predictable failure semantics

  Those characteristics are important for the platform’s runtime-first and replayability requirements.

  ### 5. It would not replace the current controls

  Even if adopted later, LLM Guard should not replace:

  - HTML and executable-markup removal
  - Evidence isolation in JSON
  - Separation of untrusted context from policy instructions
  - Strict structured model responses
  - Fail-closed grounding behavior
  - Existing deterministic high-confidence rules
  - Security telemetry
  - Provenance and citation handling

  A classifier may determine that text is suspicious, but it does not provide the complete RAG trust-boundary architecture already implemented.

  ## Recommended approach

  ### Keep Step 11 as implemented

  Retain RagSecurityGuard as the canonical typed application contract and keep security orchestration outside RagServiceGraph wherever possible. This is especially important because Repowise currently identifies
  rag_service_graph.py as a churn-heavy hotspot with existing complexity in _post_processing_safety.

  ### Add lightweight native controls later where justified

  Some LLM Guard techniques can be implemented without adopting the package:

  - Invisible Unicode/control-character removal using unicodedata
  - Unicode normalization before security inspection
  - Encoded or obfuscated instruction detection
  - URL scheme validation
  - Secret-pattern detection for high-confidence credential formats
  - Context length and segment-count limits
  - Separate raw and sanitized evidence hashes for auditability

  These are deterministic and fit naturally inside the existing typed RagSecurityGuard.

  ### Evaluate LLM Guard separately as a future defense-in-depth service

  If semantic injection detection becomes necessary, evaluate LLM Guard outside Step 11 through a dedicated security-provider boundary:

  RagSecurityGuard
      → PromptInjectionDetectionProvider
          → LLM Guard HTTP service

  It should not be imported directly into the graph or intelligence code. The provider should return a typed result containing:

  @dataclass(frozen=True, slots=True)
  class PromptInjectionAssessment:
      detected: bool
      risk_score: float
      scanner_name: str
      scanner_version: str
      model_name: str
      model_revision: str

  Before production adoption, that evaluation should require:

  - A project-specific financial RAG attack corpus
  - False-positive and false-negative measurements
  - Adversarial Unicode and encoding cases
  - Direct and indirect injection tests
  - CPU/GPU and ONNX latency benchmarks
  - Concurrency and cancellation testing
  - Pinned model revisions
  - Offline artifact availability
  - Service timeout and circuit-breaker behavior
  - Clear fail-open versus fail-closed policy by pipeline stage
  - Full telemetry and trace propagation
  - Replay records containing scanner/model versions and decisions

  ## Final assessment

   Question                                                         Recommendation
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Install llm-guard directly into the Polaris environment?           No
  ───────────────────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────────
   Replace RagSecurityGuard with LLM Guard?                         No
  ───────────────────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────────
   Use its design ideas to improve native controls?                 Yes
  ───────────────────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────────
   Consider its semantic classifier later?                          Yes, as an isolated provider/service
  ───────────────────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────────
   Revise completed Step 11 to depend on it?                        No
  ───────────────────────────────────────────────────────────────  ─────────────────────────────────────────────────────────────────
   Create a separate future security-classifier evaluation plan?    Recommended when semantic detection becomes a demonstrated need

  Because I do not recommend integrating the toolkit into Step 11, I have not produced a revised Step 11 implementation plan or modified the plan file.

  ### Sources

  - LLM Guard repository and scanner catalog (https://github.com/protectai/llm-guard)
  - Prompt Injection scanner documentation (https://protectai.github.io/llm-guard/input_scanners/prompt_injection/)
  - LLM Guard RAG security guidance (https://protectai.github.io/llm-guard/tutorials/rag/)
  - Optimization guidance and ONNX options (https://protectai.github.io/llm-guard/tutorials/optimization/)
  - Production best practices (https://protectai.github.io/llm-guard/get_started/best_practices/)
  - Project dependency declarations (https://github.com/protectai/llm-guard/blob/main/pyproject.toml)
  - LLM Guard changelog (https://protectai.github.io/llm-guard/changelog/)
  
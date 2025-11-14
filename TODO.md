# Hoppy Whisper – Remaining Work

This document aggregates the implementation markdowns (`CODEBASE_ANALYSIS.md`, `SMART_CLEANUP_REMOVAL.md`, historical TODO/status files) and focuses only on what remains to be done. All items that were planned in the original implementation plan have been completed; what follows is a backlog of optional or future improvements drawn from the codebase analysis.

Legend:

- [ ] Not started / backlog
- [~] Under consideration / design choice
- [x] Completed

---

## 1. Audio capture and VAD pipeline

These items come from the “Audio Callback Blocking” and VAD-related notes in `CODEBASE_ANALYSIS.md`. Current behavior is safe enough to ship; these are potential refinements.

- [ ] 1.1 Evaluate moving VAD processing off the PortAudio callback thread.
  - Prototype a queue + worker thread design where `_audio_callback` only enqueues chunks and a background thread runs `_on_audio_chunk`.
  - Measure impact on latency and dropped frames; keep only if it improves real-world behavior.
- [ ] 1.2 Re-review VAD shutdown semantics.
  - Confirm that `_vad_stop_requested` and the guards in `_on_audio_chunk` behave correctly under rapid start/stop and error paths.
  - Consider adding an explicit “shutting down” flag if you observe real races in practice.

---

## 2. Paste robustness

The core paste behavior and timing are now configurable; additional robustness is optional.

- [ ] 2.1 Optional: add retry/backoff for `_perform_paste`.
  - Make the number of retries and base delay configurable in `AppSettings`.
  - On paste failure, log at debug level and retry with exponential backoff up to a small cap (for example, 2–3 attempts).
  - Ensure failures remain non-fatal and do not block the UI.

---

## 3. History export behavior

History export is functional and streaming for TXT; JSON export still materializes the full history in memory.

- [ ] 3.1 Optional: streaming JSON export.
  - Either:
    - Implement a streaming JSON writer (for example, writing one utterance object per line), or
    - Add a clearly documented limit or warning in code and docs that JSON export loads the entire history into memory.
  - Ensure on-disk JSON format remains backward compatible if you keep the current “single array” structure.

---

## 4. Model prefetch and offline readiness

Model prefetch currently runs as a best-effort background optimization.

- [ ] 4.1 Optional: offline-strict “ensure models” mode.
  - Add a setting (for example, `require_models_offline: bool`) that, when enabled, forces `main` to block on `ensure_models()` before accepting hotkey input.
  - On failure in this mode, show a clear error and exit rather than continuing with degraded behavior.
  - Keep the existing background prefetch path as the default behavior.

---

## 5. ONNX Runtime patching strategy

Current approach patches `onnxruntime.InferenceSession` once to inject provider preferences so that `onnx_asr` picks up DirectML/CPU settings.

- [ ] 5.1 Revisit patching if `onnx_asr` evolves.
  - Periodically check whether `onnx_asr` exposes a way to inject a custom session factory or providers.
  - If it does, replace the global `InferenceSession` patch with a local wrapper or factory that avoids changing global ORT state.
  - Keep the existing patch, with documentation, as long as there is no better integration point.

---

## 6. Micro-optimizations and housekeeping

These are low-priority improvements from the “Minor Issues” and “Performance Optimization Opportunities” sections of `CODEBASE_ANALYSIS.md`.

- [ ] 6.1 Shared float32?PCM16 conversion utility.
  - Deduplicate the float32?PCM16 conversion logic between `audio/buffer.py` and `audio/vad.py`.
  - Keep interfaces unchanged; this is strictly a code-health/perf micro-optimization.
- [ ] 6.2 Optional: VAD conversion and buffer copy micro-optimizations.
  - Investigate whether reducing redundant conversions or using vectorized operations meaningfully reduces CPU usage under load.
  - Only keep changes that measurably improve real-world performance without harming readability.

---

## 7. Documentation and tracking

These items keep the markdown set tidy and focused now that the main work is complete.

- [x] 7.1 Retire fully complete status/implementation markdowns in favor of this single backlog.
  - `IMPLEMENTATION_COMPLETE.md` and `IMPLEMENTATION_STATUS.md` have been removed; their content is reflected in `SMART_CLEANUP_REMOVAL.md` and the codebase.
- [ ] 7.2 Keep `SMART_CLEANUP_REMOVAL.md` and `CODEBASE_ANALYSIS.md` up to date.
  - When you implement or explicitly reject any of the backlog items above, update those docs so they continue to match reality.

This file should be the primary reference for remaining work. When all items here are either completed or explicitly dropped, you can archive or delete `TODO.md` as well.

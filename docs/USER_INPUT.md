# User input — durable accepted direction

This file records accepted project direction that should survive chat/session boundaries. It is not a transcript.

## 2026-10-07 bootstrap

- `fellesinnov/Plume` is independent from BOOSTED, but should reuse only the workflow concepts that proved useful there.
- Keep the starter process simple. Avoid importing C++/DAW-specific ceremony that Plume does not need.
- `PLUMES2.0-main/` is the modelling reference archive and **must not be modified** during normal development.
- The archived PLUMES2.0 implementation is the comparison source of truth for model regression work.
- Prefer ChatGPT + sandbox/GitHub CI for Python implementation and deterministic testing.
- Use a local Luna/Windows closer only when evidence specifically requires the archived PLUMES Windows executable or another local-only dependency.
- Maintain durable owners for live work and evidence: backlog, user input, gates, and a build/status log.
- Preserve lessons learned so the Plume workflow can evolve from its own evidence rather than blindly copying BOOSTED.
- The current Python files are prototype/mockup material; future restructuring is allowed. Do not create backward-compatibility obligations merely because the prototype exists.

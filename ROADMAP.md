# Roadmap — MCP 2026-07-28 support

Last updated: 2026-07-29

Tracks the migration to MCP revision `2026-07-28` across the two repositories
that make up this package. Design decisions and the compatibility contract live
in [`docs/design/mcp-2026-migration.md`](docs/design/mcp-2026-migration.md);
this file records **status**.

| Repo | Role | Branch | Head |
| --- | --- | --- | --- |
| `chuk-mcp` | Python facade, typed models, design docs | `rust-backend` | `1dc20e0` |
| `chuk-mcp-rs` | Rust core + PyO3 bindings — all wire behaviour | `mcp-2026` | `4b3c06f` |

**Nothing is merged to `main` in either repo yet.** `chuk-mcp-rs/main` is still
at `f4c2fca`. Every phase below implies a `chuk-mcp-rs` release and wheel before
`chuk-mcp` can pin it (see §6 of the design note).

---

## Status at a glance

| Phase | Scope | State |
| --- | --- | --- |
| 0 | Boundary decisions + compatibility contract | **Done** |
| 1 | Versioning, `ProtocolEra`, error codes, detection, era cache | **Done** |
| 2 | Modern driver, envelope builder, stateless path | **In progress** |
| 3 | Typed results, `resultType`, upward normalisation, `.value` | Not started |
| 4 | MRTR both eras, legacy elicitation bridge | Not started |
| 5 | Catalogue caching, `subscriptions/listen`, tool definitions, auth | Not started |

Core crate: 106 tests, **97.38%** line coverage, every file ≥90% per file.
`cargo fmt`, `cargo clippy --all-targets -- -D warnings` and
`cargo test --workspace` all clean.

---

## Phase 0 — done (`chuk-mcp` `1dc20e0`)

Recorded four decisions:

- **D1** Legacy target is the three versions already supported —
  `2025-06-18`, `2025-03-26`, `2024-11-05`. `2025-11-25` deliberately excluded.
- **D2** The §5 compatibility contract is binding for all of `chuk-mcp` 1.x.
- **D3** Anything touching the wire lives in Rust; Python exposes types.
- **D4** Normalise legacy upward into the modern shape, never downward.

Corrected the inherited contract clause aliasing `ClientSession.initialize()`
to `connect()` — there is no `ClientSession` in this codebase.

## Phase 1 — done (`chuk-mcp-rs` `985ce12`, `68eff8e`)

- `protocol::era` — `ProtocolEra`, `EraMode` (`auto`/`legacy`/`2026-07-28`),
  `ServerProfile`, both detection paths, TTL'd cache keyed on
  `(endpoint, credential context)`.
- `2026-07-28` added to `SUPPORTED_VERSIONS`; `LEGACY_VERSIONS` split out.
- Error codes `-32020`, `-32021`, `-32022`, all marked non-retryable.

Two things worth remembering:

- **`LEGACY_VERSIONS` exists for a reason.** `send_initialize` defaulted to
  `SUPPORTED_VERSIONS` and proposed `[0]`, so adding `2026-07-28` at the front
  would have made every legacy handshake propose a version legacy servers
  reject. `initialize` doesn't exist in the modern era, so reaching it means the
  peer is legacy and only legacy versions belong in the offer.
- **`Detection::Undetermined` exists for a reason.** A binary Modern/Legacy
  would classify a *timeout* as legacy and cache it, pinning an endpoint to the
  wrong era after one network hiccup. `EraCache::record` refuses to store it.

## Phase 2 — in progress (`chuk-mcp-rs` `4b3c06f`)

Done:

- `protocol::meta` — reserved `_meta` keys, `RequestMeta`. Required fields are
  non-optional in the type; optional fields are omitted rather than null.
- `protocol::envelope` — the single place headers and body are produced. Every
  header is derived *from* the params it embeds; `headers_match_body` makes the
  agreement checkable. Base64 sentinel encoding verified against every row of
  the spec's encoding table.
- `ServerProfile::from_discover` corrected to the real `DiscoverResult` schema
  (see Corrections below).
- `server/discover` and `subscriptions/listen` method constants.

Remaining before any modern request can go on the wire:

- [ ] `x-mcp-header` parameter promotion — `Mcp-Param-{Name}` extraction, the
      validation constraints (non-empty, tchar syntax, case-insensitive
      uniqueness, primitive types excluding `number`, statically reachable via
      `properties` chains only), and the rule that a client **MUST** exclude an
      invalid tool definition from `tools/list` rather than failing the whole list.
- [ ] Transport wiring for the stateless path — no `Mcp-Session-Id`, `Accept`
      listing both `application/json` and `text/event-stream`, per-request POST.
- [ ] New-request-ID retry on a broken response stream. `Last-Event-ID`
      resumability is gone; a dropped stream loses the request and it **MUST**
      be re-issued under a new id.
- [ ] Status-aware HTTP detection (see Known gaps).

Gate: no `Mcp-Session-Id` on any modern request; header/body mismatch rejected.

## Phases 3–5 — not started

See §8 of the design note for scope and gates. Conformance CI is wired as a
permanently-red job that goes green through phases 2–4.

---

## Side work — complete, awaiting merge

Both are independent of the migration and mergeable on their own.

| Branch | Head | What |
| --- | --- | --- |
| `deps/pyo3-0.29` | `ea0192f` | PyO3 `0.23 → 0.29`, clears all 6 Dependabot alerts |
| `ci/per-file-coverage-gate` | `75d770c` | Enforces the 90% floor per file, not in aggregate |

**`deps/pyo3-0.29`** closes GHSA-36hh-v3qg-5jq4 (high), GHSA-chgr-c6px-7xpp
(moderate) and GHSA-pph8-gcv7-4qj5 (low) — six alerts that were three
advisories counted across two manifests. Six minor releases of API churn:
`PyObject` removed, `with_gil` → `attach`, `downcast` → `cast`, and
`FromPyObject` for `Clone` pyclasses becoming opt-in (enabled on exactly the
four types Python passes into Rust, a set the compiler identified rather than
guessed). Verified with a maturin wheel running `chuk-mcp`'s Python suite at
563 passed / 1 skipped — identical to the pre-upgrade baseline.

**`ci/per-file-coverage-gate`** replaces `--fail-under-lines 90`, which compared
the crate *total* despite the comment claiming per-file. A new file at 50% passed
as long as the rest carried the average. Enabling real enforcement exposed
`server/session.rs` sitting at exactly 90.00% with zero slack; it is now 100%.

---

## Corrections found along the way

Worth keeping because each was wrong in a way that would have failed silently.

- **`server/discover` result schema.** Phase 1 built `from_discover` on guessed
  field names. The real `DiscoverResult` uses **`supportedVersions`**, not
  `protocolVersions`, and puts identity in
  `_meta["io.modelcontextprotocol/serverInfo"]`, not at the top level — unlike
  the legacy `initialize` result, where `serverInfo` is a sibling of
  `capabilities`. A test now asserts the guessed name does not work.
- **`logging/setLevel` was replaced, not abandoned.** Log level is per-request
  via `io.modelcontextprotocol/logLevel`, and a server **MUST NOT** emit
  `notifications/message` for a request that omitted it — so omitting the field
  silences logging rather than defaulting it.
- **Request-scoped notifications do not travel on `subscriptions/listen`.**
  `notifications/progress` and `notifications/message` flow only on the response
  stream of the request they relate to.
- **`resources/templates/list` is in the `CacheableResult` set** — five methods,
  not four.
- **Resource-not-found moved `-32002` → `-32602`.** Clients **SHOULD** still
  accept `-32002` from earlier servers.
- **`requestState` is the MRTR correlation carrier.**
  `notifications/elicitation/complete` and `elicitationId` are both gone.
- **Roots, Sampling and Logging are Deprecated, not Removed** — the legacy
  driver serves them for the full twelve-month window.

---

## Known gaps and open questions

- [ ] **HTTP era detection is 400-only.** `classify_http_error_body` is
      documented and tested for `400`, but a modern server answers an unknown
      method with `404` + `-32601`, and the HTTP+SSE fallback path also keys off
      `404`/`405`. `-32601` is currently classified as legacy, which is correct
      on a `400` and wrong on a `404`. Needs a status-aware entry point before
      the transport is wired.
- [ ] **Legacy error codes must not be emitted under the modern era.** The spec
      says new implementations **SHOULD NOT** use `-32000`..`-32019` at all, and
      that receivers **MUST NOT** assume meaning for them apart from `-32002`.
      The crate's seven existing MCP codes live there. They are grandfathered
      for *receiving*; the modern driver must not *emit* them.
- [ ] **`CURRENT_VERSION` becomes `2026-07-28`.** Unavoidable and visible.
      `chuk-tool-processor` was checked and does not assert on it. **`mcp-cli`
      and `chuk-llm` still need confirming** before the 1.0 tag.
- [ ] **Conformance suite not yet wired.** Release gate is
      [modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance)
      for `2026-07-28`, alongside the existing legacy tests.
- [ ] **`chuk-mcp-server` needs the mirror-image work.** A dual-era server
      serves both eras from one route; the pushed-elicitation-to-MRTR
      translation runs the opposite direction. The negotiation and envelope code
      is deliberately in the shared core so it is written once.

### Housekeeping

- [ ] **`chuk-mcp-rs` has moved to `IBM/chuk-mcp-rs`.** Pushes still redirect
      from `chrishayuk/chuk-mcp-rs`, but the remote should be updated before
      that stops working.

---

## Verifying locally

```bash
# Rust core (in chuk-mcp-rs)
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

# Per-file coverage (script lives on ci/per-file-coverage-gate)
cargo llvm-cov --package chuk-mcp --ignore-filename-regex 'bin/' \
  --json --output-path coverage.json
python3 scripts/coverage-gate.py coverage.json --min-lines 90

# Python facade against a locally built wheel (in chuk-mcp-rs/crates/chuk-mcp-python)
maturin build --release --out /tmp/wheels
# then, in chuk-mcp, install the wheel plus the pydantic extra and run:
python -m pytest tests -q   # expect 563 passed, 1 skipped
```

Note the Python suite needs `pydantic` installed — without it 22 tests fail on
the optional-dependency path and look like real regressions.

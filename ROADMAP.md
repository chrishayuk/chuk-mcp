# Roadmap — MCP 2026-07-28 support

Last updated: 2026-07-30

Tracks the migration to MCP revision `2026-07-28` across the two repositories
that make up this package. Design decisions and the compatibility contract live
in [`docs/design/mcp-2026-migration.md`](docs/design/mcp-2026-migration.md);
this file records **status**.

| Repo | Role | Branch | Head |
| --- | --- | --- | --- |
| `chuk-mcp` | Python facade, typed models, design docs | `rust-backend` | `1dc20e0` |
| `chuk-mcp-rs` | Rust core + PyO3 bindings — all wire behaviour | `mcp-2026` | `6944157` |

`chuk-mcp-rs/main` is at `7061012` and carries the PyO3 security upgrade and the
per-file coverage gate; `mcp-2026` is merged up to it. The migration branch itself
is not yet merged, and every phase implies a `chuk-mcp-rs` release and wheel
before `chuk-mcp` can pin it (see §6 of the design note).

---

## Status at a glance

| Phase | Scope | State |
| --- | --- | --- |
| 0 | Boundary decisions + compatibility contract | **Done** |
| 1 | Versioning, `ProtocolEra`, error codes, detection, era cache | **Done** |
| 2 | Modern driver, envelope builder, stateless path | **Done** |
| 3 | Typed results, `resultType`, upward normalisation, `.value` | Not started |
| 4 | MRTR both eras, legacy elicitation bridge | Not started |
| 5 | Catalogue caching, `subscriptions/listen`, tool definitions, auth | Not started |

Core crate: 241 tests, **97.56%** line coverage, every file ≥90% per file — now
enforced, not just measured.
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

## Phase 2 — done (`chuk-mcp-rs` `4b3c06f`, `e8ea630`, `4bed6ce`, `06b8543`, `36f9010`)

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
- **Status-aware HTTP era detection.** `classify_http_response` takes the status
  code, because the status changes what the body means: `-32601` on a `400` says
  nothing about era, but on a `404` it means "modern server, no such method",
  while a bare `404` means a legacy server with no modern endpoint. Auth and
  `5xx` statuses are `Undetermined` rather than Legacy, so a sick server is not
  mistaken for an old one and cached as such.
- **Version renegotiation after `-32022`.** `renegotiate` picks a mutually
  supported version from the server's `data.supported`, preferring our own order
  over the server's. Only an empty intersection is fatal.
- `McpError::data()`, so protocol errors' recoverable detail is reachable.

- **`x-mcp-header` promotion** (`protocol::header_params`). Names must be RFC
  9110 `tchar` tokens, which excludes CR/LF by construction so a name cannot
  inject a header break. `number` is refused because its text form is not
  canonical and client and server could disagree on `1.0` versus `1`.
  Annotations reached through `items`, a composition or conditional keyword,
  `$ref` or `$defs` are *rejected rather than ignored* — silently skipping one
  would leave the client sending no header while the server expects one. A
  violation invalidates only that tool, so the caller drops it from
  `tools/list` rather than failing the listing.
- **Stateless transport** (`transports::http_modern`), alongside the frozen
  legacy one. No session id is ever sent, and one supplied in configuration is
  dropped rather than forwarded. `_meta` and mirrored headers are injected by
  the transport, so no caller can omit them. A server's own JSON-RPC error is
  routed through intact rather than flattened into "HTTP 400", so a `-32022`
  still carries the `supported` list `renegotiate` needs.
- **New-request-ID retry.** A dead response stream loses its request and it must
  be re-issued under a *new* id — but the caller is waiting on the id it wrote,
  so the transport keeps the mapping and rewrites the response back. Bounded,
  with the exhausted case reported rather than hung.

Gate met: no `Mcp-Session-Id` on any modern request; header and body agree by
construction; and no server response of any kind causes a hard failure against a
legacy peer. Twelve e2e tests drive a raw-socket server that records what it
actually received, including a stream deliberately closed without a response.

### The dual-era switch (`transports::http_dual`)

Not a pre-flight selector: on HTTP the first real call **is** the probe, so the
transport starts modern with the era unknown and classifies the first response.
A legacy verdict re-sends the request — safe, because every response yielding
that verdict means the server rejected it before processing. The re-send carries
the caller's *original* params, so a legacy server never sees modern `_meta`.

Caching Modern on any answered request would have pinned an endpoint on the
strength of a `401` or a `502`, so `Dispatched` distinguishes a positively
modern answer from one that proves nothing. An unhealthy server is mistaken for
neither era.

### The dual-era switch on stdio (`transports::stdio_dual`)

The easier half: stdio has a legitimate pre-flight, so `server/discover` is
probed once before any real work and detection fails deterministically rather
than half-way through a call.

Era means something different here. On HTTP it selects between transports; on
stdio there is one pipe and era is purely message *shape*. `_meta` injection
therefore lives in the transport's writer task, which is what makes it safe — no
`send_*` helper can omit metadata the modern protocol requires, and none needed
changing. The switch is set before the probe and cleared if the peer turns out
legacy, so a legacy server never receives `_meta`.

A `-32022` during the probe is renegotiated. A process that dies is
`Undetermined`, not legacy: falling back would be a guess that surfaces a
confusing handshake failure instead of the real problem.

## Phases 3–5 — not started

See §8 of the design note for scope and gates. Conformance CI is wired as a
permanently-red job that goes green through phases 2–4.

---

## Side work

| Branch | Head | State |
| --- | --- | --- |
| `deps/pyo3-0.29` | `ea0192f` | **Merged** to `main` as `1df1510`; all 6 alerts now report `fixed` |
| `ci/per-file-coverage-gate` | `75d770c` | **Merged** to `main` as `7061012` |

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

- [x] **Legacy error codes are no longer emitted by new code.** The modern
      driver's own failures now use `-31001`..`-31004`, outside the JSON-RPC
      reserved range, with `is_local_error` / `is_jsonrpc_reserved` to tell them
      from a peer's. This also fixes something subtler than the spec rule: a
      caller could not previously distinguish "the server rejected this" from
      "we never got an answer". A peer's own error still passes through
      untouched. The seven grandfathered MCP codes remain for *receiving*.
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

- [x] **Remotes repointed at the `IBM` org.** Both repos moved
      (`IBM/chuk-mcp`, `IBM/chuk-mcp-rs`); pushes were redirecting from
      `chrishayuk/`. Both `origin` URLs updated and verified.

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

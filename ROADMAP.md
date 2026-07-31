# Roadmap — MCP 2026-07-28 support

Last updated: 2026-07-31 (Phase 4)

Tracks the migration to MCP revision `2026-07-28` across the two repositories
that make up this package. Design decisions and the compatibility contract live
in [`docs/design/mcp-2026-migration.md`](docs/design/mcp-2026-migration.md);
this file records **status**.

| Repo | Role | Branch | Head |
| --- | --- | --- | --- |
| `chuk-mcp` | Python facade, typed models, design docs | `rust-backend` | `8343b5a` |
| `chuk-mcp-rs` | Rust core + PyO3 bindings — all wire behaviour | `mcp-2026` | `694f290` |

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
| 3 | Typed results, `resultType`, upward normalisation, `.value` | **Done** |
| 4 | MRTR both eras, legacy elicitation bridge | **Done** |
| 5 | Catalogue caching, `subscriptions/listen`, tool definitions, auth | Not started |

Phase 5 is genuinely untouched: `SUBSCRIPTIONS_LISTEN` is a method constant and
nothing more, and there is no catalogue caching code at all.

Core crate: 323 tests, **97.32%** line coverage, all 53 files ≥90% per file —
enforced, not just measured.
`cargo fmt`, `cargo clippy --all-targets -- -D warnings` and
`cargo test --workspace` all clean.

---

## Phase 0 — done (`chuk-mcp` `1dc20e0`)

Recorded four decisions:

- **D1** Legacy target is the three versions already supported —
  `2025-06-18`, `2025-03-26`, `2024-11-05`. `2025-11-25` is negotiable but not
  fully implemented (offered so a `2025-11-25`-capable server isn't downgraded;
  driven by the legacy lifecycle, its additive features not consumed — see §4).
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

## Phase 2 — done (`chuk-mcp-rs` `4b3c06f` … `6944157`)

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

### Bounded buffers on the new transports

Both new transports take `TransportLimits` via `start_with_limits`, matching the
legacy transport. The SSE loop checks the bound per chunk and ends the stream
with `LOCAL_MALFORMED_RESPONSE`; non-streaming reads go through
`read_body_bounded` rather than an unbounded `response.text()`.

This came out of a merge, not a review — see Corrections.

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

## Phase 3 — done (`chuk-mcp-rs` `mcp-2026`)

Result types now carry the modern envelope, upward-normalised so 0.9-era caller
code runs unmodified (gate met). Tool results first (the common case):

- `result_type` (`resultType`) — absent on a legacy result, normalised to
  `"complete"` (D4). `.text`/`.content`/`.isError`/`.to_dict()` unchanged.
- `.value` — the flattened 0.9-era accessor: a single structured block's `data`,
  else the list, else the text, else the raw content blocks.
- `structuredContent` and `serverIdentity` getters. `serverIdentity` reads the
  reserved `io.modelcontextprotocol/serverInfo` `_meta` key (self-reported,
  unverified — display/attribution only).

Verified from Python against both eras: a modern structured result flattens
`.value` to its data and surfaces `serverIdentity`, and a real legacy `sqlite`
result normalises `resultType` to `"complete"`.

The same envelope treatment now covers the other result types via a shared
`result_envelope` helper: `ReadResourceResult`, `GetPromptResult` and
`CompletionResult` gain `resultType` normalisation and a `.value` accessor, and
the list results (`ListTools/Resources/Prompts/ResourceTemplatesResult`) capture
`resultType` too. `serverIdentity` is on the tool result (the multi-server
attribution case); extending it to the others is a small follow-up if wanted.

## Phase 4 — done (`chuk-mcp-rs` `6422700` … `98da8d2`)

The revision removed server-initiated requests outright. A server needing
`elicitation/create`, `sampling/createMessage` or `roots/list` answered now
*returns* one as an `input_required` result and expects the whole call retried;
a legacy server pushes a request mid-call and holds the original open. Gate met:
one caller-supplied `InputHandler` answers both, and the same caller code
completes either.

- `protocol::mrtr` — `InputRequired`, the `InputRequests`/`InputResponses` maps,
  and elicitation as *this* revision defines it (`mode`, `requestedSchema`, the
  three-action model, URL mode) — a different shape from the pre-2026 helpers in
  `types::elicitation`, which stay for the Python package.
- `RequestState` has no `Display`, no `Deref`, and a `Debug` that redacts.
  Clients MUST NOT inspect it and it is typically an AEAD blob binding the
  principal; a debug log is exactly where that must not surface.
- Modern driver: answer, then resend under a **new id** with `inputResponses`
  and the exactly-echoed state. Bounded at eight rounds — a server may keep
  asking and nothing else would stop the loop. Stale state from an earlier round
  is dropped when the server stops sending it.
- Legacy bridge: `send_message` dropped inbound server requests at the id
  filter, so a pushed `elicitation/create` left the server waiting forever.
- `AcceptDefaults` answers a form from its schema's own defaults (SEP-1034),
  declines when a required field has none, and never consents to a URL on a
  user's behalf.
- Python: `connect(url, on_elicit=handler)`. The coroutine is started while
  attached and awaited after dropping the GIL — a user may take a long time to
  answer a form, and holding it would stall every other Python thread.

### The bug the in-process tests could not see

The legacy bridge passed over an in-process transport and could never have
fired over real Streamable HTTP: a legacy server pushes on the standalone
server-to-client **`GET`** stream, and that transport only ever spoke on POSTs.
Nothing was listening. Found by instrumenting the conformance runner — across a
whole elicitation scenario exactly two messages reached the client, and the
pushed request was not among them.

`transports::http_listen` now holds that stream open, reconnects on a graceful
close, and stops for good on 404/405/501 while retrying a 503.

Then a second, subtler one: a server can only send a request on a stream that
*exists*, and the client was sending `tools/call` in the gap before the GET was
established — losing a race it did not know it was in, and losing it
consistently. `Transport::ready` makes it explicit; `initialize` awaits it.

## Phase 5 — not started

See §8 of the design note for scope and gates.

The conformance job is **not** the permanently-red job originally planned. It
runs the scenarios that pass as blocking checks and reports the ones that do not
separately, non-blockingly, naming what each needs and telling you if one starts
passing. A red-by-design job would have gone unread for the months phases 4–5
take; a green job with a printed gap list is read every run. The trade is that
nothing forces the gaps closed — see the conformance entry under Known gaps.

## Interlude — developer experience and measurement (`chuk-mcp-rs` `5170155`…`81ce827`)

Not a phase. Four things that were blocking adoption rather than correctness.

**`connect()`.** Connecting meant naming a transport, then choosing between the
legacy handshake and dual-era detection, then wiring the settled connection into
a client — three decisions before the first tool call, and the era one fails at
runtime against half the servers out there. `connect("url or command")` now
picks the transport from the target, detects the era, completes that era's
handshake and returns a ready client; `Connect` is the same with the knobs
exposed. On HTTP the probe is issued deliberately before the caller's traffic,
because the first request *is* the probe and otherwise the caller's first call
discovers the era by accident.

**The client surface is uniform.** `server_info()`, `capabilities()`, `era()`
and `protocol_version()` are all accessors; the fields are private. All four are
decided by the handshake and were never meaningful to assign. `from_profile`
carries era and version through, and `from_settled` is deprecated because a
client built with it reports `era() == None` even though the era is known.
`connect_to_server` is deprecated for going straight to `initialize` without
asking whether the peer is modern.

**Python argument order.** `register_tool`/`register_resource` accept their
arguments in any order. `chuk_mcp` has always put the handler second and the
Rust core puts it last; the three values have disjoint types, so resolving by
kind rather than by position honours both conventions and guesses at nothing.

**Benchmarks.** Micro-benchmarks over the per-message hot paths, and an
end-to-end harness running one workload through three clients against one server
binary. On an M2 Pro, 1000 calls: `rust-native` 55.2 µs/call, `python-bindings`
86.3 µs/call, `pure-python` (0.9.4) 500.6 µs/call — **5.8× more tool calls per
second for a Python caller who changes nothing**. The baseline is pinned to
0.9.4 on purpose; every later release delegates to this core, so anything newer
measures the library against itself.

---

## Exercised from Python (2026-07-30)

The 2026 work is no longer Rust-side-only theory. Built a maturin wheel from
`mcp-2026`, installed it under the `chuk-mcp` (`rust-backend`) facade, and drove
real servers:

- **Legacy path works end-to-end from Python** over both stdio and Streamable
  HTTP — `initialize`, `tools/list`, `tools/call`, session ids.
- **`2026-07-28` verified from Python.** Added `connect_dual_stdio` to the PyO3
  bindings (era-aware: probes `server/discover`, drives the stateless modern
  protocol for a modern peer, falls back to `initialize` for a legacy one). A
  modern stdio server negotiates era `2026-07-28` and a modern `tools/call`
  round-trips. The client exposes `.era` and `.protocol_version`.
- **`2025-11-25` is now negotiable** (see D1): against the reference `mcp` 2.x
  SDK server — whose `initialize` caps at `2025-11-25` on both stdio and HTTP —
  the client now negotiates `2025-11-25` instead of downgrading to `2025-06-18`.

### Modern over HTTP from Python — now works (2026-07-31)

Previously pending: only stdio dual-connect was exposed. `connect()` routes HTTP
through the dual-era transport, so Python reaches the modern era over HTTP too.
Verified against a modern Streamable HTTP server driven from Python:

- era `2026-07-28`, protocol version `2026-07-28`, server identity read from the
  reserved `_meta` key;
- the first request on the wire is `server/discover`;
- `MCP-Protocol-Version` mirrors `_meta`, and **no `Mcp-Session-Id` is sent**;
- all three required `_meta` keys present (`protocolVersion`,
  `clientCapabilities`, `clientInfo`);
- a modern `tools/call` round-trips with `structuredContent` intact.

Still pending: a **modern chuk server** — `CoreServer` has no `server/discover`,
so every modern leg so far has been verified against hand-written modern servers.
This is now the single blocker for both the modern server path and official
server-side conformance. See the `chuk-mcp-server` gap below.

## What's next, in order

Items 2 and 3 of the previous list — Phase 3 typed results, and wiring the
official conformance suite — are both done. That leaves one thing gating
everything downstream, and then the work that unblocks conformance.

1. **Merge `mcp-2026` and ship a `chuk-mcp-rs` wheel.** Still the gate: the
   wheel is what lets `chuk-mcp` pin the core and downstream consumers see any
   of this. The branch has grown considerably — the whole 2026 protocol path,
   MRTR in both eras, both conformance suites, `connect()`, and the benchmarks —
   so the merge is larger than it was, but it is also far better exercised: the
   modern era round-trips from Python over both stdio and HTTP, and elicitation
   is answered from Python in either era.
2. **A modern `CoreServer`.** `server/discover`, the stateless request path, and
   an HTTP serving mode. This one item unblocks three separate things: the
   modern server leg, the official suite's server scenarios (which need a
   `--url`), and the modern-server column that the in-repo matrix currently
   shows as empty.
3. **Phase 5** — catalogue caching, `subscriptions/listen`, full tool
   definitions, auth hardening. Gate: private-cache isolation across two
   principals.

Before the 1.0 tag: confirm `mcp-cli` and `chuk-llm` do not assert on
`CURRENT_VERSION`, which is already `2026-07-28` in the core.

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

- **An unbounded SSE buffer, found by a merge rather than a review.** Merging
  `main` produced a *semantic* conflict git could not see: `send_via_http` had
  gained a `max_buffer_size`, and the reason it had applied equally to the new
  code — the modern transport's SSE loop accumulated into an unbounded `String`,
  so a peer that simply withholds the event boundary could grow it until the
  process died. The text merged cleanly and said nothing. Worth remembering that
  a clean merge of a security fix does not mean the fix reached new code written
  in parallel.
- **A `401` was proof of nothing, and was being read as proof of everything.**
  The first draft of the dual-era HTTP switch cached `Modern` on any answered
  request, so an auth failure or a `502` would pin an endpoint on the strength of
  an error that says nothing about the protocol. Caught by writing the test, not
  by reading the code.
- **Coverage can fall silently.** After the buffer work `http_modern.rs` dropped
  to 91.86% and still passed, because the aggregate gate was what `main` had at
  the time. The per-file gate is now merged, which is the point of it.
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
- [~] **Conformance — two suites now, both blocking in CI.**

      *Official.* The [modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance)
      (`0.1.16`) **client** scenarios run against the
      `chuk-mcp-conformance-client` runner: `initialize` and `tools_call` pass
      at both `2025-06-18` and `2025-11-25` (the suite independently confirms
      the client negotiates `2025-11-25`).

      *In-repo.* Because the official suite cannot reach the modern era (its
      draft client scenarios are auth-only) or our server (it drives servers
      over `--url`), spec requirements are also expressed as data and run
      against this client and this server in both eras — 31 rules, all holding:

      | Era | Subject | Rules |
      | --- | --- | --- |
      | legacy | client | 6 |
      | `2026-07-28` | client | 9 |
      | legacy | server | 10 |
      | both | protocol | 6 |

      There are deliberately **no modern-server rules**. An unimplemented era
      belongs in the matrix as an absence rather than hidden behind rules nobody
      wrote, so the empty column is the honest signal that item 2 of *What's
      next* has not happened.

      Blocking now: `initialize` and `tools_call` at both versions, plus
      **`elicitation-sep1034-client-defaults`** at `2025-11-25`, which Phase 4
      fixed.

      **`sse-retry`** passes too, so the known-gaps list is now empty: every
      client scenario the suite offers at a version we support passes. It was
      one missing idea rather than three — a server may answer a POST by
      opening a stream, sending an event id and a retry delay, then closing it
      *without the response*, which asks to be resumed on the GET stream rather
      than reporting a failure. Two details each cost a check: the delay must be
      read **after** a stream ends (the `retry:` governing a reconnection
      arrives on the stream that just closed), and the listener must race its
      open stream against a resume request, or a server holding the GET open
      while a POST stream dies is never reconnected.

      **Server** scenarios still need the modern chuk server and an HTTP
      serving mode; the `draft` (`2026-07-28`) client scenarios remain auth-only
      (Phase 5).

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

# Per-file coverage (enforced in CI; script on main)
cargo llvm-cov --package chuk-mcp --ignore-filename-regex 'bin/' \
  --json --output-path coverage.json
python3 scripts/coverage-gate.py coverage.json --min-lines 90

# Python facade against a locally built wheel (in chuk-mcp-rs/crates/chuk-mcp-python)
maturin build --release --out /tmp/wheels
# then, in chuk-mcp, install the wheel plus the pydantic extra and run:
python -m pytest tests -q   # expect 563 passed, 1 skipped

# Conformance — in-repo rule suite, then the official client scenarios
./scripts/run-conformance.sh
./scripts/run-conformance.sh --gaps   # also re-check the known gaps

# Benchmarks
cargo bench -p chuk-mcp     # per-message protocol costs
python3 -m benchmarks       # end-to-end: Rust vs PyO3 vs pure Python
```

Note the Python suite needs `pydantic` installed — without it 22 tests fail on
the optional-dependency path and look like real regressions.

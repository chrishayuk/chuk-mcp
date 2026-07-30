# MCP 2026-07-28 migration — boundary decisions and compatibility contract

Status: **accepted** (Phase 0)
Date: 2026-07-29
Applies to: `chuk-mcp` (Python) and `chuk-mcp-rs` (Rust core + PyO3 bindings)

This is the document Phase 1 codes against. Nothing here is implementation; it
records the decisions that would otherwise be made ad hoc and inconsistently
across two repositories.

---

## 1. Decisions recorded

**D1 — Legacy target is every version `chuk-mcp` supports today**: `2025-06-18`,
`2025-03-26`, `2024-11-05`. All three keep working unchanged and `2026-07-28` is
added alongside them. `2025-11-25` is **negotiable but not fully implemented** —
it is offered so a `2025-11-25`-capable server negotiates to it instead of being
downgraded, but it is driven by the legacy lifecycle and its net-new features are
not consumed — see §4.

**D2 — The downstream compatibility contract in §5 is binding** for the whole
`1.x` line of `chuk-mcp`.

**D3 — Everything that touches the wire lives in Rust.** See §3.

**D4 — Normalisation is upward-only.** Legacy responses are normalised into the
2026 shape. The 2026 shape is never degraded into the legacy shape. Era never
appears in a public type.

---

## 2. What changed since the analysis was written

The analysis this plan derives from assumed a pure-Python `chuk-mcp` with a
driver layer that new code could sit beside. That codebase no longer exists.
The `rust-backend` branch deleted ~23k lines of Python:

| | Before | Now |
|---|---|---|
| Transports, client, server, `send_*` | Python, in this repo | Rust, in `chuk-mcp-rs` |
| `src/chuk_mcp` | ~28k lines | ~4.9k lines |
| `_rust.py` | — | flat alias table over the `chuk_mcp_rs` PyO3 extension |
| Release | one repo | two repos: crates.io + PyPI wheel, then a pin here |

Consequence: there is no Python driver layer to extend. Every P0 item is a
two-repo coordinated ship. §6 covers the mechanics.

---

## 3. Boundary: which side of PyO3 each component lands on

Rule: **anything that touches the wire is Rust; anything a caller names is
exposed through Python.**

### Rust (`crates/chuk-mcp`)

| Component | Notes |
|---|---|
| Version registry | `protocol::versioning` — `SUPPORTED_VERSIONS` gains `2026-07-28`, `LEGACY_VERSIONS` split out |
| `ProtocolEra` + configured mode | `protocol::era` — `auto` (default) / `legacy` / `2026-07-28` |
| Era detection state machine | `protocol::era::detect` — two *separate* paths, see §7 |
| Era cache | `protocol::era::cache` — keyed `(endpoint, credential context)`, TTL'd |
| Envelope builder | `protocol::envelope` + `protocol::meta` — `_meta` and every mirrored header from **one** function; `protocol::header_params` for `x-mcp-header` |
| Modern driver | `transports::http_modern`; `transports::http_dual` selects between eras |
| Legacy driver | `transports::http` — frozen; `Mcp-Session-Id`, `initialize`, `ping` |
| ResultNormaliser | Upward-only (D4) |
| MRTR mechanics | Including the legacy pushed-`elicitation/create` bridge |
| Catalogue cache | `ttlMs` / `cacheScope`, keyed by principal |
| `subscriptions/listen` | One stream per server, opt-in per type |
| Error codes | `-32020`, `-32021`, `-32022`; `-32002` → `-32602` |

Putting the normaliser and negotiator in Rust rather than in Python means the
Rust-native client, the Python client, and any future Rust-backed
`chuk-mcp-server` share one implementation. This is the same argument the
analysis made for putting it in `chuk-mcp` rather than in `chuk-tool-processor`
— it just moves one layer further down.

### Python (`src/chuk_mcp`)

| Component | Notes |
|---|---|
| Typed result models | Re-exported from Rust structs; `MCPExecutionResult` and friends |
| Typed exceptions | Re-exported PyO3 exception classes |
| Era config plumbing | Keyword args on parameter objects → Rust |
| Pure-data model layer | `JSONRPCMessage`, `MessageMethod`, capabilities/info — unchanged |

`chuk-mcp` stays a thin, typed, documented facade. No protocol logic returns to
Python.

---

## 4. Legacy surface

The Rust core declares:

```rust
// crates/chuk-mcp/src/protocol/versioning.rs:6
pub const SUPPORTED_VERSIONS: &[&str] = &["2025-06-18", "2025-03-26", "2024-11-05"];
```

Phase 1 makes this:

```rust
pub const SUPPORTED_VERSIONS: &[&str] =
    &["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"];
```

`2025-11-25` is **negotiable but not fully implemented**. It is offered by the
legacy `initialize` handshake (`LEGACY_VERSIONS`) and driven by the legacy
stateful lifecycle. We do **not** implement its net-new additive features —
icons metadata, reworked `ElicitResult`/`EnumSchema`, URL-mode elicitation, OIDC
discovery, incremental scope consent, RFC 9728 alignment, JSON Schema 2020-12 —
which stay out of the driver we intend to freeze.

Why negotiate it at all: without it, a server whose newest legacy revision is
`2025-11-25` (notably the reference `mcp` 2.x SDK, whose `initialize` caps at
`2025-11-25`) negotiates **down** to `2025-06-18` — a needless downgrade against
a perfectly capable modern server. Offering `2025-11-25` lets the handshake meet
at the server's actual best legacy version. Its additive features being wire-
compatible optionals, ignoring them is safe: tools, resources, and prompts work
unchanged. What we give up is only the ability to *claim* full `2025-11-25`
conformance or to consume those additive features.

Consequences:

- The conformance gate is `2026-07-28` only, alongside the existing legacy tests.
- The legacy driver is frozen for *features*: `2025-11-25` is negotiated and
  handled with the shared legacy lifecycle, with no revision-specific feature
  work; the whole legacy driver is deleted when the twelve-month deprecation
  window closes.

---

## 5. Backwards-compatibility contract

Binding for all of `chuk-mcp` `1.x`.

### 5.1 Correction to the inherited contract

The inherited contract says *"`ClientSession.initialize()` survives as an alias
for `connect()`"*. **There is no `ClientSession` in this codebase** and there
never was in the Rust-backed release. That clause is unimplementable as
written. The actual surface is:

- High-level: `connect_to_server()` → `MCPClient` with `call_tool`,
  `list_tools`, `list_resources`, `read_resource`, `list_prompts`,
  `get_prompt`, `ping`, `capabilities`, `server_info`, `close`
- Low-level: `stdio_client()` / `StreamableHTTPTransport` + the `send_*` family

`connect_to_server()` is already the connect verb. No alias is required.

### 5.2 Guarantees

1. **Every symbol in `chuk_mcp.__all__` keeps working**, under every era, for
   the whole `1.x` line. Where the 2026 wire protocol removed the underlying
   operation, the binding is emulated — see 5.3.
2. **`ToolResult.text`, `.content`, `.isError`, `.to_dict()` keep their current
   semantics.** New fields (`resultType`, `structuredContent`, `_meta`,
   `server_identity`) are additive. A legacy result with no `resultType`
   normalises to `"complete"`.
3. **`.value` is added** to result types as the flattened 0.9-era accessor.
4. **Default era is `auto`.** No existing configuration becomes invalid.
5. **Legacy-only servers work with zero configuration** until the twelve-month
   deprecation window closes (no earlier than 2027-07-28).
6. **`chuk-tool-processor` upgrades with a version bump and nothing else.** It
   adopts the new result types at its own pace.

### 5.3 Removed-in-2026 operations: what the binding does

Each of these is public today and names an operation the 2026 revision removed.
Under `era=legacy` all behave exactly as they do now.

| Symbol | Under `era=2026-07-28` |
|---|---|
| `send_initialize` | No `initialize` on the wire. Calls `server/discover` and returns an `InitializeResult` synthesised from the response. `protocolVersion`, `capabilities`, `serverInfo` all populate; `instructions` is `None` unless the server supplies it. |
| `send_initialized_notification` | No-op, returns successfully. |
| `send_ping` / `MCPClient.ping()` | Maps to `server/discover` — a cheap RPC every server MUST implement — and returns `True` on success. This is an honest liveness check, not a stub. |
| `send_resources_subscribe` / `_unsubscribe` | Translated to a `subscriptions/listen` opt-in / opt-out for `resourceSubscriptions`. |
| `send_roots_list` | Roots is *deprecated, not removed*. Works during the window. |
| `send_roots_list_changed_notification` | Removed outright in 2026. No-op under the modern era; warns once. |
| `StreamableHTTPTransport.get_session_id()` | Returns `None`. There are no protocol sessions. |

### 5.4 The one unavoidable behaviour change

`CURRENT_VERSION` becomes `"2026-07-28"` and `supported_versions()` grows. Any
caller asserting equality against `"2025-06-18"` sees a change. This cannot be
avoided while also advertising 2026 support — it is the value's entire purpose.

`chuk-tool-processor` was checked and does not assert on it. It does hardcode
`"protocolVersion": "2024-11-05"` at `mcp/transport/sse_transport.py:196`, but
that is the deprecated HTTP+SSE path and is unaffected. Flagged here for
`mcp-cli` and `chuk-llm` to confirm before the `1.0` tag.

---

## 6. Release mechanics

Every wire-affecting change ships in this order:

1. `chuk-mcp-rs`: land in `crates/chuk-mcp`, expose via `crates/chuk-mcp-python`
2. Tag → crates.io + PyPI wheel (PyPI publish is currently behind a manual
   opt-in in that repo's release workflow)
3. `chuk-mcp`: raise the `chuk-mcp-rs>=` floor in `pyproject.toml`, re-export
   new symbols from `_rust.py`, ship

`chuk-mcp` cannot ship a protocol change ahead of a wheel. Phase gates below
are defined on the `chuk-mcp` side, so each implies its wheel has shipped.

---

## 7. Detection, restated precisely

The two transports do **not** share an algorithm. The spec is explicit that
`server/discover` is a backward-compatibility probe *on stdio*.

**stdio** — probe with `server/discover`. Any error that is not a recognised
modern error means legacy; fall back to `initialize`.

**Streamable HTTP** — never probe. Issue the first real request in modern form
and classify the response. The **status code changes what the body means**, so
classifying on the body alone gets legacy servers wrong:

| Response | Verdict |
| --- | --- |
| `2xx` | modern |
| `400` carrying a recognised modern error | modern |
| `400` otherwise | legacy — re-send under the legacy driver |
| `404`/`405` with a JSON-RPC error body | modern (unknown method on a modern endpoint) |
| `404`/`405` with a bare or non-JSON body | legacy — nothing modern is hosted here |
| anything else (`401`, `429`, `5xx`) | **undetermined** |

`-32601` shows why the status matters: on a `400` it says nothing about era, but
on a `404` it is a modern server reporting an unknown method — the same body,
the opposite conclusion. The first real call *is* the probe, so HTTP never pays
a round trip for detection.

Two rules keep detection honest in both directions:

- An **undetermined** verdict is never cached and never read as legacy. A server
  that is unhealthy or wants credentials has not said which protocol it speaks.
- An *answered* request only proves a **modern** peer when the answer is a
  success or a recognised modern error. Treating any answered request as proof
  would pin an endpoint on the strength of a `401`.

Re-sending after a legacy verdict is safe rather than a double-execution risk:
every response that yields it means the request was rejected *before* the server
processed it. The re-send carries the caller's original params, not the modern
envelope, so a legacy server never sees `_meta` it would reject.

Recognised modern errors: `-32022` `UnsupportedProtocolVersion`, `-32020`
`HeaderMismatch`, `-32021` `MissingRequiredClientCapability`.

Era is a property of `(endpoint, credential context)` — not of the client and
not of the transport. Cached with a TTL and invalidated on any `-32022`, because
a server can be upgraded underneath a running client.

---

## 8. Phases and gates

| Phase | Scope | Gate |
|---|---|---|
| 0 | This document | Accepted |
| 1 | Versioning, `ProtocolEra`, error codes, detection state machine, era cache | Detection unit tests on both paths; pinning honoured |
| 2 | Modern driver, envelope builder, stateless path, new-ID stream retry | No `Mcp-Session-Id` on any modern request; header/body mismatch rejected |
| 3 | Typed results, `resultType`, upward normalisation, `.value` | 0.9-era caller code runs unmodified |
| 4 | MRTR both eras, legacy elicitation bridge, `requestState` correlation | Identical caller code drives both eras |
| 5 | Catalogue caching, `subscriptions/listen`, full tool definitions, auth hardening | Private-cache isolation across two principals |

Conformance CI is wired in Phase 1a as a permanently-red job that goes green
through 2–4. It is not a phase of its own.

### Spec details that are easy to get wrong

- `logging/setLevel` is removed but **replaced, not abandoned** — log level is
  per-request via `io.modelcontextprotocol/logLevel` in `_meta`, and servers
  MUST NOT emit `notifications/message` for requests that omitted it.
- **Request-scoped notifications do not travel on `subscriptions/listen`.**
  `notifications/progress` and `notifications/message` stay on the response
  stream of the request they belong to.
- `resources/templates/list` is in the `CacheableResult` set — **five** methods.
- Resource-not-found moved `-32002` → `-32602`.
- `requestState` is the MRTR correlation carrier; `notifications/elicitation/complete`
  and `elicitationId` are both gone.
- Roots, Sampling and Logging are **Deprecated, not Removed** — the legacy
  driver still serves them for the full window.
- `Mcp-Session-Id` is applied unconditionally today at
  `crates/chuk-mcp/src/transports/http.rs:168-169`. The assertion that it never
  appears on a modern request is a Rust-side test.
</content>
</invoke>

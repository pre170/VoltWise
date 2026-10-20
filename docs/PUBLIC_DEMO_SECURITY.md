# Public demo security

VoltWise uses a deliberately small access boundary for a controlled hackathon
demo. It is not a multi-user identity system.

## Route inventory

| Route | Effect and exposure |
| --- | --- |
| `/` and static assets | Read the compiled judge UI. The browser then calls the same-origin API. |
| `/health` | Anonymous, side-effect-free process liveness. It does not query SQLite or MCP. |
| `/api/health` | Read application mode and service status. |
| `/api/household/overview`, `/api/devices`, `/api/devices/{id}` | Read simulated household/device state. |
| `/api/devices/{id}/turn-on-and-verify` | Mutates simulated device state and writes audit events without using the browser MCP gateway. |
| `/api/devices/{id}/diagnose` | Runs verification/recovery, mutates simulated device state, and writes audit events without using the browser MCP gateway. |
| `/api/energy/*` | Reads deterministic energy results; comparison and explanation calls also append audit events. |
| `/api/tariff/*` | Reads deterministic tariff results or recommendations; calls also append audit events. |
| `/api/demo/state` | Reads the global selected scenario and heater fault. |
| `/api/demo/reset` | Resets global demo/device state and appends a reset event while preserving history. |
| `/api/demo/energy-scenario`, `/api/demo/device-fault` | Mutate the global deterministic demo selection. |
| `/api/sim/chat` | Routes a bounded utterance through the official MCP client and `/mcp`; it can invoke any routed tool and writes a real MCP trace. |
| `/api/events` | Reads persisted application audit history. |
| `/api/sim/traces` | Reads private MCP request evidence, arguments, outcomes, timing, and safe error type. |
| `/mcp` | Real MCP Streamable HTTP initialization, discovery, and tool invocation. Several tools mutate simulated devices or append history. |
| `/docs`, `/redoc`, `/openapi.json` | Reveal the REST surface and schemas when enabled for local development. |

## Access strategy

Local development is unchanged: `VOLTWISE_PUBLIC_DEMO` defaults to `false`,
the UI and REST API have no Basic challenge, API documentation remains enabled,
and the MCP bearer token remains optional.

For a public deployment, set `VOLTWISE_PUBLIC_DEMO=true`. Startup then fails
closed unless all three server-side values are supplied:

- `VOLTWISE_DEMO_USERNAME`
- `VOLTWISE_DEMO_PASSWORD`
- `VOLTWISE_MCP_BEARER_TOKEN`

In this mode:

- `/health` remains anonymous for load-balancer health checks.
- The UI, static assets, every REST route, and history endpoints require HTTP
  Basic authentication. Browsers manage the credentials; they are not embedded
  in the frontend bundle or placed in JavaScript configuration.
- `/docs`, `/redoc`, and `/openapi.json` are disabled and return 404 after
  authentication.
- `/mcp` does not accept the judge's Basic credential. It requires the separate
  MCP bearer token. The server-side `SimulatorGateway` supplies that token to
  its official MCP client, preserving the real Streamable HTTP hop.
- REST bodies default to 64 KiB, REST processing defaults to a 12-second
  timeout, and one-process fixed-window limits default to 120 read requests and
  30 mutation requests per client IP per minute. Rejections are structured
  413, 504, or 429 responses.

Basic credentials and bearer tokens must be injected at runtime, never built
into the image or committed to an environment file. HTTP Basic is safe only
behind HTTPS. Configure the TLS ingress to expose the single application origin
and keep port 8080 private.

The application rate limiter relies on the ASGI client address after Uvicorn's
trusted-proxy processing. Set `VOLTWISE_FORWARDED_ALLOW_IPS` to only the real
ingress proxy addresses. If it is wrong, clients may share one rate bucket or a
spoofed forwarded address may be trusted. Edge request and connection limits
remain recommended, especially for `/mcp`, which has a separate request-body
limit but no application-level request-rate limiter.

## Shared judge state

The demo has one global scenario, fault selection, simulated device state, and
SQLite audit stream. Authentication controls who can access it; it does not
isolate one authenticated judge from another. Concurrent resets can invalidate
an active walkthrough, and concurrent heater commands can interleave simulator
retry state.

For the single-instance hackathon deployment:

1. Admit one active judge/demo operator at a time.
2. Run **Reset demo** immediately before each walkthrough.
3. Avoid sharing the credential beyond the judging group and rotate it if it is
   disclosed.
4. Keep one worker and one application instance.
5. Monitor failed authentication, 429, 503, and application-error logs without
   logging Authorization headers.

Per-browser isolated state would require session-scoped application containers,
repository partitioning, MCP routing context, reset semantics, and cleanup. That
is a significant architecture change and is intentionally not implemented.

## Residual risks

- HTTP Basic is a shared gate, not per-user identity, revocation, or audit.
- Any authenticated judge can reset the demo, select faults, invoke simulator
  commands, and call direct domain REST operations.
- In-memory rate limits reset with the process and do not coordinate replicas.
- The timeout cannot guarantee cancellation of already-running synchronous
  thread work, though the MCP client has its own shorter timeout.
- SQLite and mutable simulator state remain single-instance concerns.
- `/health` confirms only that the process can answer HTTP.
- Credential stuffing, volumetric denial of service, and connection limits must
  be handled by the HTTPS ingress or another trusted edge control.

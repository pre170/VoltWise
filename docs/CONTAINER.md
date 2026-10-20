# Container packaging

VoltWise is packaged as one production-like ASGI service. One Uvicorn worker
serves the compiled React application, FastAPI routes, and the official MCP
SDK's Streamable HTTP application. This is deployment packaging only; it does
not deploy AWS resources.

## Build and run

```powershell
docker build -t voltwise .
docker run --rm --name voltwise -p 8080:8080 -v voltwise-data:/data voltwise
```

Routes on the single public port:

- `/` and client-side paths: frozen React production build
- `/api/...`: FastAPI and simulator gateway
- `/mcp`: real MCP Streamable HTTP transport
- `/health`: lightweight process liveness
- `/docs`: OpenAPI UI

The browser uses same-origin `/api` URLs in a production build. Local Vite
development retains `http://127.0.0.1:8000` as its default API URL.

## Runtime configuration

| Variable | Container default | Purpose |
| --- | --- | --- |
| `PORT` | `8080` | Single HTTP listen port. |
| `VOLTWISE_HOST` | `0.0.0.0` | Uvicorn bind address. |
| `VOLTWISE_STATIC_DIR` | `/app/frontend/dist` | Compiled frontend directory containing `index.html`. |
| `VOLTWISE_MODE` | `SIMULATION` | Only `SIMULATION` is implemented; do not set `PRODUCTION`. |
| `VOLTWISE_DB_PATH` | `/data/voltwise.db` | SQLite runtime state and trace path. |
| `VOLTWISE_MCP_URL` | `http://127.0.0.1:$PORT/mcp` | Gateway target; normally leave unset in the combined container. |
| `VOLTWISE_MCP_PATH` | `/mcp` | Public/internal MCP path. |
| `VOLTWISE_MCP_HOST` | `127.0.0.1` | SDK transport-security host setting; it does not change the combined public listener. |
| `VOLTWISE_MCP_PORT` | `8000` | Standalone MCP launcher port; unused as a listener by the combined host. |
| `VOLTWISE_MCP_ALLOWED_HOSTS` | local hosts only | MCP DNS-rebinding allowlist. Add the exact deployment host later. |
| `VOLTWISE_MCP_ALLOWED_ORIGINS` | local origins only | Allowed browser origins for direct MCP requests. |
| `VOLTWISE_MCP_BEARER_TOKEN` | unset | Optional MCP bearer protection; the internal gateway sends the same value. |
| `VOLTWISE_MCP_MAX_REQUEST_BODY_SIZE` | `1048576` | MCP request-body limit in bytes. |
| `VOLTWISE_MCP_CLIENT_TIMEOUT_SECONDS` | `8` | Gateway timeout for the loopback MCP operation. |
| `VOLTWISE_CORS_ORIGINS` | local Vite origins | API CORS allowlist. Same-origin container requests need no CORS grant. |
| `VOLTWISE_FORWARDED_ALLOW_IPS` | `127.0.0.1` | Trusted reverse-proxy IPs for forwarded headers. |
| `VOLTWISE_LOG_LEVEL` | `info` | Uvicorn log level. |
| `VOLTWISE_PUBLIC_DEMO` | `false` | Enable the public-demo security boundary. Local development remains unchanged when false. |
| `VOLTWISE_DEMO_USERNAME` | unset | Shared browser HTTP Basic username; required in public-demo mode. |
| `VOLTWISE_DEMO_PASSWORD` | unset | Shared browser HTTP Basic password; required in public-demo mode. |
| `VOLTWISE_REST_MAX_REQUEST_BODY_SIZE` | `65536` | Maximum REST request body in bytes in public-demo mode. |
| `VOLTWISE_REST_REQUEST_TIMEOUT_SECONDS` | `12` | REST response timeout in public-demo mode. |
| `VOLTWISE_REST_RATE_LIMIT_PER_MINUTE` | `120` | Per-client read limit for this one process. |
| `VOLTWISE_REST_MUTATION_RATE_LIMIT_PER_MINUTE` | `30` | Per-client non-read limit for this one process. |

Do not bake bearer tokens or cloud credentials into the image. A later AWS
deployment must inject configuration at runtime and use IAM roles rather than
static AWS credentials.

Set `VOLTWISE_PUBLIC_DEMO=true` before any public exposure. The process then
fails startup unless browser Basic credentials and a distinct MCP bearer token
are present. Supply them through runtime secret injection, not Docker build
arguments or frontend environment variables. See
[Public demo security](PUBLIC_DEMO_SECURITY.md) for the route inventory,
controls, and residual risks.

## MCP architecture boundary

The one-process layout does not shortcut MCP:

```text
Browser
  -> POST /api/sim/chat
  -> SimulatorGateway
  -> official MCP ClientSession
  -> loopback HTTP /mcp
  -> SDK Streamable HTTP session manager
  -> VoltWise MCP tool
  -> deterministic VoltWiseApplication
  -> structured result
```

The MCP SDK application retains its request-size, Origin/Host, and optional
bearer-token middleware. Its lifespan is started by the combined ASGI lifespan.
If the configured MCP URL is unavailable, the gateway returns controlled HTTP
503 and persists a failed trace; there is no direct application fallback.

## Persistence and reset

SQLite remains appropriate for the initial single-instance hackathon package.
Attach a volume at `/data` to retain events, traces, and demo selection across
container replacement. Without a volume, that history is ephemeral. Automated
restart coverage verifies that the selected scenario, selected fault, events,
and MCP traces survive when the same database file is reused. Transient device
state intentionally restarts at its safe baseline: the heater is reported OFF
at 2 W even when the selected fault remains persisted.

`POST /api/demo/reset` still restores the deterministic scenario, fault,
simulation clock, heater state, and ordinary simulated device states. Events
and genuine MCP traces remain audit history; reset does not fabricate a trace.

## Security and scaling notes

- The runtime image uses a non-root `voltwise` account.
- `.dockerignore` excludes secrets, local databases, development dependencies,
  browser profiles, screenshots, and test artifacts.
- MCP Host/Origin checks and the one-MiB default body limit remain enabled.
- Public-demo mode adds small per-client, per-process REST limits. Apply edge
  rate and connection limits as well; in-memory limits reset on restart and do
  not coordinate replicas.
- This package deliberately uses one worker and assumes one application
  instance. SQLite and in-memory MCP sessions are not configured for replicas.
- Demo state is global, not isolated by browser session. Two judges can change
  the same fault/scenario or reset each other's run. Concurrent heater commands
  can also interleave the mutable retry counter, so demonstrations must be
  serialized.
- SQLite writes are short and use a five-second busy timeout, but there is no
  queue or cross-request transaction covering a whole diagnostic. A burst of
  concurrent writes can still produce lock errors.
- In public-demo mode, Basic authentication protects the UI and REST API while
  a required, distinct bearer token protects `/mcp`. Keep the container port
  reachable only from the TLS-terminating ingress. Never put either credential
  in frontend variables.
- Local mode deliberately remains unrestricted. Never expose it publicly.
- REST and MCP body limits are separate. Apply ingress limits before public
  exposure as defense in depth.
- `/health` is a side-effect-free liveness check. It deliberately does not make
  an MCP call or write SQLite; use an external post-deployment smoke test for
  end-to-end readiness.
- Configure `VOLTWISE_MCP_ALLOWED_HOSTS` for the exact public hostname before
  exposing `/mcp`. If forwarded headers are trusted, restrict
  `VOLTWISE_FORWARDED_ALLOW_IPS` to the actual proxy path rather than `*`.

## AWS deployment options

No AWS resources are created by this repository.

1. **Single EC2 instance with an attached EBS data volume — recommended for the
   hackathon.** Run exactly one container, mount the EBS-backed directory at
   `/data`, and terminate TLS either at an Application Load Balancer with an ACM
   certificate or at a carefully maintained reverse proxy on the instance. This
   most closely matches the tested single-instance and local-block-storage model.
   The tradeoff is instance patching, process supervision, backup, and recovery
   responsibility.
2. **One ECS/Fargate task with an ALB and EFS.** This provides managed task
   scheduling and persistent storage across task replacement, but introduces
   more services, networking, and fixed cost categories. Keep desired count at
   one. SQLite-on-EFS behavior must be load-tested before relying on it; do not
   scale tasks horizontally against this database.
3. **App Runner — not recommended.** Its container filesystem is ephemeral and
   the service is designed for stateless applications. AWS also stopped opening
   App Runner to new customers on 31 March 2026. It is acceptable only for an
   existing eligible account when losing local audit state is explicitly
   acceptable.

For an ALB deployment, expose only HTTPS publicly, redirect or close HTTP, route
all four paths through the same origin, and keep the container listener private
to the load balancer security group. Validate Streamable HTTP behavior through
the chosen proxy before the judging window.

## Promotional-credit cost-risk checklist

Do not rely on a hard-coded estimate. Use the AWS Pricing Calculator for the
chosen region and re-check the current service pages before provisioning.

- Compute runtime: EC2 instance hours or Fargate vCPU and memory duration.
- Always-on ingress: load balancer hours and processed data.
- Persistent storage: EBS or EFS capacity, operations/throughput, and snapshots.
- Container registry: ECR image storage, scanning choice, and data transfer.
- Network: public IPv4, NAT gateway if introduced, cross-AZ traffic, and internet
  data transfer. Avoid a NAT gateway unless the architecture truly requires it.
- Observability: CloudWatch log ingestion, retention, metrics, and alarms.
- DNS/TLS: hosted-zone and domain-registration categories; certificate behavior
  depends on the selected ingress.
- Backups and orphaned resources: retained volumes, snapshots, load balancers,
  elastic IPs, log groups, and old images can continue accruing cost.
- Before deployment, create actual and forecast budget alerts well below the
  promotional-credit ceiling. Budget notifications are delayed, so they are a
  warning mechanism rather than a hard spending cap.

## Verification

With a production frontend build present, the local single-origin smoke test
starts the combined host on loopback, initializes the official MCP client,
checks the required eight-tool set and full registry count, exercises the four
canonical flows with a reset between each, restarts against the same temporary
SQLite file, and verifies that an unavailable gateway MCP target fails closed:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-deployment.ps1
```

It writes its disposable database and server logs beneath the current user's
temporary directory and prints that evidence path. It does not use or delete
the repository's existing data.

For a running container, basic manual probes are:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod -Method Post http://127.0.0.1:8080/api/demo/reset
Invoke-RestMethod http://127.0.0.1:8080/api/sim/traces
```

The latest successful trace should report `STREAMABLE_HTTP` and protocol
`2025-11-25`. Static assets are served by Uvicorn/Starlette, not Vite.

The Docker client alone is insufficient for testing: the Linux Docker daemon
must be running before `docker build` or `docker run` can succeed.

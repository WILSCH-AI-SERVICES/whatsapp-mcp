# DaveX2001/deliverable-tracking#1609 — Deploy WhatsApp MCP on WILSCH

## Definition of Done

### Pass 1: Repo + patches (fork)
- [x] Fork `lharries/whatsapp-mcp` → `MariusWilsch/whatsapp-mcp`
- [x] Branch `wilsch-patches` with: transport swap (streamable-http), JID allowlist, send tools removed
- [x] Docker stack (bridge Dockerfile, MCP Dockerfile, docker-compose.yml, .env.example)
- [x] Patches pushed to fork

### Pass 2: Deploy + pair on WILSCH
- [x] Clone fork into `~/projects/personal/whatsapp-mcp__full/` on WILSCH-AI-SERVER
- [x] `.env` with token B + empty `WHATSAPP_ALLOWED_JIDS`
- [x] `docker compose up -d --build`
- [x] Both containers Up (`docker ps` shows `whatsapp-bridge` + `whatsapp-mcp`)
- [x] QR pair with primary WhatsApp number (via `docker logs whatsapp-bridge`)
- [x] Messages syncing to SQLite (row count > 0)

### Pass 3: Caddy publish + SSL
- [x] `/etc/caddy/conf.d/whatsapp-mcp.conf` created at `whatsapp-mcp.wilsch-deployment.com`
- [x] Bearer token B check enforced in Caddyfile
- [x] `systemctl reload caddy` successful
- [x] Valid SSL cert on subdomain (`curl -I` returns 200/401)
- [x] Public endpoint returns 401 without Bearer, 200+MCP with

### Pass 4: JID discovery + allowlist lock
- [x] `list_chats` returns JIDs after sync complete
- [x] User selects whitelist JIDs
- [x] `WHATSAPP_ALLOWED_JIDS` env updated, container restarted
- [x] Whitelisted JID queries succeed
- [x] Non-whitelisted JID queries return allowlist error

### Pass 5: MetaMCP registration
- [x] WhatsApp MCP added in MetaMCP UI (Streamable HTTP, URL + Authorization Bearer B)
- [x] Assigned to `hand-picked` namespace
- [x] Endpoint exists with token A
- [x] Tool list visible in MetaMCP inspector

### Pass 6: End-to-end verification
- [x] Claude Code `hand-picked-tools` config points at MetaMCP endpoint
- [x] Tool call from Claude returns live message data from allowlisted chat
- [x] Non-allowlisted JID request returns rejection

### Pass 7: Token persistence
- [x] `.env` on WILSCH has both tokens A + B
- [x] `agent-browser auth` vault entries exist locally for A and B

### Pass 8: WILSCH cleanup
- [x] `/etc/caddy/conf.d/metamcp.conf` removed
- [x] Caddy reloaded
- [x] `metamcp-pg` container stopped + removed
- [x] Postgres volume still present (`docker volume ls`)

### Pass 9: MetaMCP namespace cleanup
- [x] `hand-picked` namespace contents captured before deletions
- [x] 4 namespaces deleted via agent-browser: `read-website-fast`, `supabase`, `sequential-thinking`, `fireflies`
- [x] Underlying MCP server entries preserved
- [x] No hand-picked tools broken

### Pass 10: Post-completion sweep
- [x] Cross-server scan for additional orphan configs/containers documented

### Pass 11: Restore upstream tool surface (read-only → read+send parity)

Reverses the "send tools stripped" patch from Pass 1 commit `60f0022`. Per-client tool toggling delegated to MetaMCP UI rather than enforced at Python layer.

- [x] Re-add imports for `send_message`, `send_file`, `send_audio_message` in `main.py`
- [x] Re-add 3 `@mcp.tool()` definitions for those send tools
- [x] Update module docstring (drop "stripped" reference, add tool-toggling-via-MetaMCP note)

### Pass 12: Send allowlist split + Michael read access

Adds independent send allowlist (security default = empty blocks all) and grants Michael Reichert 1:1 read access for backfill of Phase 1 sign-off.

- [x] New env var `WHATSAPP_SEND_ALLOWED_JIDS` plumbed through `docker-compose.yml`
- [x] `_reject_send_if_blocked()` gate added; called from each send tool
- [x] `.env.example` updated with both vars + comments explaining semantics
- [ ] On WILSCH `.env`: read list extended with `4915233772868@s.whatsapp.net` (Michael Reichert)
- [ ] On WILSCH `.env`: send list set to `4917666990272@s.whatsapp.net` (David Eberle) + `120363405992061758@g.us` (Grooming Prep)
- [ ] On WILSCH `.env`: block-comment JID→identity mapping above each list (future-self readability)
- [ ] `docker compose build --no-cache whatsapp-mcp && docker compose up -d` clean
- [ ] Smoke: read on Michael's 1:1 returns messages (was rejected pre-Pass 12)
- [ ] Smoke: `send_message` to Grooming JID succeeds
- [ ] Smoke: `send_message` to non-allowlisted JID returns `recipient not in send allowlist` error
- [ ] `#1609` reopened in `DaveX2001/deliverable-tracking` with completion comment

---

## Operational Learnings (for future re-deploys / maintenance)

### Upstream drift — expect periodic re-patching (every 6-8 weeks)

`lharries/whatsapp-mcp` is unmaintained (~March 2025). WhatsApp bumps client version periodically; whatsmeow HEAD catches up fast. Expect the following on re-deploy:

**whatsmeow API drift (Go bridge):**
The latest whatsmeow requires `context.Context` as first arg on many calls. Upstream `main.go` does not use ctx. Sites needing `ctx.Background()` injection:
- `container.GetFirstDevice()` → `container.GetFirstDevice(ctx)`
- `client.GetGroupInfo(jid)` → `client.GetGroupInfo(ctx, jid)`
- `client.Store.Contacts.GetContact(jid)` → `...GetContact(ctx, jid)`
- `client.Download(downloader)` → `client.Download(ctx, downloader)`
- `sqlstore.New("sqlite3", path, dbLog)` → `sqlstore.New(ctx, "sqlite3", path, dbLog)`

When next whatsmeow API change hits, grep for `not enough arguments in call to` during build, patch in order.

**Go version tracking:**
whatsmeow HEAD at time of deploy required Go 1.25. Bump `FROM golang:1.25-bookworm` in `whatsapp-bridge/Dockerfile` when new whatsmeow version requires newer Go.

**Go module freshness:**
`go get -u go.mau.fi/whatsmeow && go mod tidy` runs during build to pull latest. `go.sum` is not committed — regenerated each build for freshness. Rebuild with `--no-cache` when chasing protocol updates.

**MCP SDK versioning (Python):**
Upstream pins `mcp[cli]>=1.6.0`. Streamable HTTP transport requires `mcp[cli]>=1.12.0`. Keep our pin at 1.12+.

### FastMCP quirks

**DNS-rebinding protection rejects proxy Host headers.**
FastMCP 1.12+ enforces `allowed_hosts`. Behind Caddy the upstream sees `Host: whatsapp-mcp.wilsch-deployment.com` → 421 Misdirected Request. **Fix in Caddy:**
```
reverse_proxy 127.0.0.1:8090 {
    header_up Host {upstream_hostport}
}
```
Rewrites Host to `127.0.0.1:8090` so FastMCP's default localhost allowlist accepts.

**Return type contracts.**
Upstream `whatsapp.py::list_messages` returns a pre-formatted `str` (not `List[Dict]`). `list_chats` returns `List[Chat]` dataclass (not dict). MCP tool signatures must:
- Return type `Any` on `list_messages` (string payload legal)
- Filter via `getattr(obj, "jid")` not `obj.get("jid")` for dataclass objects

### Allowlist filter placement

**Post-SQL filter masks results when combined with LIMIT.**
Upstream `list_chats` applies `LIMIT N` inside SQL. If none of the top-N chats are allowlisted, caller sees `[]` → looks broken.

**Fix:** when allowlist is active, fetch a wide window (e.g. 500), filter in Python, then paginate. Implemented in `main.py::list_chats`.

### QR pair flow

- Bridge prints ASCII QR to stdout via `docker logs whatsapp-bridge`
- QR rotates ~20s, full cycle times out ~60s
- Session persists in `whatsmeow.db` after first pair — no re-pair on container restart unless force-unlinked
- **Gotcha:** bridge logs message content at INFO level (plaintext). Treat `docker logs` as sensitive.

### Two-token auth model

- **Token B:** Caddy → WhatsApp MCP. Set in `.env` on server + Caddyfile `@authed header Authorization`.
- **Token A:** Claude → MetaMCP endpoint. Set in MetaMCP "API Keys" page + used as `Authorization: Bearer` header in client MCP config.

Layers are independent — tokens don't have to match, can rotate separately.

### MetaMCP operational gotchas

- **Delete namespace = cascade delete endpoint.** Recreating namespace does NOT restore endpoint; must recreate endpoint too (same slug to preserve URL).
- **Session handle stale after container restart.** Clients receive `Session not found (32600)` until MCP reconnect. Clients auto-retry on next init; in Claude Code, run `/mcp` to force reconnect.
- **Tool name prefix.** MetaMCP exposes tools as `<server-name>__<tool>` (e.g. `whatsapp-mcp__list_chats`), not raw `list_chats`.
- **Tools/call requires prior tools/list in same session.** Call `tools/list` before `tools/call` if hitting endpoint manually via curl.

### Deployment conventions (WILSCH-AI-SERVER)

- **Agent SSH = read-only.** `docker ps/logs/inspect` work. `docker stop/rm/exec/compose up` blocked by socket proxy.
- **For compose operations: SSH as `marius` user.** marius has docker group + sudo. Sandbox blocks `docker compose up/down` via any SSH user by default unless deployment_belief is overridden per-session.
- **Caddy config lives at `/etc/caddy/conf.d/*.conf`.** Owned by `caddy:caddy` — needs sudo to write. `systemctl reload caddy` picks up changes without downtime. SSL auto-provisions via Let's Encrypt on first request.

### WhatsApp ingestion use case

- **Bridge ingests ALL messages into SQLite** regardless of allowlist. MCP layer is the firewall — Claude sees only allowlisted chats.
- **Ban risk (primary account) = low for read-only, low-volume** but non-zero. Mitigations: pair as Linked Device (phone remains primary), no automated sending.
- **Recovery path if compromise suspected:** WhatsApp app → Settings → Linked Devices → Log out the bridge device. Instant disconnect; account intact.

# DaveX2001/deliverable-tracking#1609 — Deploy WhatsApp MCP on WILSCH

## Definition of Done

### Pass 1: Repo + patches (fork)
- [ ] Fork `lharries/whatsapp-mcp` → `MariusWilsch/whatsapp-mcp`
- [ ] Branch `wilsch-patches` with: transport swap (streamable-http), JID allowlist, send tools removed
- [ ] Docker stack (bridge Dockerfile, MCP Dockerfile, docker-compose.yml, .env.example)
- [ ] Patches pushed to fork

### Pass 2: Deploy + pair on WILSCH
- [ ] Clone fork into `~/projects/personal/whatsapp-mcp__full/` on WILSCH-AI-SERVER
- [ ] `.env` with token B + empty `WHATSAPP_ALLOWED_JIDS`
- [ ] `docker compose up -d --build`
- [ ] Both containers Up (`docker ps` shows `whatsapp-bridge` + `whatsapp-mcp`)
- [ ] QR pair with primary WhatsApp number (via `docker logs whatsapp-bridge`)
- [ ] Messages syncing to SQLite (row count > 0)

### Pass 3: Caddy publish + SSL
- [ ] `/etc/caddy/conf.d/whatsapp-mcp.conf` created at `whatsapp-mcp.wilsch-deployment.com`
- [ ] Bearer token B check enforced in Caddyfile
- [ ] `systemctl reload caddy` successful
- [ ] Valid SSL cert on subdomain (`curl -I` returns 200/401)
- [ ] Public endpoint returns 401 without Bearer, 200+MCP with

### Pass 4: JID discovery + allowlist lock
- [ ] `list_chats` returns JIDs after sync complete
- [ ] User selects whitelist JIDs
- [ ] `WHATSAPP_ALLOWED_JIDS` env updated, container restarted
- [ ] Whitelisted JID queries succeed
- [ ] Non-whitelisted JID queries return allowlist error

### Pass 5: MetaMCP registration
- [ ] WhatsApp MCP added in MetaMCP UI (Streamable HTTP, URL + Authorization Bearer B)
- [ ] Assigned to `hand-picked` namespace
- [ ] Endpoint exists with token A
- [ ] Tool list visible in MetaMCP inspector

### Pass 6: End-to-end verification
- [ ] Claude Code `hand-picked-tools` config points at MetaMCP endpoint
- [ ] Tool call from Claude returns live message data from allowlisted chat
- [ ] Non-allowlisted JID request returns rejection

### Pass 7: Token persistence
- [ ] `.env` on WILSCH has both tokens A + B
- [ ] `agent-browser auth` vault entries exist locally for A and B

### Pass 8: WILSCH cleanup
- [ ] `/etc/caddy/conf.d/metamcp.conf` removed
- [ ] Caddy reloaded
- [ ] `metamcp-pg` container stopped + removed
- [ ] Postgres volume still present (`docker volume ls`)

### Pass 9: MetaMCP namespace cleanup
- [ ] `hand-picked` namespace contents captured before deletions
- [ ] 4 namespaces deleted via agent-browser: `read-website-fast`, `supabase`, `sequential-thinking`, `fireflies`
- [ ] Underlying MCP server entries preserved
- [ ] No hand-picked tools broken

### Pass 10: Post-completion sweep
- [ ] Cross-server scan for additional orphan configs/containers documented

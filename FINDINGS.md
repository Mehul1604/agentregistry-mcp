# AgentRegistry API Findings & README Gap

## Date: 2026-02-22

---

## Problem: README Not Stored on `arctl mcp publish`

When you run `arctl mcp publish`, the local `README.md` file is **never uploaded** to the registry. The publish flow (`internal/cli/mcp/publish.go`) only sends:

- `name` (from mcp.yaml author + name)
- `version` (from mcp.yaml)
- `description` (from mcp.yaml)
- `packages` (registryType, identifier from CLI flags)
- `runtimeHint` (from mcp.yaml)
- `runtimeArgs` (from mcp.yaml)

The `README.md` sitting next to `mcp.yaml` is completely ignored.

---

## Where READMEs Live

### Database Table: `server_readmes`

```sql
CREATE TABLE server_readmes (
    server_name  VARCHAR(255) NOT NULL,
    version      VARCHAR(255) NOT NULL,
    content      BYTEA NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text/markdown',
    size_bytes   INTEGER NOT NULL,
    sha256       BYTEA NOT NULL,
    fetched_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (server_name, version),
    CONSTRAINT fk_server_readmes_server
        FOREIGN KEY (server_name, version)
        REFERENCES servers(server_name, version)
        ON DELETE CASCADE
);
```

### Go Struct

```go
// pkg/registry/database/database.go:36
type ServerReadme struct {
    ServerName  string
    Version     string
    Content     []byte
    ContentType string
    SizeBytes   int
    SHA256      []byte
    FetchedAt   time.Time
}
```

---

## README Read Endpoints (exist, work, but table is empty after publish)

### GET `/v0/servers/{serverName}/readme`

Returns README for the **latest** version.

**Call chain:**
```
Handler (servers.go:358)
  -> registry.GetServerReadmeLatest(ctx, serverName)
    -> service (registry_service.go:437)
      -> s.db.GetLatestServerReadme(ctx, nil, serverName)
        -> postgres.go:1082
          SQL: SELECT ... FROM server_readmes sr
               INNER JOIN servers s ON sr.server_name = s.server_name
                 AND sr.version = s.version
               WHERE sr.server_name = $1 AND s.is_latest = true
               LIMIT 1
```

### GET `/v0/servers/{serverName}/versions/{version}/readme`

Returns README for a **specific** version. Supports `version=latest`.

**Call chain:**
```
Handler (servers.go:385)
  -> if version == "latest":
       registry.GetServerReadmeLatest(ctx, serverName)
     else:
       registry.GetServerReadmeByVersion(ctx, serverName, version)
         -> service (registry_service.go:441)
           -> s.db.GetServerReadme(ctx, nil, serverName, version)
             -> postgres.go:1057
               SQL: SELECT ... FROM server_readmes
                    WHERE server_name = $1 AND version = $2
                    LIMIT 1
```

### Response Shape

```json
{
  "content": "# My Server\nDescription here...",
  "contentType": "text/markdown",
  "sizeBytes": 1024,
  "sha256": "a1b2c3d4e5f6...",
  "version": "1.0.0",
  "fetchedAt": "2025-02-22T10:00:00Z"
}
```

---

## README Write Paths (no public API endpoint)

There is **no public REST endpoint** to upload a README. The only write path is:

### Service Method

```go
// internal/registry/service/registry_service.go:407
func (s *registryServiceImpl) StoreServerReadme(
    ctx context.Context,
    serverName, version string,
    content []byte,
    contentType string,
) error
```

### Database Method

```go
// internal/registry/database/postgres.go:998
func (db *PostgreSQL) UpsertServerReadme(ctx context.Context, tx pgx.Tx, readme *ServerReadme) error
```

SQL:
```sql
INSERT INTO server_readmes (server_name, version, content, content_type, size_bytes, sha256, fetched_at)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (server_name, version) DO UPDATE
SET content = EXCLUDED.content,
    content_type = EXCLUDED.content_type,
    size_bytes = EXCLUDED.size_bytes,
    sha256 = EXCLUDED.sha256,
    fetched_at = EXCLUDED.fetched_at
```

### Callers (internal only)

1. **Seeder** (`internal/registry/seed/builtin.go:91`) - seeds built-in servers with pre-baked READMEs
2. **Importer** (`internal/registry/importer/importer.go:249`) - downloads README from GitHub during `arctl import --enrich-server-data`

---

## What `arctl import` Does

Hidden admin command (`internal/cli/import.go`). Bulk-imports servers **directly to the database** (bypasses HTTP API, runs with no auth).

### Usage

```bash
arctl import --source <path|url> [flags]
```

### Flags

| Flag | Description |
|------|-------------|
| `--source` | (required) JSON file path, HTTP URL, or registry `/v0/servers` URL |
| `--update` | Update existing entries if name/version already exists |
| `--enrich-server-data` | Fetch GitHub metadata (stars, security, etc.) AND download READMEs |
| `--readme-seed` | Pre-built JSON file mapping server@version to base64 README content |
| `--github-token` | GitHub token for higher rate limits during enrichment |
| `--generate-embeddings` | Generate semantic embeddings during import |
| `--skip-validation` | Disable schema validation |
| `--progress-cache` | File to store import progress for resumable runs |
| `--timeout` | HTTP request timeout (default 30s) |

### Flow

```
1. Read seed data (JSON file / HTTP URL / registry API with pagination)
2. For each server (10 concurrent goroutines):
   a. Validate ServerJSON schema
   b. Optionally enrich from GitHub API:
      - Stars, forks, watchers, language, topics
      - Release download counts
      - OpenSSF Scorecard score
      - Dependabot/CodeQL detection
      - Security alert counts
      - OSV vulnerability scan
      - Docker Hub pull counts
      - Endpoint health probe
   c. registry.CreateServer() -> inserts into PG
   d. Optionally store embeddings
   e. If --enrich-server-data:
      - Check --readme-seed file first
      - Otherwise download README.md from GitHub (via repository.url)
      - registry.StoreServerReadme() -> inserts into server_readmes
```

### README Download Logic (importer.go:1226-1243)

```
downloadReadme(ctx, server):
  1. Check server.Repository.URL exists
  2. Parse GitHub owner/repo from URL
  3. Fetch via GitHub Contents API: GET /repos/{owner}/{repo}/contents/README.md
  4. Decode base64 content
  5. Return (content, "text/markdown")
```

---

## Gap Summary

| What | Status |
|------|--------|
| `server_readmes` DB table | Exists |
| `GET /v0/servers/{name}/readme` | Works (returns 404 when empty) |
| `GET /v0/servers/{name}/versions/{version}/readme` | Works (returns 404 when empty) |
| `POST/PUT` endpoint to upload README | Does NOT exist |
| `arctl mcp publish` uploads README | Does NOT happen |
| `arctl import --enrich-server-data` downloads README | Works (from GitHub only) |
| Service method `StoreServerReadme()` | Works |
| DB method `UpsertServerReadme()` | Works |

### To fix: two things needed

1. **Add a public REST endpoint** for README upload (e.g., `PUT /v0/servers/{name}/versions/{version}/readme`)
2. **Modify `arctl mcp publish`** to read the local `README.md` and upload it after creating the server

---

## Affected Servers (our 3 MCP servers)

| Server | Published Name | Version | README in DB? |
|--------|---------------|---------|---------------|
| cheap-summarizer | `mehul/cheap-summarizer` | 0.1.0 | No |
| fast-log-analyzer | `mehul/fast-log-analyzer` | 0.1.0 | No |
| premium-research-agent | `mehul/premium-research-agent` | 0.1.0 | No |

All 3 have local `README.md` files (~207 lines each) but none were uploaded to the registry.

---

## Custom Metadata in mcp.yaml (also not stored)

The `metadata` field in `mcp.yaml` is also not published:

```yaml
# cheap-summarizer
metadata:
  capability: summarization
  domain: text
  cost: low
  latency: medium
  reliability: 0.7

# fast-log-analyzer
metadata:
  capability: log-analysis
  cost: medium
  latency: low
  reliability: 0.9

# premium-research-agent
metadata:
  capability: research
  cost: high
  latency: high
  reliability: 0.95
```

The `manifest.ProjectManifest` struct does not have a `Metadata` field, so this custom data in `mcp.yaml` is silently ignored during publish.

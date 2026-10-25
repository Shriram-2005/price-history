# AGENTS.md

## External docs - Swiggy Builders Club
This project integrates Swiggy MCP servers. Before writing Swiggy code, fetch the authoritative docs:
- Index: https://mcp.swiggy.com/builders/llms.txt
- Full text: https://mcp.swiggy.com/builders/llms-full.txt
- Per-page: append `.md` to any https://mcp.swiggy.com/builders/docs/... URL

Tool schemas live under `/docs/reference/{food,instamart,dineout,scenes}`.
Error codes live at `/docs/reference/errors`.
Auth flow is at `/docs/start/authenticate`.

### Rules
1. Before recommending a tool name, parameter, error code, rate limit, or auth flow, fetch the relevant doc and verify.
2. Never invent tool names or parameters. If the docs don't cover it, say so and ask.
3. Prefer `.md` page fetches over `llms-full.txt` when you know the exact area - it's cheaper on context.

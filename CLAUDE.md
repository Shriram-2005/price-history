# Claude Guidelines & Swiggy Builders Club MCP Docs

You have access to Swiggy Builders Club docs - the authoritative source for Swiggy MCP (Food, Instamart, Dineout, Scenes). Always consult these before writing Swiggy code:
- Index: https://mcp.swiggy.com/builders/llms.txt
- Full text: https://mcp.swiggy.com/builders/llms-full.txt
- Per-page: append `.md` to any https://mcp.swiggy.com/builders/docs/... URL

Tool schemas live under `/docs/reference/{food,instamart,dineout,scenes}`.
Error codes live at `/docs/reference/errors`.
Auth flow is at `/docs/start/authenticate`.

### Rules:
1. Before recommending a tool name, parameter, error code, rate limit, or auth flow, fetch the relevant doc and verify.
2. Never invent tool names or parameters. If the docs don't cover it, say so and ask.
3. Prefer `.md` page fetches over `llms-full.txt` when you know the exact area - it's cheaper on context.

### Smoke test verification:
Food server exposes 20 tools:
- search_restaurants
- search_menu
- get_restaurant_menu
- update_food_cart
- get_food_cart
- flush_food_cart
- fetch_food_coupons
- apply_food_coupon
- place_food_order
- get_payment_options
- check_payment_status
- confirm_order
- track_food_order
- get_food_delivery_status
- get_food_orders
- get_food_order_details
- get_addresses
- create_address
- delete_address
- recommend_address
- report_error (Note: utility diagnostic tool)
Total core tools: 20

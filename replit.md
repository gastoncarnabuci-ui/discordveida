# Discord Answer Bot

A Python Discord bot that answers questions in Spanish with an original, dryly sarcastic supercomputer persona.

## Run & Operate

- `uv run python -m discord_bot` — run the Discord bot
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required secrets: `DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`
- Optional env: `OPENAI_MODEL` (defaults to `gpt-5.4-mini`), `DISCORD_GUILD_ID` (for faster command registration in one test server)

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Python 3.13, `discord.py`, OpenAI Python SDK
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

_Populate as you build — short repo map plus pointers to the source-of-truth file for DB schema, API contracts, theme files, etc._

## Architecture decisions

_Populate as you build — non-obvious choices a reader couldn't infer from the code (3-5 bullets)._

## Product

- `/preguntar` lets a server member ask the bot a question.
- Mentioning the bot in a message also triggers a reply.
- Answers prioritize accuracy and clearly state uncertainty; the bot does not have live web access.
- The bot uses a playful, sarcastic voice without slurs, identity-based insults, or imitating a named character.

## User preferences

- The user wants a sarcastic, ironic personality that still prioritizes correct answers.

## Gotchas

- Enable the Message Content Intent in Discord's Developer Portal for mention-based replies.
- OpenAI requests are billed to the account that owns `OPENAI_API_KEY`.
- Conversation context is temporary and isolated by user and channel; it resets when the bot restarts.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details

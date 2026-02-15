# Assist Link

## Overview

Assist Link is an intelligent voice support mobile agent for credit card queries. It's a React Native (Expo) mobile app with a dual-backend architecture: a Node.js/Express server acts as the primary entry point and proxy, while a Python/FastAPI backend handles the core business logic including AI-powered voice transcription, sentiment analysis, and ticket management.

The app allows users to tap "Talk to Support" and speak to an AI agent that attempts to resolve credit card queries. It continuously monitors emotional sentiment, detects dissatisfaction in real-time, softly stops failed conversations, and creates support tickets (via Trello) when human follow-up is needed.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend (React Native / Expo)
- **Framework**: Expo SDK 54 with expo-router for file-based routing
- **Navigation**: Stack-based navigation with two main screens: home (`app/index.tsx`) and conversation detail (`app/conversation/[id].tsx`)
- **State Management**: TanStack React Query for server state, local React state for UI
- **Styling**: React Native StyleSheet with a custom color theme system supporting light/dark modes (`constants/colors.ts`)
- **Fonts**: Inter font family (Regular, Medium, SemiBold, Bold) via `@expo-google-fonts/inter`
- **Animations**: `react-native-reanimated` for UI animations (pulsing orbs, waveforms, fade-ins)
- **Key Libraries**: expo-haptics, expo-av (audio), expo-image-picker, expo-linear-gradient, react-native-gesture-handler, react-native-keyboard-controller

### Backend Layer 1: Node.js/Express (server/)
- **Purpose**: Serves as the main entry point on the default port, handles CORS, serves static assets in production, and proxies all `/api` requests to the FastAPI backend
- **Proxy**: Uses `http-proxy-middleware` to forward `/api/*` routes to `http://127.0.0.1:8001`
- **Process Management**: Automatically spawns the FastAPI Python process and restarts it on failure
- **File**: `server/index.ts` (main), `server/routes.ts` (proxy setup)

### Backend Layer 2: Python/FastAPI (backend/)
- **Purpose**: Core business logic — conversation management, voice processing, sentiment analysis, ticket creation
- **Port**: Runs on port 8001
- **API Routes**:
  - `POST /api/conversations/start` — Start a new support conversation
  - `POST /api/conversations/{id}/message` — Send a text message in a conversation
  - `POST /api/conversations/voice` — Process voice audio (transcribe + sentiment + respond)
  - `POST /api/sentiment/analyze` — Analyze audio sentiment via Deepgram
  - `POST /api/sentiment/text` — Analyze text sentiment locally
  - `GET /api/health` — Health check with integration status
- **Data Storage**: In-memory Python dictionary (`backend/store.py`). Conversations are stored in `conversations_store` dict — no persistent database for conversation data currently.
- **Conversation Logic**: Pattern-matching based intent classification for credit card queries (bill generation, payment deduction, balance, due dates, complaints). See `backend/services/conversation.py`.

### Database (PostgreSQL / Drizzle)
- **Schema**: Defined in `shared/schema.ts` using Drizzle ORM with a `users` table (id, username, password)
- **Config**: `drizzle.config.ts` points to PostgreSQL via `DATABASE_URL` environment variable
- **Current Usage**: The schema exists but the main conversation data is stored in-memory on the Python side. The Drizzle/Postgres setup appears to be scaffolding for future user authentication.
- **Migrations**: Output to `./migrations` directory, managed via `drizzle-kit push`

### API Communication Pattern
- Mobile app → Express server (port 5000) → FastAPI (port 8001) for all `/api` routes
- The `lib/query-client.ts` constructs API URLs using `EXPO_PUBLIC_DOMAIN` environment variable
- Uses `expo/fetch` for HTTP requests with credentials included

### Build & Deployment
- **Dev**: Two processes run concurrently — `expo:dev` for the mobile app bundler and `server:dev` for the Express server (which spawns FastAPI)
- **Production**: Static Expo build via `expo:static:build`, Express serves built assets, esbuild bundles the server code
- **Scripts**: `db:push` for database schema sync

## External Dependencies

### Deepgram API
- **Purpose**: Speech-to-text transcription (Nova-2 model) and audio sentiment analysis
- **Config**: `DEEPGRAM_API_KEY` environment variable
- **Endpoints Used**: `/v1/listen` for transcription, `/v1/listen` with sentiment model for audio intelligence
- **Fallback**: Returns empty/neutral results if not configured

### Trello API
- **Purpose**: Mandatory ticket creation for support cases (especially escalated/complaint conversations)
- **Config**: `TRELLO_API_KEY`, `TRELLO_TOKEN`, `TRELLO_LIST_ID` environment variables
- **Endpoint Used**: `POST /1/cards` to create cards
- **Fallback**: Generates local ticket IDs (`LOCAL-{timestamp}`) if Trello is not configured

### Key NPM Dependencies
- `expo` ~54.0.27, `react` 19.1.0, `react-native` 0.81.5
- `express` ^5.0.1 (Express v5)
- `drizzle-orm` + `drizzle-zod` for database ORM and validation
- `@tanstack/react-query` for data fetching
- `http-proxy-middleware` for API proxying
- `pg` for PostgreSQL connection

### Key Python Dependencies
- `fastapi` + `uvicorn` for the API server
- `httpx` for async HTTP requests to Deepgram and Trello
- `pydantic` for data models/validation
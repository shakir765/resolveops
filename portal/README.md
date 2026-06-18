# ResolveOps Helpdesk Portal

React + Vite + Tailwind helpdesk UI for the ResolveOps API.

## Features

- Submit IT tickets (async processing)
- View **My tickets** filtered by signed-in user ID
- Ticket detail with auto-refresh until resolved, failed, or escalated
- Simple user identity stored in `localStorage` (no SSO in v1)

## Prerequisites

- ResolveOps API on `http://localhost:8000`
- RabbitMQ + graph worker running for async resolution

## Setup

```powershell
cd portal
copy .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Environment

| Variable | Default |
|----------|---------|
| `VITE_API_URL` | `http://localhost:8000` |

## API used

- `POST /tickets` — create ticket (`source: portal`)
- `POST /tickets/{id}/process` — queue async graph run
- `GET /tickets?user_id=` — list my tickets
- `GET /tickets/{id}` — detail + resolution (`user_response`)

## Build

```powershell
npm run build
npm run preview
```

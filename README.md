# gogo-backend-mcp

A lightweight MCP-powered backend for serving curated travel spots straight from `model.spot`. The FastMCP server in `trip.py` exposes tools that let any compatible client request the latest main attractions, supporting sites, and the top ten most popular destinations.

## Features
- `major_views`, `sub_views`, and `top_10_spots` tools implemented via FastMCP.
- SQLAlchemy ORM mapped through `model/spot.py` with GeoAlchemy spatial support.
- Environment-driven configuration with `.env` plus sensible defaults in `util/database.py`.

## Requirements
```powershell
python -m pip install -r requirements.txt
```

## Environment
Copy `.env.example` (if you create one) or create a `.env` file with at least:
```
DATABASE_URL=postgresql+psycopg://user:password@localhost/spot_db
LOG_LEVEL=INFO
```
`util/database.py` will fall back to `postgresql+psycopg://postgres:password@localhost/spot_db` when nothing is provided.

## Database
- The app expects a PostgreSQL database with a `public.spot` table matching `model.spot.Spot`.
- The table requires the PostGIS extension for the `location` geometry column.
- Apply your own migrations or schema creation outside this service; SQLAlchemy will not auto-create tables here.

## Running locally
```powershell
python trip.py
```
The MCP server listens on stdio and exposes three async tools:
1. `major_views` – active spots with `popularity > 3000`.
2. `sub_views` – active spots with `1 < popularity < 3000`.
3. `top_10_spots` – ten most popular active spots.

Each tool returns JSON data from the respective helper in `src/action.py`.

## Logging
`util/logging_setup.py` configures a single console handler; change `LOG_LEVEL` or wrap calls with your own handlers if you need file logging.

## MCP Setup
This project uses FastMCP to create an MCP server. The server exposes three tools that clients can call to retrieve travel spot data.

```mcp.json
{
    "servers": {
        "trip-mcp": {
            "command": "uv",
            "args": [
                "--directory",
                "/{Project Parent Location}",
                "run",
                "trip.py"
            ],
            "env": {
            }
        }
        // add your MCP stdio servers configuration here
        // example:
        // "my-mcp-server": {
        //     "type": "stdio",
        //     "command": "my-command",
        //     "args": [],
        //     "env": {
        //         "TOKEN": "my_token"
        //     }
        // }
    }
}
```


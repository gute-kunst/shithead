# Architecture

## Overview

This project implements the card game Shithead as a WebSocket-based multiplayer server with a separate Python terminal client.

- `server/pyshithead/main.py` exposes the FastAPI application and WebSocket endpoints.
- `server/pyshithead/models/web` manages connected clients and maps them onto a game table.
- `server/pyshithead/models/common` translates WebSocket payloads into typed requests and adapts the game engine into outbound response models.
- `server/pyshithead/models/game` contains the game rules, state transitions, and card-handling logic.
- `client_py/shithead` is a terminal client that connects to the server and sends typed requests over the shared protocol.

The runtime behavior in this document is based on the current code and on the integration coverage in `server/tests/test_main.py`.

## Runtime Architecture

```mermaid
flowchart LR
    Player[Player at terminal]
    Client[Python terminal client<br/>client_py/shithead/client.py]

    subgraph Server[FastAPI server]
        Main[main.py<br/>FastAPI app]
        Endpoint[/WebSocket /game/{game_id}/]
        Tables[GameTablesManager]
        Table[GameTable]
        Clients[ClientManager]
        Manager[GameManager]

        subgraph Engine[Game rules engine]
            Game[Game]
            Requests[PlayRequest types<br/>ChoosePublicCardsRequest<br/>PrivateCardsRequest<br/>HiddenCardRequest<br/>TakePlayPileRequest]
            Domain[Player / Dealer / PileOfCards<br/>SetOfCards / events_and_states]
        end

        Schema[request_models<br/>Pydantic request/response schema]
        Aux[/WebSocket /ws<br/>test endpoint/]
    end

    Player --> Client
    Client -->|connect + send JSON| Endpoint
    Endpoint --> Main
    Main --> Tables
    Tables -->|resolve table by id| Table
    Table --> Clients
    Table -->|start_game / game_request| Manager
    Main -->|request_factory| Schema
    Schema -->|typed inbound request| Table

    Manager --> Game
    Manager -->|translate inbound payloads| Requests
    Requests -->|validate + process| Game
    Game <--> Domain

    Manager -->|rules / public_info / private_info| Schema
    Table -->|broadcast table state + logs| Schema
    Schema -->|client_id / current_game_table / log / invalid-request| Clients
    Clients -->|fan-out JSON responses| Endpoint
    Endpoint --> Client
    Main -. auxiliary only .-> Aux
```

## Request And Response Flow

### Join flow

1. A client connects to `/game/{game_id}`.
1. `main.py` asks `GameTablesManager` for a table.
1. `GameTable.add_client()` registers the WebSocket through `ClientManager`.
1. The server sends:
   - `client_id` to the new client
   - `log` to connected clients
   - `current_game_table` to connected clients

### Game start flow

1. Any connected client sends `{"type": "start_game"}`.
1. `GameTable.start_game()` creates a `GameManager` from the connected client ids.
1. `GameManager` initializes `Game`, which uses `Dealer` to create and distribute cards.
1. The server broadcasts shared data:
   - `rules`
   - `public_info`
1. The server then sends `private_info` individually to each client.

### Turn processing flow

1. A client sends a typed request such as `choose_public_cards`, `private_cards`, `hidden_card`, or `take_play_pile`.
1. `request_models.request_factory()` converts raw JSON into a Pydantic request model.
1. `GameTable.game_request()` forwards the request into `GameManager.process_request()`.
1. `GameManager` converts the transport model into a game-engine request object and calls into `Game`.
1. `Game` validates the move, updates piles and player state, and applies event-driven effects such as:
   - advancing turn order
   - burning the pile
   - changing valid ranks
   - removing finished players
1. The server broadcasts updated `public_info`.
1. The acting client receives refreshed `private_info`.
1. Invalid moves are returned to the acting client as `invalid-request`.

## Current Architectural Constraints

- `GameTablesManager.get_game_table_by_id()` currently ignores the requested `game_id` and always returns the first table. The project is effectively single-table today.
- The main gameplay transport is WebSocket-only. There is no separate REST API for game actions.
- The `/ws` endpoint is only a simple test/demo socket and is not part of the main gameplay path.
- The generated client models in `client_py/shithead/model.py` are derived from `server/pyshithead/models/common/request_models.py`, so the server schema is the protocol source of truth.

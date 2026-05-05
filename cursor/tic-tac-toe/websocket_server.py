import asyncio
import json
import random
import string

import websockets
from websockets.exceptions import ConnectionClosed

WINNING_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]

rooms: dict[str, dict] = {}
client_to_room: dict = {}


def generate_room_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(alphabet) for _ in range(length))
        if code not in rooms:
            return code


def new_room_state() -> dict:
    return {
        "board": [""] * 9,
        "currentPlayer": "X",
        "gameActive": True,
        "scores": {"X": 0, "O": 0, "draw": 0},
        "players": {},
    }


def winning_player(board: list[str]) -> str | None:
    for a, b, c in WINNING_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: list[str]) -> bool:
    return all(cell != "" for cell in board)


async def send_json(ws, payload: dict) -> None:
    await ws.send(json.dumps(payload))


async def broadcast_state(room_code: str) -> None:
    room = rooms.get(room_code)
    if not room:
        return

    disconnected = []
    for ws, symbol in list(room["players"].items()):
        try:
            await send_json(
                ws,
                {
                    "type": "state",
                    "room": room_code,
                    "you": symbol,
                    "board": room["board"],
                    "currentPlayer": room["currentPlayer"],
                    "gameActive": room["gameActive"],
                    "scores": room["scores"],
                },
            )
        except ConnectionClosed:
            disconnected.append(ws)

    for ws in disconnected:
        changed_room = remove_player(ws)
        if changed_room and changed_room != room_code:
            await broadcast_state(changed_room)


def remove_player(ws) -> str | None:
    room_code = client_to_room.pop(ws, None)
    if not room_code or room_code not in rooms:
        return None

    room = rooms[room_code]
    room["players"].pop(ws, None)
    if not room["players"]:
        rooms.pop(room_code, None)
        return None

    # If room now has one player, re-open board to wait for second.
    if len(room["players"]) == 1:
        room["board"] = [""] * 9
        room["currentPlayer"] = "X"
        room["gameActive"] = True
        # Ensure remaining player always becomes X for next opponent.
        remaining_ws = next(iter(room["players"]))
        room["players"] = {remaining_ws: "X"}
    return room_code


async def handle_message(ws, message: dict) -> None:
    msg_type = message.get("type")

    if msg_type == "create_room":
        old_room = remove_player(ws)
        if old_room:
            await broadcast_state(old_room)
        room_code = generate_room_code()
        room = new_room_state()
        room["players"][ws] = "X"
        rooms[room_code] = room
        client_to_room[ws] = room_code
        await send_json(ws, {"type": "room_created", "room": room_code})
        await broadcast_state(room_code)
        return

    if msg_type == "join_room":
        room_code = str(message.get("room", "")).upper().strip()
        room = rooms.get(room_code)
        if not room:
            await send_json(ws, {"type": "error", "message": "Room not found."})
            return
        if len(room["players"]) >= 2 and ws not in room["players"]:
            await send_json(ws, {"type": "error", "message": "Room is full."})
            return

        old_room = remove_player(ws)
        if old_room:
            await broadcast_state(old_room)

        if ws not in room["players"]:
            # First player keeps X; second player becomes O.
            used_symbols = set(room["players"].values())
            symbol = "O" if "X" in used_symbols else "X"
            room["players"][ws] = symbol
        client_to_room[ws] = room_code
        await broadcast_state(room_code)
        return

    room_code = client_to_room.get(ws)
    room = rooms.get(room_code) if room_code else None
    if not room:
        await send_json(ws, {"type": "error", "message": "Join a room first."})
        return

    player = room["players"].get(ws)
    if not player:
        await send_json(ws, {"type": "error", "message": "Player not in room."})
        return

    if msg_type == "leave_room":
        changed_room = remove_player(ws)
        if changed_room:
            await broadcast_state(changed_room)
        return

    if msg_type == "reset_board":
        room["board"] = [""] * 9
        room["currentPlayer"] = "X"
        room["gameActive"] = True
        await broadcast_state(room_code)
        return

    if msg_type == "reset_scores":
        room["scores"] = {"X": 0, "O": 0, "draw": 0}
        await broadcast_state(room_code)
        return

    if msg_type == "make_move":
        if not room["gameActive"]:
            await send_json(ws, {"type": "error", "message": "Game is over. Press Restart Game."})
            return
        if room["currentPlayer"] != player:
            await send_json(ws, {"type": "error", "message": "Not your turn — wait for your opponent."})
            return

        index = message.get("index")
        if not isinstance(index, int) or index < 0 or index > 8:
            await send_json(ws, {"type": "error", "message": "Invalid move."})
            return
        if room["board"][index] != "":
            await send_json(ws, {"type": "error", "message": "That square is already taken."})
            return

        room["board"][index] = player
        winner = winning_player(room["board"])
        if winner:
            room["gameActive"] = False
            room["scores"][winner] += 1
        elif is_draw(room["board"]):
            room["gameActive"] = False
            room["scores"]["draw"] += 1
        else:
            room["currentPlayer"] = "O" if room["currentPlayer"] == "X" else "X"
        await broadcast_state(room_code)


async def handler(ws):
    try:
        async for text in ws:
            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                await send_json(ws, {"type": "error", "message": "Invalid JSON."})
                continue
            await handle_message(ws, message)
    finally:
        changed_room = remove_player(ws)
        if changed_room:
            await broadcast_state(changed_room)


async def main():
    # Newer websockets versions may enforce origin checks more strictly.
    # Allow local browser origins used by this project and non-browser clients.
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        None,
    ]
    async with websockets.serve(handler, "0.0.0.0", 8765, origins=allowed_origins):
        print("WebSocket server running on ws://localhost:8765", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

const cells = document.querySelectorAll("[data-cell]");
const statusText = document.getElementById("status");
const restartButton = document.getElementById("restart");
const resetScoresButton = document.getElementById("reset-scores");
const soundToggleButton = document.getElementById("sound-toggle");
const gameModeSelect = document.getElementById("game-mode");
const scoreXText = document.getElementById("score-x");
const scoreOText = document.getElementById("score-o");
const scoreDrawText = document.getElementById("score-draw");
const onlinePanel = document.getElementById("online-panel");
const roomInput = document.getElementById("room-input");
const createRoomButton = document.getElementById("create-room");
const joinRoomButton = document.getElementById("join-room");
const leaveRoomButton = document.getElementById("leave-room");
const onlineStatus = document.getElementById("online-status");
const serverAddressText = document.getElementById("server-address");
const boardSection = document.querySelector(".board");

const winningLines = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [0, 3, 6],
  [1, 4, 7],
  [2, 5, 8],
  [0, 4, 8],
  [2, 4, 6],
];
const SCORE_STORAGE_KEY = "ticTacToeScoresV1";
const WS_PORT = 8765;

function getWebSocketUrl() {
  const host = window.location.hostname || "localhost";
  const isSecurePage = window.location.protocol === "https:";
  const protocol = isSecurePage ? "wss" : "ws";
  return `${protocol}://${host}:${WS_PORT}`;
}

const WS_URL = getWebSocketUrl();

let board = Array(9).fill("");
let currentPlayer = "X";
let gameActive = true;
let soundEnabled = true;
let audioContext = null;
let gameMode = "pvp";
let isComputerThinking = false;
let ws = null;
let isConnected = false;
let roomCode = "";
let mySymbol = "";
let isMyTurn = false;
let lastBoardSnapshot = Array(9).fill("");
let lastGameActive = true;
const scores = { X: 0, O: 0, draw: 0 };

function updateStatus(message, { isError = false } = {}) {
  statusText.textContent = message;
  statusText.classList.remove("status-pop", "status-error");
  void statusText.offsetWidth;
  statusText.classList.add("status-pop");
  if (isError) {
    statusText.classList.add("status-error");
  }
}

function setOnlineStatus(message) {
  onlineStatus.textContent = message;
}

function renderServerAddress() {
  const hostLabel = window.location.hostname || "localhost";
  serverAddressText.textContent = `Server: ${WS_URL} (host: ${hostLabel})`;
}

function renderScores() {
  scoreXText.textContent = String(scores.X);
  scoreOText.textContent = String(scores.O);
  scoreDrawText.textContent = String(scores.draw);
}

function saveScores() {
  try {
    window.localStorage.setItem(SCORE_STORAGE_KEY, JSON.stringify(scores));
  } catch {}
}

function loadScores() {
  try {
    const raw = window.localStorage.getItem(SCORE_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    const x = Number(parsed?.X);
    const o = Number(parsed?.O);
    const draw = Number(parsed?.draw);
    if (Number.isFinite(x) && x >= 0 && Number.isFinite(o) && o >= 0 && Number.isFinite(draw) && draw >= 0) {
      scores.X = x;
      scores.O = o;
      scores.draw = draw;
    }
  } catch {}
}

function getWinningLine(player) {
  return winningLines.find((line) => line.every((index) => board[index] === player)) || null;
}

function isDraw() {
  return board.every((cell) => cell !== "");
}

function getAudioContext() {
  if (!audioContext) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) {
      return null;
    }
    audioContext = new Ctx();
  }
  return audioContext;
}

async function unlockAudio() {
  const ctx = getAudioContext();
  if (!ctx) return;
  if (ctx.state === "suspended") {
    try {
      await ctx.resume();
    } catch {}
  }
}

function playTone(frequency, duration, type = "sine", volume = 0.03, delay = 0) {
  if (!soundEnabled) return;
  const ctx = getAudioContext();
  if (!ctx) return;
  const now = ctx.currentTime + delay;
  const oscillator = ctx.createOscillator();
  const gainNode = ctx.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, now);
  gainNode.gain.setValueAtTime(0.0001, now);
  gainNode.gain.exponentialRampToValueAtTime(volume, now + 0.015);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, now + duration);
  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);
  oscillator.start(now);
  oscillator.stop(now + duration + 0.02);
}

function playMoveSound(player) {
  playTone(player === "X" ? 440 : 554.37, 0.1, "triangle", 0.03);
}

function playWinSound() {
  playTone(523.25, 0.12, "triangle", 0.04, 0);
  playTone(659.25, 0.12, "triangle", 0.04, 0.09);
  playTone(783.99, 0.18, "triangle", 0.04, 0.18);
}

function playDrawSound() {
  playTone(349.23, 0.15, "sine", 0.025, 0);
  playTone(329.63, 0.15, "sine", 0.025, 0.12);
}

function playResetSound() {
  playTone(392, 0.08, "square", 0.018, 0);
  playTone(523.25, 0.08, "square", 0.018, 0.07);
}

function setSoundState(enabled) {
  soundEnabled = enabled;
  soundToggleButton.textContent = enabled ? "Sound: On" : "Sound: Off";
  soundToggleButton.setAttribute("aria-pressed", String(enabled));
}

function resetScores(localOnly = true) {
  scores.X = 0;
  scores.O = 0;
  scores.draw = 0;
  renderScores();
  if (localOnly) saveScores();
}

function availableMoves() {
  return board.map((cell, idx) => (cell === "" ? idx : -1)).filter((idx) => idx >= 0);
}

function findWinningMove(player) {
  const moves = availableMoves();
  for (const move of moves) {
    board[move] = player;
    const wins = getWinningLine(player) !== null;
    board[move] = "";
    if (wins) return move;
  }
  return null;
}

function pickComputerMove() {
  const winMove = findWinningMove("O");
  if (winMove !== null) return winMove;
  const blockMove = findWinningMove("X");
  if (blockMove !== null) return blockMove;
  if (board[4] === "") return 4;
  const corners = [0, 2, 6, 8].filter((index) => board[index] === "");
  if (corners.length > 0) return corners[Math.floor(Math.random() * corners.length)];
  const moves = availableMoves();
  return moves[Math.floor(Math.random() * moves.length)];
}

function drawBoard() {
  cells.forEach((cell, i) => {
    cell.textContent = board[i];
    // Do NOT use HTML disabled on cells — disabled buttons don't fire click events,
    // so "not your turn" feedback would never run. Lock only filled / ended-game squares.
    cell.disabled = false;
    const locked = board[i] !== "" || !gameActive;
    cell.classList.toggle("cell-disabled", locked);
    cell.setAttribute("aria-disabled", String(locked));
    cell.classList.remove("cell-played", "cell-win");
    if (board[i] !== "") cell.classList.add("cell-played");
  });
}

function highlightWinningLine() {
  const xLine = getWinningLine("X");
  const oLine = getWinningLine("O");
  const winningLine = xLine || oLine;
  if (!winningLine) return;
  winningLine.forEach((index) => cells[index].classList.add("cell-win"));
}

function applyServerState(payload) {
  const previousBoard = lastBoardSnapshot.slice();
  const previousGameActive = lastGameActive;
  board = Array.isArray(payload.board) ? payload.board.slice(0, 9) : Array(9).fill("");
  currentPlayer = payload.currentPlayer === "O" ? "O" : "X";
  gameActive = Boolean(payload.gameActive);
  scores.X = Number(payload.scores?.X) || 0;
  scores.O = Number(payload.scores?.O) || 0;
  scores.draw = Number(payload.scores?.draw) || 0;
  mySymbol = payload.you || "";
  roomCode = payload.room || roomCode;
  isMyTurn = gameActive && mySymbol !== "" && mySymbol === currentPlayer;
  drawBoard();
  highlightWinningLine();
  renderScores();
  // Play move sound when a new mark appears from server updates.
  if (soundEnabled) {
    for (let i = 0; i < board.length; i += 1) {
      if (previousBoard[i] === "" && (board[i] === "X" || board[i] === "O")) {
        playMoveSound(board[i]);
        break;
      }
    }
  }
  if (!gameActive) {
    if (getWinningLine("X")) {
      updateStatus("Player X wins!");
      if (previousGameActive) playWinSound();
    } else if (getWinningLine("O")) {
      updateStatus("Player O wins!");
      if (previousGameActive) playWinSound();
    } else {
      updateStatus("It's a draw!");
      if (previousGameActive) playDrawSound();
    }
  } else if (isMyTurn) {
    updateStatus(`Your turn (${mySymbol})`);
  } else if (mySymbol) {
    updateStatus(`Opponent turn (${currentPlayer})`);
  } else {
    updateStatus("Waiting for opponent...");
  }
  lastBoardSnapshot = board.slice();
  lastGameActive = gameActive;
}

function sendMessage(payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify(payload));
}

function ensureSocketConnected() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  ws = new WebSocket(WS_URL);
  ws.addEventListener("open", () => {
    isConnected = true;
    setOnlineStatus("Connected. Create or join a room.");
  });
  ws.addEventListener("close", () => {
    isConnected = false;
    mySymbol = "";
    roomCode = "";
    isMyTurn = false;
    setOnlineStatus("Disconnected from server.");
  });
  ws.addEventListener("message", (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      setOnlineStatus("Bad message from server.");
      return;
    }
    if (msg.type === "error") {
      const text = msg.message || "Server error.";
      updateStatus(text, { isError: true });
      setOnlineStatus(text);
      return;
    }
    if (msg.type === "room_created") {
      roomInput.value = msg.room;
      setOnlineStatus(`Room ${msg.room} created. Share code with friend.`);
      return;
    }
    if (msg.type === "state") {
      applyServerState(msg);
      setOnlineStatus(`Room ${msg.room} | You: ${msg.you || "-"}`);
    }
  });
}

function finishTurnLocal() {
  const winningLine = getWinningLine(currentPlayer);
  if (winningLine) {
    winningLine.forEach((cellIndex) => cells[cellIndex].classList.add("cell-win"));
    scores[currentPlayer] += 1;
    renderScores();
    saveScores();
    updateStatus(`Player ${currentPlayer} wins!`);
    gameActive = false;
    isComputerThinking = false;
    playWinSound();
    return true;
  }
  if (isDraw()) {
    scores.draw += 1;
    renderScores();
    saveScores();
    updateStatus("It's a draw!");
    gameActive = false;
    isComputerThinking = false;
    playDrawSound();
    return true;
  }
  currentPlayer = currentPlayer === "X" ? "O" : "X";
  updateStatus(gameMode === "cpu" && currentPlayer === "O" ? "Computer is thinking..." : `Player ${currentPlayer}'s turn`);
  return false;
}

function performMove(index) {
  board[index] = currentPlayer;
  cells[index].textContent = currentPlayer;
  cells[index].disabled = false;
  cells[index].classList.add("cell-played", "cell-disabled");
  cells[index].setAttribute("aria-disabled", "true");
  playMoveSound(currentPlayer);
}

function runComputerTurn() {
  if (!gameActive || gameMode !== "cpu" || currentPlayer !== "O") {
    isComputerThinking = false;
    return;
  }
  const move = pickComputerMove();
  if (move === undefined) {
    isComputerThinking = false;
    return;
  }
  performMove(move);
  const ended = finishTurnLocal();
  if (!ended) isComputerThinking = false;
}

function handleBoardClick(event) {
  unlockAudio();
  const cell = event.target.closest("button[data-cell]");
  if (!cell) {
    return;
  }

  const index = [...cells].indexOf(cell);
  if (index < 0) {
    return;
  }

  // Always use the dropdown as source of truth (avoids stale gameMode).
  const mode = gameModeSelect.value;

  if (mode === "cpu") {
    if (board[index] !== "" || !gameActive) {
      return;
    }
    if (isComputerThinking) {
      updateStatus("Wait — the computer is moving.", { isError: true });
      return;
    }
    if (currentPlayer === "O") {
      updateStatus("Not your turn — the computer is playing.", { isError: true });
      return;
    }
    performMove(index);
    const ended = finishTurnLocal();
    if (!ended && currentPlayer === "O") {
      isComputerThinking = true;
      window.setTimeout(runComputerTurn, 350);
    }
    return;
  }

  // Online (pvp) — always send; server validates and replies with error or state
  if (!roomCode || !isConnected) {
    updateStatus("Create or join an online room first.", { isError: true });
    return;
  }
  if (!gameActive) {
    return;
  }
  if (board[index] !== "") {
    return;
  }
  sendMessage({ type: "make_move", room: roomCode, index });
}

function resetGameLocal() {
  board = Array(9).fill("");
  currentPlayer = "X";
  gameActive = true;
  isComputerThinking = false;
  cells.forEach((cell) => {
    cell.textContent = "";
    cell.disabled = false;
    cell.classList.remove("cell-played", "cell-win", "cell-disabled");
    cell.setAttribute("aria-disabled", "false");
  });
  updateStatus("Player X's turn");
  playResetSound();
}

function updateModeUI() {
  onlinePanel.style.display = gameMode === "pvp" ? "block" : "none";
}

if (boardSection) {
  boardSection.addEventListener("click", handleBoardClick);
} else {
  cells.forEach((cell) => cell.addEventListener("click", handleBoardClick));
}

restartButton.addEventListener("click", () => {
  unlockAudio();
  if (gameMode === "pvp" && roomCode) {
    sendMessage({ type: "reset_board", room: roomCode });
  } else {
    resetGameLocal();
  }
});

soundToggleButton.addEventListener("click", () => {
  unlockAudio();
  setSoundState(!soundEnabled);
});

resetScoresButton.addEventListener("click", () => {
  unlockAudio();
  if (gameMode === "pvp" && roomCode) {
    sendMessage({ type: "reset_scores", room: roomCode });
  } else {
    resetScores(true);
  }
});

gameModeSelect.addEventListener("change", () => {
  gameMode = gameModeSelect.value;
  updateModeUI();
  if (gameMode === "cpu") {
    resetGameLocal();
    loadScores();
    renderScores();
  } else {
    resetGameLocal();
    resetScores(false);
    ensureSocketConnected();
    updateStatus("Create or join an online room.");
  }
});

createRoomButton.addEventListener("click", () => {
  unlockAudio();
  ensureSocketConnected();
  if (!isConnected) {
    setOnlineStatus("Connecting...");
    return;
  }
  sendMessage({ type: "create_room" });
});

joinRoomButton.addEventListener("click", () => {
  unlockAudio();
  ensureSocketConnected();
  const room = roomInput.value.trim().toUpperCase();
  if (!room) {
    setOnlineStatus("Enter room code first.");
    return;
  }
  sendMessage({ type: "join_room", room });
});

leaveRoomButton.addEventListener("click", () => {
  unlockAudio();
  if (!roomCode) return;
  sendMessage({ type: "leave_room", room: roomCode });
  roomCode = "";
  mySymbol = "";
  isMyTurn = false;
  updateStatus("Left room. Create or join another.");
});

loadScores();
renderScores();
gameMode = gameModeSelect.value;
updateModeUI();
renderServerAddress();
ensureSocketConnected();

// Ensure first board click always unlocks audio context.
document.addEventListener("pointerdown", unlockAudio, { once: true });

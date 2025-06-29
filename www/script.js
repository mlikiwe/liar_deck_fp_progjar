document.addEventListener("DOMContentLoaded", () => {
  const API_URL = "http://localhost:8889";

  // Global variable to hold the player's ID
  let myPlayerId = null;
  let isPolling = false;

  const opponentsDiv = document.getElementById("opponents");
  const startButton = document.getElementById("start-game-button");
  const logUl = document.getElementById("game-log");
  const actionsDiv = document.getElementById("actions");
  const myHandDiv = document.getElementById("my-hand");
  const playerArea = document.getElementById("player-area");

  // --- Main Functions ---

  async function joinGameAndInitialize() {
    const urlParams = new URLSearchParams(window.location.search);
    const existingPlayerId = urlParams.get("player");

    if (existingPlayerId) {
      myPlayerId = existingPlayerId;
      document.getElementById("player-id").textContent = myPlayerId;
      await getGameState(); // Initial fetch
      pollGameState(); // Start polling
    } else {
      try {
        const response = await fetch(`${API_URL}/game/join`, {
          method: "POST",
        });
        const data = await response.json();

        if (response.ok && data.player_id) {
          myPlayerId = data.player_id;
          const newUrl = `${window.location.pathname}?player=${myPlayerId}`;
          history.pushState({ path: newUrl }, "", newUrl);

          document.getElementById("player-id").textContent = myPlayerId;
          await getGameState(); // Initial fetch
          pollGameState(); // Start polling
        } else {
          alert("Failed to join game: " + (data.message || "Unknown error"));
          logUl.innerHTML = `<li><b>Error:</b> ${data.message}</li>`;
        }
      } catch (error) {
        console.error("Error joining game:", error);
        alert("Could not connect to the server to join the game.");
      }
    }
  }

  function updateUI(state) {
    if (!state) {
      console.log("Skipping UI update due to no state.");
      return;
    }

    opponentsDiv.innerHTML = "";
    logUl.innerHTML = "";

    if (state.log && state.log.length > 0) {
      state.log.forEach((msg) => {
        logUl.innerHTML += `<li>${msg}</li>`;
      });
      logUl.scrollTop = logUl.scrollHeight;
    } else {
      logUl.innerHTML = "<li>Welcome to the game lobby!</li>";
    }

    if (!state.game_started) {
      actionsDiv.style.display = "none";
      myHandDiv.innerHTML = "";
      document.getElementById("table-area").style.display = "none";

      opponentsDiv.innerHTML = "<h3>Players in Lobby:</h3>";
      if (state.assigned_players && state.assigned_players.length > 0) {
        state.assigned_players.forEach((p_id) => {
          const playerText = p_id === myPlayerId ? `${p_id} (You)` : p_id;
          opponentsDiv.innerHTML += `<p>${playerText}</p>`;
        });
      }

      if (myPlayerId === "player1") {
        startButton.textContent = "Start Game";
        startButton.style.display = "block";
      } else {
        startButton.style.display = "none";
        logUl.innerHTML += "<li>Waiting for player1 to start the game...</li>";
      }
    } else if (state.game_winner) {
      actionsDiv.style.display = "none";
      myHandDiv.innerHTML = "";
      document.getElementById("table-area").style.display = "block";

      logUl.innerHTML += `<li><b>Winner is ${state.game_winner}! Game Over.</b></li>`;
      if (myPlayerId === "player1") {
        startButton.textContent = "Play New Game";
        startButton.style.display = "block";
      } else {
        startButton.style.display = "none";
      }
      document.getElementById("current-turn").textContent = "Game Over";
    } else {
      playerArea.style.display = "block";
      document.getElementById("table-area").style.display = "block";
      startButton.style.display = "none";
      actionsDiv.style.display = "block";

      if (state.all_players_card_count) {
        for (const [id, count] of Object.entries(
          state.all_players_card_count
        )) {
          if (id !== myPlayerId) {
            let status = "";
            if (
              state.players_eliminated &&
              state.players_eliminated.includes(id)
            ) {
              status = "(ELIMINATED)";
            }
            opponentsDiv.innerHTML += `<p>${id}: ${count} cards ${status}</p>`;
          }
        }
      }

      if (state.is_eliminated) {
        playerArea.innerHTML = "<h1>You have been eliminated.</h1>";
        actionsDiv.style.display = "none";
        return;
      }

      const isMyTurn = state.current_turn === myPlayerId;

      document.getElementById("ref-card").textContent = state.reference_card;
      document.getElementById("pile-count").textContent = state.card_pile_count;
      document.getElementById("current-turn").textContent = state.current_turn;
      document.getElementById(
        "roulette-index"
      ).textContent = `Roulette Index: ${state.roulette_index}`;

      myHandDiv.innerHTML = "";
      state.your_hand.forEach((card) => {
        const cardDiv = document.createElement("div");
        cardDiv.className = "card";
        cardDiv.textContent = card;
        cardDiv.dataset.cardName = card;
        cardDiv.addEventListener("click", () => {
          if (isMyTurn) {
            cardDiv.classList.toggle("selected");
          }
        });
        myHandDiv.appendChild(cardDiv);
      });

      document.getElementById("play-button").disabled = !isMyTurn;
      document.getElementById("challenge-button").disabled =
        !isMyTurn || state.card_pile_count === 0;
    }
  }

  async function getGameState() {
    if (!myPlayerId) return null;
    try {
      const response = await fetch(
        `${API_URL}/game/state?player_id=${myPlayerId}`
      );
      if (!response.ok) {
        console.error("Failed to get game state, status:", response.status);
        return null;
      }
      const state = await response.json();
      updateUI(state);
      return state;
    } catch (error) {
      console.error("Error fetching game state:", error);
      return null;
    }
  }

  async function pollGameState() {
    if (isPolling) return;
    isPolling = true;

    while (true) {
      const state = await getGameState();
      // Hentikan polling jika game berakhir ATAU jika giliran kita
      if (!state || state.game_winner || state.current_turn === myPlayerId) {
        break;
      }
      // Tunggu 2 detik sebelum polling lagi
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    isPolling = false;
  }

  // --- Event Listeners ---

  startButton.addEventListener("click", async () => {
    try {
      const response = await fetch(`${API_URL}/game/start`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        alert("Error starting game: " + data.message);
      }
      await getGameState();
      pollGameState(); // Mulai polling setelah game dimulai
    } catch (error) {
      console.error("Error starting game:", error);
      alert("Could not start the game.");
    }
  });

  document.getElementById("play-button").addEventListener("click", async () => {
    const selectedCardsNodes = document.querySelectorAll(
      "#my-hand .card.selected"
    );
    const cardsToPlay = Array.from(selectedCardsNodes).map(
      (node) => node.dataset.cardName
    );

    if (cardsToPlay.length === 0) {
      alert("Select at least one card to play.");
      return;
    }

    await fetch(`${API_URL}/game/play`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: myPlayerId, cards: cardsToPlay }),
    });

    // Ambil state terbaru & mulai polling lagi karena giliran kita sudah selesai
    await getGameState();
    pollGameState();
  });

  document
    .getElementById("challenge-button")
    .addEventListener("click", async () => {
      await fetch(`${API_URL}/game/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: myPlayerId }),
      });
      // Ambil state terbaru & mulai polling lagi karena giliran kita sudah selesai
      await getGameState();
      pollGameState();
    });

  // --- Initial Load ---
  joinGameAndInitialize();
});

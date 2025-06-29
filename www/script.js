document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const myPlayerId = urlParams.get("player") || "player1";
  document.getElementById("player-id").textContent = myPlayerId;

  const API_URL = "http://localhost:8889";

  let isPolling = false;

  async function getGameState() {
    try {
      const response = await fetch(
        `${API_URL}/game/state?player_id=${myPlayerId}`
      );
      if (!response.ok) throw new Error("Failed to get game state");
      const state = await response.json();
      updateUI(state);
      return state;
    } catch (error) {
      console.error("Error fetching game state:", error);
      return null;
    }
  }

  function updateUI(state) {
    if (!state) {
      console.log("Skipping UI update due to no state.");
      return;
    }

    const opponentsDiv = document.getElementById("opponents");
    opponentsDiv.innerHTML = "";
    if (state.all_players_card_count) {
      for (const [id, count] of Object.entries(state.all_players_card_count)) {
        if (id !== myPlayerId) {
          const isEliminated =
            state.players_eliminated && state.players_eliminated.includes(id);
          const isWinner = id === state.game_winner;

          let status = "";
          if (isWinner) {
            status = "(WINNER)";
          } else if (isEliminated) {
            status = "(ELIMINATED)";
          }

          opponentsDiv.innerHTML += `<p>${id}: ${count} cards ${status}</p>`;
        }
      }
    }

    const isMyTurn = state.current_turn === myPlayerId;
    const startButton = document.getElementById("start-game-button");
    const logUl = document.getElementById("game-log");

    // 2. Mengatur UI berdasarkan status permainan (tanpa 'return' prematur)
    if (!state.game_started || state.game_winner) {
      document.getElementById("actions").style.display = "none";

      if (state.game_winner) {
        // Game Over
        logUl.innerHTML = `<li><b>Winner is ${state.game_winner}! Game Over.</b></li>`;
        if (myPlayerId === "player1") {
          startButton.textContent = "Play New Game";
          startButton.style.display = "block";
        } else {
          startButton.style.display = "none";
        }
        document.getElementById("my-hand").innerHTML = ""; // Kosongkan tangan
        document.getElementById("current-turn").textContent = "Game Over";
      } else {
        // Sebelum game dimulai
        logUl.innerHTML = "<li>Game has not started.</li>";
        if (myPlayerId === "player1") {
          startButton.textContent = "Start New Game";
          startButton.style.display = "block";
        } else {
          startButton.style.display = "none";
        }
      }
    } else {
      startButton.style.display = "none";
      document.getElementById("actions").style.display = "block";

      document.getElementById("ref-card").textContent = state.reference_card;
      document.getElementById("pile-count").textContent = state.card_pile_count;
      document.getElementById("current-turn").textContent = state.current_turn;
      const rouletteIndex = document.getElementById("roulette-index");
      rouletteIndex.textContent = `Roulette Index: ${state.roulette_index}`;

      logUl.innerHTML = "";
      state.log.forEach((msg) => {
        logUl.innerHTML += `<li>${msg}</li>`;
      });

      if (state.is_eliminated) {
        const playerArea = document.getElementById("player-area");
        playerArea.innerHTML = "<h5>You are eliminated from the game.</h5>";
        document.getElementById("actions").style.display = "none";
      }

      const myHandDiv = document.getElementById("my-hand");
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

  async function pollGameState() {
    if (isPolling) return;
    isPolling = true;

    while (true) {
      const state = await getGameState();
      if (!state || state.game_winner || state.current_turn === myPlayerId) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    isPolling = false;
  }

  const setLoading = (isLoading) => {
    const loadingIndicator =
      document.getElementById("loading-indicator") ||
      (() => {
        const indicator = document.createElement("div");
        indicator.id = "loading-indicator";
        indicator.innerHTML = "Loading...";
        indicator.style.position = "fixed";
        indicator.style.top = "10px";
        indicator.style.right = "10px";
        indicator.style.padding = "8px 12px";
        indicator.style.background = "rgba(0,0,0,0.7)";
        indicator.style.color = "white";
        indicator.style.borderRadius = "4px";
        indicator.style.display = "none";
        document.body.appendChild(indicator);
        return indicator;
      })();

    loadingIndicator.style.display = isLoading ? "block" : "none";
  };

  async function fetchWithLoading(url, options = {}) {
    setLoading(true);
    try {
      const response = await fetch(url, options);
      return response;
    } finally {
      setLoading(false);
    }
  }

  async function getGameState() {
    try {
      const response = await fetchWithLoading(
        `${API_URL}/game/state?player_id=${myPlayerId}`
      );
      if (!response.ok) throw new Error("Failed to get game state");
      const state = await response.json();
      updateUI(state);
      return state;
    } catch (error) {
      console.error("Error fetching game state:", error);
      return null;
    }
  }

  document
    .getElementById("start-game-button")
    .addEventListener("click", async () => {
      await fetchWithLoading(`${API_URL}/game/start`, { method: "POST" });
      await getGameState();
      pollGameState();
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

    await fetchWithLoading(`${API_URL}/game/play`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: myPlayerId, cards: cardsToPlay }),
    });

    await getGameState();
    pollGameState();
  });

  document
    .getElementById("challenge-button")
    .addEventListener("click", async () => {
      await fetchWithLoading(`${API_URL}/game/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: myPlayerId }),
      });
      await getGameState();
      pollGameState();
    });

  getGameState();
  pollGameState();
});

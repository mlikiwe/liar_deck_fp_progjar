document.addEventListener("DOMContentLoaded", () => {
  const API_URL = "http://localhost:8181";

  // Global variable to hold the player's ID
  let myPlayerId = null;
  let isPolling = false;
  let isLoading = false;

  const opponentsDiv = document.getElementById("opponents");
  const startButton = document.getElementById("start-game-button");
  const logUl = document.getElementById("game-log");
  const actionsDiv = document.getElementById("actions");
  const myHandDiv = document.getElementById("my-hand");
  const playerArea = document.getElementById("player-area");

  // Create toast notification instead of loading overlay
  const loadingToast = document.createElement("div");
  loadingToast.id = "loading-toast";
  loadingToast.innerHTML = '<div class="spinner"></div><span>Loading...</span>';
  loadingToast.style.display = "none";
  loadingToast.style.position = "fixed";
  loadingToast.style.top = "20px";
  loadingToast.style.right = "20px";
  loadingToast.style.padding = "10px 15px";
  loadingToast.style.backgroundColor = "#333";
  loadingToast.style.color = "white";
  loadingToast.style.borderRadius = "4px";
  loadingToast.style.zIndex = "1000";
  loadingToast.style.display = "flex";
  loadingToast.style.alignItems = "center";
  loadingToast.style.gap = "10px";
  loadingToast.style.boxShadow = "0 2px 5px rgba(0,0,0,0.3)";
  loadingToast.style.transition = "opacity 0.3s ease-in-out";
  loadingToast.style.opacity = "0";

  // Style for the spinner
  const style = document.createElement("style");
  style.textContent = `
        #loading-toast .spinner {
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    `;
  document.head.appendChild(style);
  document.body.appendChild(loadingToast);

  // Function to show/hide loading toast
  function setLoading(loading) {
    isLoading = loading;
    if (loading) {
      loadingToast.style.display = "flex";
      setTimeout(() => {
        loadingToast.style.opacity = "1";
      }, 10);
    } else {
      loadingToast.style.opacity = "0";
      setTimeout(() => {
        loadingToast.style.display = "none";
      }, 300);
    }
  }

  // --- Main Functions ---

  async function joinGameAndInitialize() {
    const urlParams = new URLSearchParams(window.location.search);
    const existingPlayerId = urlParams.get("player");

    setLoading(true);
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

          localStorage.setItem("auth_key", data.key || ""); // Store auth key if provided

          await getGameState(); // Initial fetch
          pollGameState(); // Start polling
        } else {
          alert("Failed to join game: " + (data.message || "Unknown error"));
          logUl.innerHTML = `<li><b>Error:</b> ${data.message}</li>`;
        }
      } catch (error) {
        console.error("Error joining game:", error);
        alert("Could not connect to the server to join the game.");
      } finally {
        setLoading(false);
      }
    }
  }

  function updateUI(state) {
    setLoading(false);
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
      setLoading(true);
      const response = await fetch(
        `${API_URL}/game/state?player_id=${myPlayerId}`,
        {
          headers: {
            "Content-Type": "application/json",
            "auth-key": localStorage.getItem("auth_key"),
          },
        }
      );
      if (!response.ok) {
        console.error("Failed to get game state, status:", response.status);
        return null;
      }

      const state = await response.json();

      if (!localStorage.getItem("auth_key")) {
        const authKey = state.key;
        if (authKey) {
          localStorage.setItem("auth_key", authKey);
        }
      }
      updateUI(state);
      return state;
    } catch (error) {
      console.error("Error fetching game state:", error);
      setLoading(false);
      return null;
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
      // Tunggu 2 detik sebelum polling lagi
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    isPolling = false;
  }

  startButton.addEventListener("click", async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/game/start`, {
        method: "POST",
        body: JSON.stringify({ key: localStorage.getItem("auth_key") }),
      });
      const data = await response.json();
      if (!response.ok) {
        alert("Error starting game: " + data.message);
        setLoading(false);
      }
      await getGameState();
      await pollGameState(); // Mulai polling setelah game dimulai
    } catch (error) {
      console.error("Error starting game:", error);
      alert("Could not start the game.");
      setLoading(false);
    }
  });

  document.getElementById("play-button").addEventListener("click", async () => {
    const playerKey = localStorage.getItem("auth_key");
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

    try {
      setLoading(true);
      await fetch(`${API_URL}/game/play`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_id: myPlayerId,
          cards: cardsToPlay,
          key: playerKey,
        }),
      });

      // Ambil state terbaru & mulai polling lagi karena giliran kita sudah selesai
      await getGameState();
      await pollGameState();
    } catch (error) {
      console.error("Error playing cards:", error);
      setLoading(false);
      alert("Failed to play cards. Please try again.");
    }
  });

  document
    .getElementById("challenge-button")
    .addEventListener("click", async () => {
      try {
        setLoading(true);
        await fetch(`${API_URL}/game/challenge`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            player_id: myPlayerId,
            key: localStorage.getItem("auth_key"),
          }),
        });
        // Ambil state terbaru & mulai polling lagi karena giliran kita sudah selesai
        await getGameState();
        await pollGameState();
      } catch (error) {
        console.error("Error challenging:", error);
        setLoading(false);
        alert("Failed to challenge. Please try again.");
      }
    });

  // --- Initial Load ---
  joinGameAndInitialize();
});

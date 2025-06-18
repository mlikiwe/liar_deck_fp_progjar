document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const myPlayerId = urlParams.get('player') || 'player1';
    document.getElementById('player-id').textContent = myPlayerId;

    const API_URL = 'http://localhost:8889'; // Sesuaikan port dengan server Anda

    let selectedCardsState = [];
    let isPolling = false; 
    let currentTurnFromServer = null;

    // Fungsi untuk mengambil state game dari server
    async function getGameState() {
        try {
            const response = await fetch(`${API_URL}/game/state?player_id=${myPlayerId}`);
            if (!response.ok) throw new Error('Failed to get game state');
            const state = await response.json();
            updateUI(state);
            // ================== PERBAIKAN KUNCI ==================
            // Kembalikan 'state' agar fungsi lain yang memanggil bisa menggunakannya.
            return state;
            // =======================================================
        } catch (error) {
            console.error('Error fetching game state:', error);
            // Kembalikan null jika terjadi error agar tidak crash
            return null;
        }
    }

    // Fungsi untuk memperbarui tampilan UI berdasarkan state
    function updateUI(state) {
        // Tambahkan pengecekan jika state null
        if (!state) {
            console.log("Skipping UI update due to no state.");
            return;
        }

        const isMyTurn = state.current_turn === myPlayerId;
        console.log("--- Updating UI ---");
        console.log("Data dari Server (state.current_turn):", state.current_turn);
        console.log("ID Player dari URL (myPlayerId):", myPlayerId);
        console.log("Apakah ini giliran saya? (isMyTurn):", isMyTurn);
        
        if (!state.game_started || state.game_winner) {
            document.getElementById('actions').style.display = 'none';
            document.getElementById('start-game-button').style.display = 'block';

            if (state.game_winner) {
                document.getElementById('game-log').innerHTML = `<li><b>Winner is ${state.game_winner}!</b></li>`;
                document.getElementById('start-game-button').style.display = 'none';
            }
            return;
        }

        document.getElementById('start-game-button').style.display = 'none';
        document.getElementById('actions').style.display = 'block';

        document.getElementById('ref-card').textContent = state.reference_card;
        document.getElementById('pile-count').textContent = state.card_pile_count;
        document.getElementById('current-turn').textContent = state.current_turn;

        const myHandDiv = document.getElementById('my-hand');
        myHandDiv.innerHTML = '';
        state.your_hand.forEach(card => {
            const cardDiv = document.createElement('div');
            cardDiv.className = 'card';
            cardDiv.textContent = card;
            cardDiv.dataset.cardName = card;
            if (selectedCardsState.includes(card)) {
                cardDiv.classList.add('selected');
            }
            cardDiv.addEventListener('click', () => {
                if (isMyTurn){
                    const cardName = cardDiv.dataset.cardName;
                    if (selectedCardsState.includes(cardName)) {
                        selectedCardsState = selectedCardsState.filter(c => c !== cardName);
                        cardDiv.classList.remove('selected');
                    } else {
                        selectedCardsState.push(cardName);
                        cardDiv.classList.add('selected');
                    }
                    console.log("Kartu dipilih:", selectedCardsState);
                }
            });
            myHandDiv.appendChild(cardDiv);
        });
        
        const opponentsDiv = document.getElementById('opponents');
        opponentsDiv.innerHTML = '';
        for (const [id, count] of Object.entries(state.all_players_card_count)) {
            if (id !== myPlayerId) {
                const isEliminated = state.players_eliminated.includes(id);
                opponentsDiv.innerHTML += `<p>${id}: ${count} cards ${isEliminated ? '(ELIMINATED)' : ''}</p>`;
            }
        }
        
        const logUl = document.getElementById('game-log');
        logUl.innerHTML = '';
        state.log.forEach(msg => {
            logUl.innerHTML += `<li>${msg}</li>`;
        });
        
        document.getElementById('play-button').disabled = !isMyTurn;
        document.getElementById('challenge-button').disabled = !isMyTurn || state.card_pile_count === 0;
    }

    async function pollGameState() {
        if (isPolling || currentTurnFromServer === myPlayerId) {
            return;
        }

        isPolling = true;
        console.log("Polling started...");

        while (true) {
            const state = await getGameState();
            
            // Dengan perbaikan di getGameState, 'state' sekarang tidak akan undefined
            if (!state || state.game_winner || state.current_turn === myPlayerId) {
                break; 
            }
            await new Promise(resolve => setTimeout(resolve, 2000)); 
        }

        console.log("Polling stopped. It's my turn or game is over.");
        isPolling = false;
    }

    // Aksi tombol
    document.getElementById('start-game-button').addEventListener('click', async () => {
        await fetch(`${API_URL}/game/start`, { method: 'POST' });
        await getGameState();
        pollGameState();
    });

    document.getElementById('play-button').addEventListener('click', async () => {
        const cardsToPlay = selectedCardsState;

        if (cardsToPlay.length === 0) {
            alert("Select at least one card to play.");
            return;
        }
        
        await fetch(`${API_URL}/game/play`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ player_id: myPlayerId, cards: cardsToPlay })
        });

        selectedCardsState = [];
        await getGameState(); // Ambil state setelah aksi
        pollGameState();
    });

    document.getElementById('challenge-button').addEventListener('click', async () => {
        await fetch(`${API_URL}/game/challenge`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ player_id: myPlayerId })
        });
        await getGameState(); // Ambil state setelah aksi
        pollGameState();
    });

    // Panggil getGameState sekali saat halaman dimuat
    getGameState();
});
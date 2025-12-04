// Vänta tills sidan laddat allt
document.addEventListener("DOMContentLoaded", () => {

    // Hämta formulär + input-fält
    const form = document.querySelector("form");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    // Skapa ett meddelandefält under formuläret
    const message = document.createElement("p");
    message.style.color = "red";
    form.appendChild(message);

    // Stoppa formuläret från att ladda om sidan
    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // ← Viktigt!

        // Läs värdena
        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        // Rensa tidigare felmeddelande
        message.textContent = "";

        // --- Enkel frontend-validiering ---
        if (!username || !password) {
            message.textContent = "Ange både användarnamn och lösenord.";
            return;
        }

        if (password.length < 8) {
            message.textContent = "Lösenord måste vara minst 8 tecken.";
            return;
        }

        // --- Skicka användarnamn + lösenord via fetch ---
        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json" // Vi skickar JSON
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            // Ta emot JSON från servern
            const result = await response.json();

            // Lyckad inloggning?
            if (result.success) {
                // Omdirigera till sidan som servern anger
                window.location.href = result.redirect;
            } 
            else {
                // Vid fel lösenord → visa meddelande
                message.textContent = "Fel användarnamn eller lösenord.";

                // Töm lösenordet men behåll användarnamnet
                passwordInput.value = "";
            }

        } catch (error) {
            // Fångar nätverksfel eller serverfel
            message.textContent = "Ett fel uppstod. Försök igen.";
        }
    });
});
// Enkel, selektiv login-handler
// Endast påverkar formulär som postar till /login (action innehåller 'login')
// Visar rött felmeddelande vid misslyckad inloggning utan att ladda om sidan
document.addEventListener("DOMContentLoaded", () => {
	// Välj bara formulär som är avsedda för login
	const loginForm = document.querySelector("form[action*='login']");
	if (!loginForm) return; // Inget login-form på sidan — gör inget

	// Hämta fälten i just detta formulär
	const usernameInput = loginForm.querySelector("#username");
	const passwordInput = loginForm.querySelector("#password");

	// Skapa (eller återanvänd) ett element för felmeddelanden
	let message = loginForm.querySelector('.login-message');
	if (!message) {
		message = document.createElement('p');
		message.className = 'login-message';
		// Enkel inline-styling så att vi inte behöver ändra CSS-filer
		message.style.color = 'red';
		message.style.marginTop = '6px';
		message.style.fontWeight = '600';
		loginForm.appendChild(message);
	}

	// Lyssna endast på submit för login-formuläret
	loginForm.addEventListener('submit', async (event) => {
		// Vi vill stoppa standard-beteendet (sida laddas ej om) endast för detta formulär
		event.preventDefault();

		// Läs värden — försäkra oss om att elementen finns
		const username = usernameInput ? usernameInput.value.trim() : '';
		const password = passwordInput ? passwordInput.value : '';

		// Rensa tidigare meddelande
		message.textContent = '';

		// Enkel klientvalidering (inte för strikt)
		if (!username || !password) {
			message.textContent = 'Ange både användarnamn och lösenord.';
			if (passwordInput) passwordInput.value = '';
			return;
		}

		// Skicka som JSON till servern (servern förväntar sig JSON för AJAX)
		try {
			const res = await fetch(loginForm.action || '/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password }),
			});

			// Försök parse JSON; om servern returnerar 400/500 kan detta misslyckas
			let data;
			try { data = await res.json(); } catch (e) { data = null; }

			if (res.ok && data && data.success) {
				// Lyckad inloggning — navigera till redirect (från server)
				window.location.href = data.redirect || '/recipe';
				return;
			}

			// Misslyckad inloggning — visa fel och töm lösenordsfältet
			message.textContent = (data && data.message) ? data.message : 'Fel användarnamn eller lösenord.';
			if (passwordInput) passwordInput.value = '';

		} catch (err) {
			// Nätverksfel eller annat. Visa generiskt fel men påverka inte andra formulär
			message.textContent = 'Ett fel uppstod. Försök igen.';
			if (passwordInput) passwordInput.value = '';
		}
	});
});

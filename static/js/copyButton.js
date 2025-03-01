document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;
    const navbar = document.getElementById("navbar");
    const videoDetails = document.getElementById("videoDetails");
    const button = document.getElementById("theme-toggle");

    // Load theme preference
    const theme = localStorage.getItem("theme");

    if (theme === "light") {
        body.classList.remove("bg-dark", "text-white");
        body.classList.add("bg-light", "text-dark");
        navbar.classList.remove("navbar-dark", "bg-dark");
        navbar.classList.add("navbar-light", "bg-light");
        if (videoDetails) {
            videoDetails.classList.add("bg-light", "text-dark");
        }
        button.textContent = "🌙 Dark Mode";
        button.classList.replace("btn-outline-light", "btn-outline-dark");
    } else {
        body.classList.remove("bg-light", "text-dark");
        body.classList.add("bg-dark", "text-white");
        navbar.classList.remove("navbar-light", "bg-light");
        navbar.classList.add("navbar-dark", "bg-dark");
        if (videoDetails) {
            videoDetails.classList.add("bg-dark", "text-white");
        }
        button.textContent = "☀️ Light Mode";
        button.classList.replace("btn-outline-dark", "btn-outline-light");
    }

    function toggleTheme() {
        if (body.classList.contains("bg-dark")) {
            body.classList.remove("bg-dark", "text-white");
            body.classList.add("bg-light", "text-dark");
            navbar.classList.remove("navbar-dark", "bg-dark");
            navbar.classList.add("navbar-light", "bg-light");
            if (videoDetails) {
                videoDetails.classList.remove("bg-dark", "text-white");
                videoDetails.classList.add("bg-light", "text-dark");
            }
            localStorage.setItem("theme", "light");
            button.textContent = "🌙 Dark Mode";
            button.classList.replace("btn-outline-light", "btn-outline-dark");
        } else {
            body.classList.remove("bg-light", "text-dark");
            body.classList.add("bg-dark", "text-white");
            navbar.classList.remove("navbar-light", "bg-light");
            navbar.classList.add("navbar-dark", "bg-dark");
            if (videoDetails) {
                videoDetails.classList.remove("bg-light", "text-dark");
                videoDetails.classList.add("bg-dark", "text-white");
            }
            localStorage.setItem("theme", "dark");
            button.textContent = "☀️ Light Mode";
            button.classList.replace("btn-outline-dark", "btn-outline-light");
        }
    }

    function copyToClipboard() {
        const videoDetails = document.getElementById("videoDetails");  // Ensure element exists
        if (!videoDetails) {
            alert("No video details available to copy.");
            return;
        }
        
        let text = videoDetails.innerText;
        navigator.clipboard.writeText(text).then(() => {
            alert("Copied to clipboard!");
        }).catch(err => {
            console.error("Could not copy text: ", err);
            alert("Failed to copy.");
        });
    }

    // Attach event listeners
    button.addEventListener("click", toggleTheme);
    document.getElementById("copy-button")?.addEventListener("click", copyToClipboard);
});
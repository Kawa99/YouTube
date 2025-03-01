document.addEventListener("DOMContentLoaded", function () {
    console.log("Theme script loaded!"); // Debugging log

    const body = document.body;
    const navbar = document.getElementById("navbar");
    const videoDetails = document.getElementById("videoDetails");
    const button = document.getElementById("theme-toggle");

    if (!button) {
        console.error("Theme toggle button not found!"); // Debugging log
        return;
    }

    console.log("Theme toggle button found:", button); // Debugging log

    let theme = localStorage.getItem("theme") || "dark";

    function applyTheme(theme) {
        console.log("Applying theme:", theme); // Debugging log

        if (theme === "light") {
            body.classList.remove("bg-dark", "text-white");
            body.classList.add("bg-light", "text-dark");
            navbar.classList.remove("navbar-dark", "bg-dark");
            navbar.classList.add("navbar-light", "bg-light");
            if (videoDetails) {
                videoDetails.classList.remove("bg-dark", "text-white");
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
                videoDetails.classList.remove("bg-light", "text-dark");
                videoDetails.classList.add("bg-dark", "text-white");
            }
            button.textContent = "☀️ Light Mode";
            button.classList.replace("btn-outline-dark", "btn-outline-light");
        }
    }

    applyTheme(theme);

    function toggleTheme() {
        console.log("Toggling theme..."); // Debugging log
        theme = theme === "dark" ? "light" : "dark";
        localStorage.setItem("theme", theme);
        applyTheme(theme);
    }

    button.addEventListener("click", toggleTheme);
});

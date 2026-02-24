(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const moonIcon = '<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M17.293 13.293A8 8 0 016.707 2.707a.75.75 0 00-.87-.22A8.5 8.5 0 1017.513 14.16a.75.75 0 00-.22-.867z"></path></svg>';
    const sunIcon = '<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10 4.5a.75.75 0 01.75.75v1a.75.75 0 01-1.5 0v-1A.75.75 0 0110 4.5zm0 9a.75.75 0 01.75.75v1a.75.75 0 01-1.5 0v-1A.75.75 0 0110 13.5zm5.5-3.5a.75.75 0 01.75.75v.5a.75.75 0 01-1.5 0v-.5a.75.75 0 01.75-.75zM4.5 10a.75.75 0 01.75.75v.5a.75.75 0 01-1.5 0v-.5A.75.75 0 014.5 10zm8.36-4.11a.75.75 0 011.06 0l.7.7a.75.75 0 11-1.06 1.06l-.7-.7a.75.75 0 010-1.06zm-6.78 6.78a.75.75 0 011.06 0l.7.7a.75.75 0 11-1.06 1.06l-.7-.7a.75.75 0 010-1.06zm7.48 1.76a.75.75 0 010 1.06l-.7.7a.75.75 0 11-1.06-1.06l.7-.7a.75.75 0 011.06 0zM7.14 6.3a.75.75 0 010 1.06l-.7.7A.75.75 0 115.38 7l.7-.7a.75.75 0 011.06 0zM10 7.25a3.5 3.5 0 100 7 3.5 3.5 0 000-7z"></path></svg>';

    function getSystemTheme() {
        return mediaQuery.matches ? "dark" : "light";
    }

    function updateThemeToggleButton(theme) {
        const button = document.getElementById("theme-toggle");
        if (!button) return;

        const isDark = theme === "dark";
        button.classList.add("inline-flex", "items-center", "justify-center");
        button.innerHTML = `${isDark ? moonIcon : sunIcon}<span class="sr-only">Theme follows your system setting</span>`;

        button.setAttribute("title", "Theme follows your system setting");
        button.setAttribute("aria-label", "Theme follows your system setting");
    }

    function applyTheme(theme) {
        const root = document.documentElement;
        root.classList.toggle("dark", theme === "dark");
        updateThemeToggleButton(theme);
    }

    function handleSystemThemeChange(event) {
        applyTheme(event.matches ? "dark" : "light");
    }

    function copyToClipboard() {
        const videoDetails = document.getElementById("videoDetails");
        if (!videoDetails) {
            if (window.Toastify) {
                Toastify({
                    text: "No video details available to copy.",
                    duration: 2500,
                    gravity: "bottom",
                    position: "right",
                    close: true,
                    style: { background: "#d97706", color: "#f8fafc" },
                }).showToast();
            }
            return;
        }

        const text = videoDetails.innerText;
        navigator.clipboard.writeText(text).then(() => {
            if (window.Toastify) {
                Toastify({
                    text: "Copied to clipboard.",
                    duration: 2000,
                    gravity: "bottom",
                    position: "right",
                    close: true,
                    style: { background: "#15803d", color: "#f8fafc" },
                }).showToast();
            }
        }).catch((err) => {
            console.error("Could not copy text:", err);
            if (window.Toastify) {
                Toastify({
                    text: "Failed to copy details.",
                    duration: 2500,
                    gravity: "bottom",
                    position: "right",
                    close: true,
                    style: { background: "#b91c1c", color: "#f8fafc" },
                }).showToast();
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(getSystemTheme());

        const copyButton = document.getElementById("copy-button");
        copyButton?.addEventListener("click", copyToClipboard);

        if (typeof mediaQuery.addEventListener === "function") {
            mediaQuery.addEventListener("change", handleSystemThemeChange);
        } else if (typeof mediaQuery.addListener === "function") {
            mediaQuery.addListener(handleSystemThemeChange);
        }
    });
})();

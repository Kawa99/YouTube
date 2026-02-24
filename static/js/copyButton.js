(() => {
    const THEME_STORAGE_KEY = "theme_preference";
    const THEME_VALUES = ["system", "light", "dark"];
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    function safeGetStorage(key) {
        try {
            return localStorage.getItem(key);
        } catch (_) {
            return null;
        }
    }

    function safeSetStorage(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (_) {
            // Ignore storage failures (private mode, blocked storage, etc.)
        }
    }

    function getStoredThemePreference() {
        const stored = safeGetStorage(THEME_STORAGE_KEY);
        if (THEME_VALUES.includes(stored)) {
            return stored;
        }

        const legacyTheme = safeGetStorage("theme");
        if (legacyTheme === "light" || legacyTheme === "dark") {
            return legacyTheme;
        }

        return "system";
    }

    function getEffectiveTheme(preference) {
        if (preference === "system") {
            return mediaQuery.matches ? "dark" : "light";
        }
        return preference;
    }

    function updateThemeToggleButton(preference, effectiveTheme) {
        const button = document.getElementById("theme-toggle");
        if (!button) return;

        if (preference === "system") {
            button.textContent = `Theme: Auto (${effectiveTheme === "dark" ? "Dark" : "Light"})`;
        } else if (preference === "dark") {
            button.textContent = "Theme: Dark";
        } else {
            button.textContent = "Theme: Light";
        }

        button.setAttribute("title", "Click to cycle theme: Auto -> Light -> Dark");
        button.setAttribute("aria-label", button.textContent);
    }

    function applyTheme(preference) {
        const effectiveTheme = getEffectiveTheme(preference);
        const root = document.documentElement;

        root.setAttribute("data-theme-preference", preference);
        root.setAttribute("data-theme", effectiveTheme);
        root.classList.toggle("dark", effectiveTheme === "dark");

        updateThemeToggleButton(preference, effectiveTheme);
    }

    function cycleThemePreference() {
        const current = getStoredThemePreference();
        const currentIndex = THEME_VALUES.indexOf(current);
        const nextPreference = THEME_VALUES[(currentIndex + 1) % THEME_VALUES.length];

        safeSetStorage(THEME_STORAGE_KEY, nextPreference);
        applyTheme(nextPreference);
    }

    function handleSystemThemeChange() {
        if (getStoredThemePreference() === "system") {
            applyTheme("system");
        }
    }

    function copyToClipboard() {
        const videoDetails = document.getElementById("videoDetails");
        if (!videoDetails) {
            if (window.Toastify) {
                Toastify({
                    text: "No video details available to copy.",
                    duration: 2500,
                    gravity: "top",
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
                    gravity: "top",
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
                    gravity: "top",
                    position: "right",
                    close: true,
                    style: { background: "#b91c1c", color: "#f8fafc" },
                }).showToast();
            }
        });
    }

    // Apply theme as early as possible to reduce flash before the page is interactive.
    applyTheme(getStoredThemePreference());

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(getStoredThemePreference());

        const toggleButton = document.getElementById("theme-toggle");
        toggleButton?.addEventListener("click", cycleThemePreference);

        const copyButton = document.getElementById("copy-button");
        copyButton?.addEventListener("click", copyToClipboard);

        if (typeof mediaQuery.addEventListener === "function") {
            mediaQuery.addEventListener("change", handleSystemThemeChange);
        } else if (typeof mediaQuery.addListener === "function") {
            mediaQuery.addListener(handleSystemThemeChange);
        }
    });
})();

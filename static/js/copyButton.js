(() => {
    const THEME_STORAGE_KEY = "theme";
    const THEME_VALUES = ["auto", "light", "dark"];
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const autoIcon = '<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M4.5 4.75A2.75 2.75 0 017.25 2h5.5a2.75 2.75 0 012.75 2.75v6.5A2.75 2.75 0 0112.75 14h-1v1.25h2a.75.75 0 010 1.5h-7.5a.75.75 0 010-1.5h2V14h-1a2.75 2.75 0 01-2.75-2.75v-6.5zM7.25 3.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h5.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25h-5.5z"></path></svg>';
    const moonIcon = '<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M17.293 13.293A8 8 0 016.707 2.707a.75.75 0 00-.87-.22A8.5 8.5 0 1017.513 14.16a.75.75 0 00-.22-.867z"></path></svg>';
    const sunIcon = '<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10 4.5a.75.75 0 01.75.75v1a.75.75 0 01-1.5 0v-1A.75.75 0 0110 4.5zm0 9a.75.75 0 01.75.75v1a.75.75 0 01-1.5 0v-1A.75.75 0 0110 13.5zm5.5-3.5a.75.75 0 01.75.75v.5a.75.75 0 01-1.5 0v-.5a.75.75 0 01.75-.75zM4.5 10a.75.75 0 01.75.75v.5a.75.75 0 01-1.5 0v-.5A.75.75 0 014.5 10zm8.36-4.11a.75.75 0 011.06 0l.7.7a.75.75 0 11-1.06 1.06l-.7-.7a.75.75 0 010-1.06zm-6.78 6.78a.75.75 0 011.06 0l.7.7a.75.75 0 11-1.06 1.06l-.7-.7a.75.75 0 010-1.06zm7.48 1.76a.75.75 0 010 1.06l-.7.7a.75.75 0 11-1.06-1.06l.7-.7a.75.75 0 011.06 0zM7.14 6.3a.75.75 0 010 1.06l-.7.7A.75.75 0 115.38 7l.7-.7a.75.75 0 011.06 0zM10 7.25a3.5 3.5 0 100 7 3.5 3.5 0 000-7z"></path></svg>';

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

    function getThemePreference() {
        const stored = safeGetStorage(THEME_STORAGE_KEY);
        return THEME_VALUES.includes(stored) ? stored : "auto";
    }

    function getSystemTheme() {
        return mediaQuery.matches ? "dark" : "light";
    }

    function getEffectiveTheme(preference) {
        if (preference === "auto") {
            return getSystemTheme();
        }
        return preference;
    }

    function updateThemeToggleButton(preference, effectiveTheme) {
        const button = document.getElementById("theme-toggle");
        if (!button) return;

        const icon = preference === "auto" ? autoIcon : (effectiveTheme === "dark" ? moonIcon : sunIcon);
        const label = preference === "auto"
            ? `Automatic (${effectiveTheme === "dark" ? "dark" : "light"})`
            : `${effectiveTheme === "dark" ? "Dark mode" : "Light mode"}`;

        button.classList.add("inline-flex", "items-center", "justify-center");
        button.innerHTML = `${icon}<span class="sr-only">${label}</span>`;

        button.setAttribute("title", `Theme: ${label}`);
        button.setAttribute("aria-label", `Theme: ${label}`);
    }

    function updateThemeMenuState(preference) {
        const options = document.querySelectorAll("#theme-menu .theme-option");
        options.forEach((option) => {
            const isActive = option.dataset.themeValue === preference;
            option.classList.toggle("bg-slate-100", isActive);
            option.classList.toggle("text-slate-900", isActive);
            option.classList.toggle("dark:bg-slate-800", isActive);
            option.classList.toggle("dark:text-slate-100", isActive);
        });
    }

    function applyThemePreference(preference) {
        const effectiveTheme = getEffectiveTheme(preference);
        const root = document.documentElement;
        root.classList.toggle("dark", effectiveTheme === "dark");
        updateThemeToggleButton(preference, effectiveTheme);
        updateThemeMenuState(preference);
    }

    function handleSystemThemeChange(event) {
        if (getThemePreference() === "auto") {
            applyThemePreference("auto");
        }
    }

    function closeThemeMenu() {
        const menu = document.getElementById("theme-menu");
        const button = document.getElementById("theme-toggle");
        if (!menu || !button) return;
        menu.classList.add("hidden");
        button.setAttribute("aria-expanded", "false");
    }

    function toggleThemeMenu() {
        const menu = document.getElementById("theme-menu");
        const button = document.getElementById("theme-toggle");
        if (!menu || !button) return;

        const willOpen = menu.classList.contains("hidden");
        menu.classList.toggle("hidden");
        button.setAttribute("aria-expanded", String(willOpen));
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
        applyThemePreference(getThemePreference());

        const themeToggle = document.getElementById("theme-toggle");
        const themeMenu = document.getElementById("theme-menu");
        themeToggle?.addEventListener("click", function (event) {
            event.stopPropagation();
            toggleThemeMenu();
        });
        themeMenu?.addEventListener("click", function (event) {
            const option = event.target.closest("[data-theme-value]");
            if (!option) return;

            const nextPreference = option.dataset.themeValue;
            if (!THEME_VALUES.includes(nextPreference)) return;
            safeSetStorage(THEME_STORAGE_KEY, nextPreference);
            applyThemePreference(nextPreference);
            closeThemeMenu();
        });

        document.addEventListener("click", function (event) {
            if (!themeMenu || !themeToggle) return;
            if (!themeMenu.contains(event.target) && !themeToggle.contains(event.target)) {
                closeThemeMenu();
            }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeThemeMenu();
            }
        });

        const copyButton = document.getElementById("copy-button");
        copyButton?.addEventListener("click", copyToClipboard);

        if (typeof mediaQuery.addEventListener === "function") {
            mediaQuery.addEventListener("change", handleSystemThemeChange);
        } else if (typeof mediaQuery.addListener === "function") {
            mediaQuery.addListener(handleSystemThemeChange);
        }
    });
})();

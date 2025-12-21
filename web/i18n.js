/**
 * i18n - Internationalization Module
 * Supports English (en) and Vietnamese (vi)
 */

(function () {
    // Default language
    const DEFAULT_LANG = 'vi';
    const STORAGE_KEY = 'fourt_language';

    // Translations cache
    let translations = null;
    let currentLang = DEFAULT_LANG;

    // Initialize
    async function init() {
        // Load saved language preference
        currentLang = localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;

        // Load translations
        try {
            const response = await fetch('/translations.json');
            translations = await response.json();
        } catch (error) {
            console.error('[i18n] Failed to load translations:', error);
            return;
        }

        // Apply translations
        applyTranslations();

        // Setup language toggle
        setupToggle();

        // Update toggle UI
        updateToggleUI();
    }

    // Apply translations to all elements with data-i18n attribute
    function applyTranslations() {
        if (!translations || !translations[currentLang]) return;

        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (translations[currentLang][key]) {
                el.textContent = translations[currentLang][key];
            }
        });

        // Also apply to placeholders
        const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
        placeholderElements.forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (translations[currentLang][key]) {
                el.placeholder = translations[currentLang][key];
            }
        });

        // Update HTML lang attribute
        document.documentElement.lang = currentLang;
    }

    // Setup language toggle click handler
    function setupToggle() {
        const toggle = document.getElementById('langToggle');
        if (!toggle) return;

        toggle.addEventListener('click', () => {
            // Toggle language
            currentLang = currentLang === 'en' ? 'vi' : 'en';

            // Save preference
            localStorage.setItem(STORAGE_KEY, currentLang);

            // Apply translations
            applyTranslations();

            // Update toggle UI
            updateToggleUI();
        });
    }

    // Update toggle button appearance
    function updateToggleUI() {
        const toggle = document.getElementById('langToggle');
        if (!toggle) return;

        const flagEn = toggle.querySelector('.flag-en');
        const flagVi = toggle.querySelector('.flag-vi');

        if (currentLang === 'en') {
            flagEn?.classList.add('active');
            flagVi?.classList.remove('active');
        } else {
            flagVi?.classList.add('active');
            flagEn?.classList.remove('active');
        }
    }

    // Get translation by key
    function t(key) {
        if (!translations || !translations[currentLang]) return key;
        return translations[currentLang][key] || key;
    }

    // Get current language
    function getLang() {
        return currentLang;
    }

    // Set language
    function setLang(lang) {
        if (lang !== 'en' && lang !== 'vi') return;
        currentLang = lang;
        localStorage.setItem(STORAGE_KEY, lang);
        applyTranslations();
        updateToggleUI();
    }

    // Expose to window
    window.i18n = {
        init,
        t,
        getLang,
        setLang,
        applyTranslations
    };

    // Auto-init when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

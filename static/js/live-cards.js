/**
 * AgroCaua — Live Card Animation Helpers
 * Provides smooth real-time animations for KPI cards across all dashboard pages.
 * Requires: agro.css (card-float, ring-pulse, value-flash, live-dot keyframes)
 */

const LiveCards = (() => {

    /**
     * Animate a value element when new data arrives.
     * Adds .kpi-value--updated class which triggers a flash + scale animation.
     * @param {HTMLElement|string} el  — element or ID
     * @param {string} newText         — new text to display
     */
    function animateValue(el, newText) {
        if (typeof el === 'string') el = document.getElementById(el);
        if (!el || el.textContent === newText) return;
        el.textContent = newText;
        el.classList.remove('kpi-value--updated');
        void el.offsetWidth; // force reflow to restart animation
        el.classList.add('kpi-value--updated');
        setTimeout(() => el.classList.remove('kpi-value--updated'), 600);
    }

    /**
     * Mark a KPI card as "live" — shows the pulsing ring on the icon wrapper
     * and reveals the live-dot indicator in the label.
     * @param {HTMLElement|string} card   — card element or ID
     * @param {string} [colorClass]       — 'green' | 'blue' | 'amber' | 'red' | 'teal'
     */
    function setLive(card, colorClass) {
        if (typeof card === 'string') card = document.getElementById(card);
        if (!card) return;
        card.classList.add('kpi-card--live');
        if (colorClass) card.classList.add(colorClass);
        // Show the live-dot inside the card label
        const dot = card.querySelector('.live-dot');
        if (dot) dot.style.display = 'inline-block';
    }

    /**
     * Set all kpi-cards on the page as live, with staggered delay.
     * @param {string} [colorClass] — default colour for all cards
     */
    function setAllLive(colorClass = 'green') {
        document.querySelectorAll('.kpi-card').forEach((card, i) => {
            setTimeout(() => setLive(card, colorClass), i * 150);
        });
    }

    /**
     * Inject a live-dot span into a label element if not already present.
     * @param {HTMLElement|string} labelEl — label element or selector
     * @param {string} [dotClass]          — extra class e.g. 'blue', 'amber'
     */
    function injectLiveDot(labelEl, dotClass = '') {
        if (typeof labelEl === 'string') labelEl = document.querySelector(labelEl);
        if (!labelEl) return;
        if (labelEl.querySelector('.live-dot')) return; // already injected
        const dot = document.createElement('span');
        dot.className = `live-dot${dotClass ? ' ' + dotClass : ''}`;
        dot.style.display = 'none';
        labelEl.prepend(dot);
    }

    /**
     * Trigger a brief "data received" highlight on a card border.
     * Useful for when a sensor card gets new data via SSE/polling.
     * @param {HTMLElement|string} card
     */
    function flashCard(card) {
        if (typeof card === 'string') card = document.getElementById(card);
        if (!card) return;
        card.style.transition = 'border-color 0.1s ease, box-shadow 0.1s ease';
        card.style.borderColor = '#4ade80';
        card.style.boxShadow = '0 0 0 3px rgba(74,222,128,0.25)';
        setTimeout(() => {
            card.style.borderColor = '';
            card.style.boxShadow = '';
            card.style.transition = '';
        }, 800);
    }

    /**
     * Count-up animation for a numeric value.
     * @param {HTMLElement|string} el
     * @param {number} from
     * @param {number} to
     * @param {string} [suffix]   — e.g. '°C', '%', ' hPa'
     * @param {number} [duration] — ms, default 600
     */
    function countUp(el, from, to, suffix = '', duration = 600) {
        if (typeof el === 'string') el = document.getElementById(el);
        if (!el || isNaN(to)) return;
        const start = performance.now();
        function step(now) {
            const t = Math.min((now - start) / duration, 1);
            // ease-out cubic
            const ease = 1 - Math.pow(1 - t, 3);
            const val = from + (to - from) * ease;
            el.textContent = val.toFixed(1) + suffix;
            if (t < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }

    /**
     * Stagger-animate a list of cards on page load.
     * Adds .card-animate-in class with increasing delays.
     * @param {string} [selector] — default '.kpi-card, .card'
     */
    function staggerEntrance(selector = '.kpi-card') {
        document.querySelectorAll(selector).forEach((card, i) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(14px)';
            setTimeout(() => {
                card.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 80 + i * 90);
        });
    }

    // Public API
    return { animateValue, setLive, setAllLive, injectLiveDot, flashCard, countUp, staggerEntrance };
})();
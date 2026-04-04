/**
 * AgroCaua Data Formatters
 * Functions for formatting dates, numbers, and sensor values
 */

/**
 * Format ISO timestamp to Portuguese locale
 */
function formatTimestamp(isoString) {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleString('pt-PT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return 'N/A';
  }
}

/**
 * Format ISO date only
 */
function formatDate(isoString) {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('pt-PT');
  } catch (e) {
    return 'N/A';
  }
}

/**
 * Format time only
 */
function formatTime(isoString) {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('pt-PT', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return 'N/A';
  }
}

/**
 * Format temperature with °C
 */
function formatTemperature(temp) {
  return temp != null ? `${temp.toFixed(1)}°C` : 'N/A';
}

/**
 * Format humidity with %
 */
function formatHumidity(humidity) {
  return humidity != null ? `${humidity.toFixed(1)}%` : 'N/A';
}

/**
 * Format pressure with hPa
 */
function formatPressure(pressure) {
  return pressure != null ? `${pressure.toFixed(1)} hPa` : 'N/A';
}

/**
 * Format GPS coordinates
 */
function formatCoordinate(coord, decimals = 6) {
  return coord != null ? coord.toFixed(decimals) : 'N/A';
}

/**
 * Format confidence as percentage
 */
function formatConfidence(confidence) {
  return confidence != null ? `${(confidence * 100).toFixed(0)}%` : 'N/A';
}

/**
 * Format boolean detection
 */
function formatDetection(detected) {
  return detected === true ? 'Sim' : detected === false ? 'Não' : 'N/A';
}

/**
 * Get status badge class based on value and thresholds
 */
function getStatusClass(value, thresholds = {}) {
  if (value == null) return 'badge-info';

  const { warning = 70, danger = 90 } = thresholds;

  if (value < warning) return 'badge-success';
  if (value < danger) return 'badge-warning';
  return 'badge-danger';
}

/**
 * Get time ago string
 */
function timeAgo(isoString) {
  if (!isoString) return 'N/A';

  try {
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'há poucos segundos';
    if (seconds < 3600) return `há ${Math.floor(seconds / 60)} minutos`;
    if (seconds < 86400) return `há ${Math.floor(seconds / 3600)} horas`;
    return `há ${Math.floor(seconds / 86400)} dias`;
  } catch (e) {
    return 'N/A';
  }
}

/**
 * ── Realtime UI helpers ──
 * Animate KPI card value changes and manage live state
 */

/**
 * Update a KPI value element with a flash animation.
 * Usage: setKpiValue('myId', '42.1°C')
 */
function setKpiValue(elementId, newValue) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (el.textContent === newValue) return; // no change
  el.textContent = newValue;
  el.classList.remove('kpi-value--updated');
  // Force reflow so animation restarts
  void el.offsetWidth;
  el.classList.add('kpi-value--updated');
  // Clean up class after animation
  setTimeout(() => el.classList.remove('kpi-value--updated'), 600);
}

/**
 * Mark a KPI card as "live" (shows pulsing ring on icon).
 * Pass the card element or its id.
 */
function setCardLive(cardOrId, isLive = true) {
  const el = typeof cardOrId === 'string' ? document.getElementById(cardOrId) : cardOrId;
  if (!el) return;
  if (isLive) {
    el.classList.add('kpi-card--live');
  } else {
    el.classList.remove('kpi-card--live');
  }
}

/**
 * Stagger-animate a list of elements on entry.
 * Usage: animateEnter(document.querySelectorAll('.sensor-card'))
 */
function animateEnter(elements, baseDelayMs = 60) {
  Array.from(elements).forEach((el, i) => {
    el.style.animationDelay = `${i * baseDelayMs}ms`;
    el.classList.add('card-animate-in');
  });
}

/**
 * Create or update a live dot span inside a container.
 * Usage: renderLiveDot('statusEl', 'green')  // color: green | red | amber | blue
 */
function renderLiveDot(containerId, color = '') {
  const el = document.getElementById(containerId);
  if (!el) return;
  let dot = el.querySelector('.live-dot');
  if (!dot) {
    dot = document.createElement('span');
    dot.className = 'live-dot';
    el.prepend(dot);
  }
  dot.className = `live-dot${color ? ' ' + color : ''}`;
}
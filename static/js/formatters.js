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

/**
 * AgroCaua Notification System
 * Toast notifications for user feedback
 */

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
  // Remove existing toast if any
  const existingToast = document.querySelector('.toast');
  if (existingToast) {
    existingToast.remove();
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type} fade-in`;
  
  const iconMap = {
    success: 'check-circle',
    error: 'alert-circle',
    warning: 'alert-triangle',
    info: 'bell'
  };
  
  toast.innerHTML = `
    <i class="icon-${iconMap[type] || 'bell'}"></i>
    <span>${message}</span>
  `;
  
  // Toast styles
  toast.style.cssText = `
    position: fixed;
    top: 2rem;
    right: 2rem;
    padding: 1rem 1.5rem;
    border-radius: 0.75rem;
    background: white;
    box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.1);
    border: 1px solid var(--color-gray-200);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    z-index: 9999;
    min-width: 300px;
    max-width: 500px;
  `;
  
  // Type-specific styling
  const colors = {
    success: 'var(--color-success)',
    error: 'var(--color-danger)',
    warning: 'var(--color-warning)',
    info: 'var(--color-info)'
  };
  
  toast.querySelector('i').style.color = colors[type] || colors.info;
  
  document.body.appendChild(toast);
  
  // Auto remove after 5 seconds
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'all 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}

/**
 * Show success message
 */
function showSuccess(message) {
  showToast(message, 'success');
}

/**
 * Show error message
 */
function showError(message) {
  showToast(message, 'error');
}

/**
 * Show warning message
 */
function showWarning(message) {
  showToast(message, 'warning');
}

/**
 * Show info message
 */
function showInfo(message) {
  showToast(message, 'info');
}

/**
 * Show loading indicator
 */
function showLoading(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.classList.add('loading');
  }
}

/**
 * Hide loading indicator
 */
function hideLoading(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.classList.remove('loading');
  }
}

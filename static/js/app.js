/**
 * AbhiApp - Core Application Script
 */

// Theme Management (Light / Dark Appearance)
function initTheme() {
  const savedTheme = localStorage.getItem('abhiapp-theme') || 'dark';
  applyTheme(savedTheme, false);
}

function applyTheme(theme, notify = true) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('abhiapp-theme', theme);
  
  // Update toggle buttons across UI
  const themeBtns = document.querySelectorAll('.theme-toggle-btn');
  themeBtns.forEach(btn => {
    if (theme === 'light') {
      btn.innerHTML = '<span>🌙</span> <span class="theme-btn-label">Dark</span>';
      btn.title = 'Switch to Dark Mode';
    } else {
      btn.innerHTML = '<span>☀️</span> <span class="theme-btn-label">Light</span>';
      btn.title = 'Switch to Light Mode';
    }
  });

  const themeSelect = document.getElementById('settingsThemeSelect');
  if (themeSelect) {
    themeSelect.value = theme;
  }

  if (notify) {
    showToast(`Switched to ${theme.toUpperCase()} appearance`, 'info');
  }
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  applyTheme(newTheme, true);
}

// Immediately apply saved theme on load
initTheme();

// Global Toast Notification Helper
function showToast(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '⚠️';

  toast.innerHTML = `
    <span>${icon}</span>
    <div style="flex:1;">${message}</div>
    <button onclick="this.parentElement.remove()" style="background:transparent;border:none;color:#94a3b8;cursor:pointer;">&times;</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Modal Management Helper
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Close modals when clicking backdrop
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});

// Mobile Sidebar Toggle
function toggleMobileSidebar() {
  const sidebar = document.getElementById('mainSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) {
    sidebar.classList.toggle('open');
    if (backdrop) {
      backdrop.classList.toggle('active');
    }
  }
}

// Global keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.active').forEach(m => m.classList.remove('active'));
    document.body.style.overflow = '';
  }
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault();
    const searchInput = document.getElementById('globalSearchInput');
    if (searchInput) searchInput.focus();
  }
});

// Global Search Redirection to Vault
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  const searchInput = document.getElementById('globalSearchInput');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (window.location.pathname.includes('/vault')) {
          if (window.loadVaultFiles) {
            window.loadVaultFiles();
          }
        } else {
          window.location.href = `/vault?search=${encodeURIComponent(query)}`;
        }
      }
    });
  }
});

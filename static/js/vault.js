/**
 * AbhiApp - Vault File Manager Module
 */

let currentVaultView = 'grid'; // 'grid' | 'table'
let currentCategory = 'all';
let currentTypeFilter = 'all';
let currentFolderId = null;
let currentSearch = '';
let currentSort = 'date_desc';
let selectedFileIds = new Set();
let vaultFilesData = [];

// Initialize Vault
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('vaultFilesContainer')) {
    // Parse URL params for initial filters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('category')) currentCategory = urlParams.get('category');
    if (urlParams.has('type')) currentTypeFilter = urlParams.get('type');
    if (urlParams.has('search')) currentSearch = urlParams.get('search');
    if (urlParams.has('folder_id')) currentFolderId = urlParams.get('folder_id');
    if (urlParams.has('favorite')) currentTypeFilter = 'favorite';

    // Set search input value if present
    const searchInput = document.getElementById('vaultSearchInput');
    if (searchInput && currentSearch) searchInput.value = currentSearch;

    // Highlight active category/filter chip
    updateFilterChipUI();

    loadVaultFiles();
  }
});

function updateFilterChipUI() {
  document.querySelectorAll('.filter-chip').forEach(chip => {
    const chipType = chip.dataset.type || chip.dataset.category;
    if (chipType === currentTypeFilter || chipType === currentCategory) {
      chip.classList.add('active');
    } else {
      chip.classList.remove('active');
    }
  });
}

function setCategoryFilter(category) {
  currentCategory = category;
  currentTypeFilter = 'all';
  loadVaultFiles();
  updateFilterChipUI();
}

function setTypeFilter(type) {
  currentTypeFilter = type;
  loadVaultFiles();
  updateFilterChipUI();
}

function setVaultSort(sortVal) {
  currentSort = sortVal;
  loadVaultFiles();
}

function toggleVaultView(viewType) {
  currentVaultView = viewType;
  const gridBtn = document.getElementById('btnViewGrid');
  const tableBtn = document.getElementById('btnViewTable');

  if (viewType === 'grid') {
    if (gridBtn) gridBtn.classList.add('active');
    if (tableBtn) tableBtn.classList.remove('active');
  } else {
    if (tableBtn) tableBtn.classList.add('active');
    if (gridBtn) gridBtn.classList.remove('active');
  }
  renderVaultFiles();
}

let searchDebounceTimer = null;
function handleVaultSearchInput(input) {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    currentSearch = input.value.trim();
    loadVaultFiles();
  }, 250);
}

// Fetch Files from Backend
async function loadVaultFiles() {
  const container = document.getElementById('vaultFilesContainer');
  if (!container) return;

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem;color:#94a3b8;gap:0.75rem;">
      <div style="font-size:2rem;animation:spin 1s linear infinite;">⏳</div>
      <div>Loading vault documents...</div>
    </div>
  `;

  // Build query URL
  const params = new URLSearchParams();
  if (currentSearch) params.append('search', currentSearch);
  if (currentCategory && currentCategory !== 'all') params.append('category', currentCategory);
  if (currentTypeFilter && currentTypeFilter !== 'all') {
    if (currentTypeFilter === 'favorite') {
      params.append('favorite', 'true');
    } else {
      params.append('type', currentTypeFilter);
    }
  }
  if (currentFolderId) params.append('folder_id', currentFolderId);
  if (currentSort) params.append('sort', currentSort);

  try {
    const res = await fetch(`/api/files?${params.toString()}`);
    const data = await res.json();
    if (data.success) {
      vaultFilesData = data.files;
      selectedFileIds.clear();
      updateBulkActionBar();
      renderVaultFiles();
    } else {
      container.innerHTML = `<div style="text-align:center;color:#f43f5e;padding:2rem;">${data.error || 'Failed to load files.'}</div>`;
    }
  } catch (err) {
    container.innerHTML = `<div style="text-align:center;color:#f43f5e;padding:2rem;">Network error fetching files from vault.</div>`;
  }
}

// Render Files to DOM
function renderVaultFiles() {
  const container = document.getElementById('vaultFilesContainer');
  const countBadge = document.getElementById('vaultFilesCountBadge');
  if (!container) return;

  if (countBadge) countBadge.textContent = `${vaultFilesData.length} file${vaultFilesData.length === 1 ? '' : 's'}`;

  if (vaultFilesData.length === 0) {
    container.innerHTML = `
      <div style="text-align:center;padding:4rem 1.5rem;background:rgba(22,31,51,0.4);border:1px dashed rgba(255,255,255,0.08);border-radius:14px;">
        <div style="font-size:3rem;margin-bottom:0.75rem;">📂</div>
        <div style="font-size:1.15rem;font-weight:600;color:#fff;margin-bottom:0.25rem;">No files found</div>
        <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:1.25rem;">No files match your active filter or search query.</div>
        <button class="btn btn-primary" onclick="openModal('uploadModal')">
          <span>📤</span> Upload Your First Document
        </button>
      </div>
    `;
    return;
  }

  if (currentVaultView === 'grid') {
    renderGridView(container);
  } else {
    renderTableView(container);
  }
}

// Render Grid View
function renderGridView(container) {
  let html = `<div class="files-grid">`;

  vaultFilesData.forEach(f => {
    const isSelected = selectedFileIds.has(f.id);
    const badgeClass = getBadgeClass(f.file_extension);
    const favClass = f.is_favorite ? 'favorited' : '';
    const extDisplay = f.file_extension.replace('.', '').toUpperCase();

    html += `
      <div class="file-card ${isSelected ? 'selected' : ''}" data-file-id="${f.id}">
        <input type="checkbox" class="file-card-select-checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleFileSelection(${f.id}, this.checked)">
        <button class="file-card-favorite-btn ${favClass}" onclick="event.stopPropagation(); toggleFileFavorite(${f.id})">
          ${f.is_favorite ? '★' : '☆'}
        </button>

        <div class="file-icon-preview-box" onclick="handleFileClick(${f.id})">
          <span class="file-ext-badge ${badgeClass}">${extDisplay}</span>
        </div>

        <div class="file-card-info" onclick="handleFileClick(${f.id})">
          <div class="file-card-name" title="${escapeHtml(f.original_name)}">${escapeHtml(f.original_name)}</div>
          <div class="file-card-meta">
            <span>${f.formatted_size}</span>
            <span>${f.relative_date}</span>
          </div>
        </div>

        <div class="file-card-actions">
          <button class="btn btn-secondary btn-sm" onclick="openFilePreview(${f.id})" title="Preview / Inspect">
            👁️ Preview
          </button>
          <div style="display:flex;gap:0.35rem;">
            <a href="/api/files/${f.id}/download" class="btn btn-secondary btn-icon btn-sm" title="Download">
              ⬇️
            </a>
            <button class="btn btn-secondary btn-icon btn-sm" onclick="openFileDetailsModal(${f.id})" title="Details & Actions">
              ⋮
            </button>
          </div>
        </div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}

// Render Table View
function renderTableView(container) {
  let html = `
    <div class="file-table-container">
      <table class="file-table">
        <thead>
          <tr>
            <th style="width:40px;"><input type="checkbox" onchange="toggleSelectAllFiles(this.checked)"></th>
            <th>Name</th>
            <th>Type</th>
            <th>Size</th>
            <th>Folder</th>
            <th>Date</th>
            <th style="text-align:right;">Actions</th>
          </tr>
        </thead>
        <tbody>
  `;

  vaultFilesData.forEach(f => {
    const isSelected = selectedFileIds.has(f.id);
    const badgeClass = getBadgeClass(f.file_extension);
    const extDisplay = f.file_extension.replace('.', '').toUpperCase();

    html += `
      <tr class="${isSelected ? 'selected' : ''}" data-file-id="${f.id}">
        <td>
          <input type="checkbox" ${isSelected ? 'checked' : ''} onchange="toggleFileSelection(${f.id}, this.checked)">
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:0.6rem;cursor:pointer;" onclick="handleFileClick(${f.id})">
            <span class="file-ext-badge ${badgeClass}" style="font-size:0.75rem;padding:2px 6px;">${extDisplay}</span>
            <span style="font-weight:600;color:#fff;" title="${escapeHtml(f.original_name)}">${escapeHtml(f.original_name)}</span>
          </div>
        </td>
        <td><span style="font-size:0.78rem;color:#94a3b8;">${f.category}</span></td>
        <td><span style="font-size:0.8rem;color:#94a3b8;">${f.formatted_size}</span></td>
        <td><span style="font-size:0.8rem;color:#94a3b8;">${escapeHtml(f.folder_path || '/')}</span></td>
        <td><span style="font-size:0.8rem;color:#94a3b8;">${f.relative_date}</span></td>
        <td style="text-align:right;">
          <div style="display:inline-flex;gap:0.35rem;">
            <button class="btn btn-secondary btn-sm" onclick="openFilePreview(${f.id})">Preview</button>
            <a href="/api/files/${f.id}/download" class="btn btn-secondary btn-sm">Download</a>
            <button class="btn btn-secondary btn-sm" onclick="openFileDetailsModal(${f.id})">⋮</button>
          </div>
        </td>
      </tr>
    `;
  });

  html += `</tbody></table></div>`;
  container.innerHTML = html;
}

function handleFileClick(fileId) {
  openFilePreview(fileId);
}

function getBadgeClass(ext) {
  const e = ext.toLowerCase();
  if (e === '.pdf') return 'badge-pdf';
  if (e === '.dwg' || e === '.dxf') return 'badge-dwg';
  if (e === '.sldprt' || e === '.sldasm' || e === '.slddrw') return 'badge-sldprt';
  if (['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg'].includes(e)) return 'badge-img';
  if (['.py', '.js', '.c', '.cpp', '.h', '.html', '.css', '.json', '.sql'].includes(e)) return 'badge-code';
  if (['.xls', '.xlsx', '.csv'].includes(e)) return 'badge-excel';
  return 'badge-other';
}

// File Selection & Bulk Action Bar
function toggleFileSelection(fileId, isChecked) {
  if (isChecked) {
    selectedFileIds.add(fileId);
  } else {
    selectedFileIds.delete(fileId);
  }
  updateBulkActionBar();
  highlightSelectedCards();
}

function toggleSelectAllFiles(isChecked) {
  if (isChecked) {
    vaultFilesData.forEach(f => selectedFileIds.add(f.id));
  } else {
    selectedFileIds.clear();
  }
  updateBulkActionBar();
  renderVaultFiles();
}

function highlightSelectedCards() {
  document.querySelectorAll('.file-card, .file-table tr[data-file-id]').forEach(el => {
    const fId = parseInt(el.dataset.fileId);
    if (selectedFileIds.has(fId)) {
      el.classList.add('selected');
    } else {
      el.classList.remove('selected');
    }
  });
}

function updateBulkActionBar() {
  let bar = document.getElementById('bulkActionBar');
  if (!bar) return;

  const countSpan = document.getElementById('bulkSelectedCount');
  if (selectedFileIds.size > 0) {
    bar.classList.add('visible');
    if (countSpan) countSpan.textContent = `${selectedFileIds.size} file${selectedFileIds.size > 1 ? 's' : ''} selected`;
  } else {
    bar.classList.remove('visible');
  }
}

// Bulk Actions
async function handleBulkDelete() {
  if (selectedFileIds.size === 0) return;
  if (!confirm(`Are you sure you want to permanently delete ${selectedFileIds.size} selected file(s)?`)) return;

  try {
    const res = await fetch('/api/files/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'delete', file_ids: Array.from(selectedFileIds) })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      loadVaultFiles();
    } else {
      showToast(data.error || 'Bulk delete failed.', 'error');
    }
  } catch (e) {
    showToast('Network error during bulk delete.', 'error');
  }
}

async function handleBulkDownload() {
  if (selectedFileIds.size === 0) return;
  const ids = Array.from(selectedFileIds);
  
  // Download ZIP by triggering POST download
  showToast('Preparing ZIP archive for download...', 'info');
  try {
    const res = await fetch('/api/files/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'download', file_ids: ids })
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AbhiApp_Vault_Export_${Date.now()}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('Vault ZIP downloaded successfully!', 'success');
    } else {
      showToast('Bulk download failed.', 'error');
    }
  } catch (e) {
    showToast('Failed to download ZIP archive.', 'error');
  }
}

function openBulkMoveModal() {
  if (selectedFileIds.size === 0) return;
  loadMoveFolderList();
  openModal('bulkMoveModal');
}

async function handleBulkMoveSubmit() {
  const select = document.getElementById('bulkMoveFolderSelect');
  const targetFolderId = select.value;

  try {
    const res = await fetch('/api/files/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'move',
        file_ids: Array.from(selectedFileIds),
        folder_id: targetFolderId
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('bulkMoveModal');
      loadVaultFiles();
    } else {
      showToast(data.error || 'Move failed.', 'error');
    }
  } catch (e) {
    showToast('Network error.', 'error');
  }
}

async function loadMoveFolderList() {
  const select = document.getElementById('bulkMoveFolderSelect');
  if (!select) return;

  try {
    const res = await fetch('/api/folders');
    const data = await res.json();
    if (data.success) {
      select.innerHTML = '<option value="root">📁 Root / No Folder</option>';
      data.folders.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.id;
        opt.textContent = `📁 ${f.full_path}`;
        select.appendChild(opt);
      });
    }
  } catch (e) {}
}

// Single File Favorite Toggle
async function toggleFileFavorite(fileId) {
  try {
    const res = await fetch(`/api/files/${fileId}/favorite`, { method: 'PUT' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'info');
      // Update local array and re-render
      const file = vaultFilesData.find(f => f.id === fileId);
      if (file) file.is_favorite = data.is_favorite;
      renderVaultFiles();
    }
  } catch (e) {
    showToast('Could not update favorite status.', 'error');
  }
}

// File Details Modal
let activeDetailsFileId = null;
async function openFileDetailsModal(fileId) {
  activeDetailsFileId = fileId;
  openModal('fileDetailsModal');

  const content = document.getElementById('fileDetailsModalBody');
  content.innerHTML = '<div style="text-align:center;padding:2rem;color:#94a3b8;">Loading details...</div>';

  try {
    const res = await fetch(`/api/files/${fileId}`);
    const data = await res.json();
    if (data.success) {
      const f = data.file;
      content.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:1.25rem;">
          <div style="display:flex;align-items:center;gap:1rem;">
            <div style="font-size:2rem;">📄</div>
            <div style="flex:1;">
              <input type="text" id="editFileNameInput" value="${escapeHtml(f.original_name)}" class="select-styled" style="width:100%;font-size:1rem;font-weight:600;padding:0.6rem;">
            </div>
            <button class="btn btn-secondary btn-sm" onclick="saveFileRename(${f.id})">Rename</button>
          </div>

          <div class="cad-spec-grid" style="grid-template-columns:1fr 1fr;">
            <div class="cad-spec-item">
              <span class="cad-spec-label">Extension</span>
              <span class="cad-spec-value">${f.file_extension}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">File Size</span>
              <span class="cad-spec-value">${f.formatted_size}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Category</span>
              <span class="cad-spec-value">${f.category}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Folder Location</span>
              <span class="cad-spec-value">${escapeHtml(f.folder_path || 'Root')}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Uploaded At</span>
              <span class="cad-spec-value">${f.uploaded_at || 'N/A'}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Last Opened</span>
              <span class="cad-spec-value">${f.last_opened_at || 'Never'}</span>
            </div>
          </div>

          <div style="display:flex;flex-direction:column;gap:0.35rem;">
            <label style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;font-weight:600;">Tags (comma separated)</label>
            <input type="text" id="editFileTagsInput" value="${escapeHtml(f.tags_raw || '')}" class="select-styled" placeholder="e.g. panel, busbar, 415v">
          </div>

          <div style="display:flex;flex-direction:column;gap:0.35rem;">
            <label style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;font-weight:600;">Description / Engineering Notes</label>
            <textarea id="editFileDescInput" class="select-styled" rows="3" placeholder="Add description...">${escapeHtml(f.description || '')}</textarea>
          </div>

          <div style="display:flex;justify-content:space-between;align-items:center;padding-top:0.75rem;border-top:1px solid rgba(255,255,255,0.08);">
            <button class="btn btn-danger btn-sm" onclick="deleteSingleFile(${f.id})">🗑️ Delete File</button>
            <div style="display:flex;gap:0.5rem;">
              <a href="/api/files/${f.id}/download" class="btn btn-secondary btn-sm">⬇️ Download</a>
              <button class="btn btn-primary btn-sm" onclick="saveFileMetadata(${f.id})">Save Changes</button>
            </div>
          </div>
        </div>
      `;
    }
  } catch (e) {
    content.innerHTML = '<div style="color:#f43f5e;">Failed to load file details.</div>';
  }
}

async function saveFileRename(fileId) {
  const newName = document.getElementById('editFileNameInput').value.trim();
  if (!newName) return;

  try {
    const res = await fetch(`/api/files/${fileId}/rename`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_name: newName })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      loadVaultFiles();
    } else {
      showToast(data.error || 'Rename failed.', 'error');
    }
  } catch (e) {
    showToast('Rename error.', 'error');
  }
}

async function saveFileMetadata(fileId) {
  const desc = document.getElementById('editFileDescInput').value.trim();
  const tags = document.getElementById('editFileTagsInput').value.trim();

  try {
    const res = await fetch(`/api/files/${fileId}/metadata`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description: desc, tags: tags })
    });
    const data = await res.json();
    if (data.success) {
      showToast('File details updated successfully!', 'success');
      closeModal('fileDetailsModal');
      loadVaultFiles();
    }
  } catch (e) {
    showToast('Failed to update details.', 'error');
  }
}

async function deleteSingleFile(fileId) {
  if (!confirm('Are you sure you want to permanently delete this file?')) return;

  try {
    const res = await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('fileDetailsModal');
      loadVaultFiles();
    }
  } catch (e) {
    showToast('Failed to delete file.', 'error');
  }
}

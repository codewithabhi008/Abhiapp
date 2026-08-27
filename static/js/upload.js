/**
 * AbhiApp - File Upload Manager Module
 */

let selectedUploadFiles = [];
let currentUploadXHR = null;

// Initialize Drag and Drop Listeners
function initUploadDropzone(dropzoneId, inputId) {
  const dropzone = document.getElementById(dropzoneId);
  const input = document.getElementById(inputId);

  if (!dropzone || !input) return;

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add('drag-over'), false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove('drag-over'), false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFilesSelected(files);
  });

  input.addEventListener('change', (e) => {
    handleFilesSelected(e.target.files);
  });

  dropzone.addEventListener('click', () => {
    input.click();
  });
}

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function handleFilesSelected(files) {
  if (!files || files.length === 0) return;

  // Add files to selection queue
  for (let i = 0; i < files.length; i++) {
    selectedUploadFiles.push(files[i]);
  }

  // Populate folder list in modal if not already populated
  loadUploadFolderDropdown();

  // Open the Upload Modal
  openModal('uploadModal');
  renderUploadFileList();
}

function renderUploadFileList() {
  const listContainer = document.getElementById('uploadQueueList');
  const countBadge = document.getElementById('uploadFileCountBadge');
  const uploadSubmitBtn = document.getElementById('btnStartUpload');

  if (!listContainer) return;

  listContainer.innerHTML = '';
  if (countBadge) countBadge.textContent = `${selectedUploadFiles.length} file(s) selected`;

  if (selectedUploadFiles.length === 0) {
    listContainer.innerHTML = '<div style="text-align:center;color:#64748b;padding:1.5rem;">No files chosen. Drag & drop or select files above.</div>';
    if (uploadSubmitBtn) uploadSubmitBtn.disabled = true;
    return;
  }

  if (uploadSubmitBtn) uploadSubmitBtn.disabled = false;

  selectedUploadFiles.forEach((file, index) => {
    const item = document.createElement('div');
    item.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:0.6rem 0.85rem;background:rgba(10,13,20,0.5);border:1px solid rgba(255,255,255,0.06);border-radius:8px;margin-bottom:0.5rem;';
    
    const sizeStr = formatBytes(file.size);
    item.innerHTML = `
      <div style="display:flex;align-items:center;gap:0.75rem;overflow:hidden;">
        <span style="font-weight:700;color:#6366f1;font-size:0.85rem;">📄</span>
        <div style="overflow:hidden;">
          <div style="font-size:0.85rem;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:320px;">${escapeHtml(file.name)}</div>
          <div style="font-size:0.72rem;color:#94a3b8;">${sizeStr}</div>
        </div>
      </div>
      <button type="button" onclick="removeFileFromQueue(${index})" style="background:transparent;border:none;color:#f43f5e;cursor:pointer;font-size:1.1rem;padding:0.2rem 0.5rem;">&times;</button>
    `;
    listContainer.appendChild(item);
  });
}

function removeFileFromQueue(index) {
  selectedUploadFiles.splice(index, 1);
  renderUploadFileList();
}

function clearUploadQueue() {
  selectedUploadFiles = [];
  renderUploadFileList();
}

async function loadUploadFolderDropdown() {
  const select = document.getElementById('uploadFolderSelect');
  if (!select || select.dataset.loaded === 'true') return;

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
      select.dataset.loaded = 'true';
    }
  } catch (e) {
    console.error('Failed to load folders for upload selector:', e);
  }
}

// Start Upload Execution
function startFileUpload() {
  if (selectedUploadFiles.length === 0) {
    showToast('Please select at least one file to upload.', 'error');
    return;
  }

  const formData = new FormData();
  selectedUploadFiles.forEach(file => {
    formData.append('files', file);
  });

  const folderId = document.getElementById('uploadFolderSelect').value;
  if (folderId && folderId !== 'root') {
    formData.append('folder_id', folderId);
  }

  const category = document.getElementById('uploadCategorySelect').value;
  if (category && category !== 'auto') {
    formData.append('category', category);
  }

  const description = document.getElementById('uploadDescriptionInput').value;
  if (description) {
    formData.append('description', description);
  }

  const tags = document.getElementById('uploadTagsInput').value;
  if (tags) {
    formData.append('tags', tags);
  }

  // UI state during upload
  const progressBox = document.getElementById('uploadProgressBox');
  const progressBar = document.getElementById('uploadProgressBarFill');
  const progressText = document.getElementById('uploadProgressText');
  const btnStart = document.getElementById('btnStartUpload');
  const btnCancel = document.getElementById('btnCancelUpload');

  progressBox.style.display = 'block';
  btnStart.style.display = 'none';
  btnCancel.style.display = 'inline-flex';
  progressBar.style.width = '0%';
  progressText.textContent = 'Uploading 0%...';

  const xhr = new XMLHttpRequest();
  currentUploadXHR = xhr;

  xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = `${percent}%`;
      progressText.textContent = `Uploading ${percent}% (${formatBytes(e.loaded)} / ${formatBytes(e.total)})`;
    }
  });

  xhr.addEventListener('load', () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      const res = JSON.parse(xhr.responseText);
      showToast(`Successfully uploaded ${res.uploaded_count} file(s) to vault!`, 'success');
      resetUploadModal();
      closeModal('uploadModal');

      // Refresh dashboard stats or vault list if present
      if (window.loadDashboardStats) window.loadDashboardStats();
      if (window.loadVaultFiles) window.loadVaultFiles();
      if (window.loadFolderContents) window.loadFolderContents();
    } else {
      let errMsg = 'Upload failed.';
      try {
        const res = JSON.parse(xhr.responseText);
        errMsg = res.error || errMsg;
      } catch (err) {}
      showToast(errMsg, 'error');
      resetUploadControls();
    }
  });

  xhr.addEventListener('error', () => {
    showToast('Network error during file upload.', 'error');
    resetUploadControls();
  });

  xhr.addEventListener('abort', () => {
    showToast('File upload cancelled.', 'info');
    resetUploadControls();
  });

  xhr.open('POST', '/api/files/upload', true);
  xhr.send(formData);
}

function cancelFileUpload() {
  if (currentUploadXHR) {
    currentUploadXHR.abort();
    currentUploadXHR = null;
  }
}

function resetUploadControls() {
  const progressBox = document.getElementById('uploadProgressBox');
  const btnStart = document.getElementById('btnStartUpload');
  const btnCancel = document.getElementById('btnCancelUpload');
  if (progressBox) progressBox.style.display = 'none';
  if (btnStart) btnStart.style.display = 'inline-flex';
  if (btnCancel) btnCancel.style.display = 'none';
}

function resetUploadModal() {
  selectedUploadFiles = [];
  currentUploadXHR = null;
  resetUploadControls();
  const desc = document.getElementById('uploadDescriptionInput');
  const tags = document.getElementById('uploadTagsInput');
  if (desc) desc.value = '';
  if (tags) tags.value = '';
  renderUploadFileList();
}

function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}

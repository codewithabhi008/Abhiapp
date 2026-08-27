/**
 * AbhiApp - Hierarchical Folder Explorer Module
 */

let currentExplorerFolderId = null;
let allUserFolders = [];

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('folderExplorerContainer')) {
    loadFoldersExplorer();
  }
});

async function loadFoldersExplorer(folderId = null) {
  currentExplorerFolderId = folderId;
  const treeContainer = document.getElementById('folderTreeNav');
  const contentContainer = document.getElementById('folderContentsContainer');
  const breadcrumbsContainer = document.getElementById('folderBreadcrumbs');

  try {
    const res = await fetch('/api/folders');
    const data = await res.json();
    if (data.success) {
      allUserFolders = data.folders;
      if (treeContainer) renderFolderTreeNav(data.tree, treeContainer);
    }
  } catch (e) {
    console.error('Failed to load folder tree:', e);
  }

  // Load content inside current folder
  if (folderId) {
    try {
      const res = await fetch(`/api/folders/${folderId}`);
      const data = await res.json();
      if (data.success) {
        renderBreadcrumbs(data.breadcrumbs, breadcrumbsContainer);
        renderFolderContents(data.folder, data.subfolders, data.files, contentContainer);
      }
    } catch (e) {
      contentContainer.innerHTML = '<div style="color:#f43f5e;padding:2rem;">Failed to load folder contents.</div>';
    }
  } else {
    // Root level view
    renderRootFolderView(contentContainer, breadcrumbsContainer);
  }
}

function renderFolderTreeNav(tree, container) {
  let html = '<div style="display:flex;flex-direction:column;gap:0.3rem;">';
  html += `
    <div class="nav-item ${currentExplorerFolderId === null ? 'active' : ''}" style="cursor:pointer;" onclick="loadFoldersExplorer(null)">
      <span class="nav-icon">📁</span>
      <span>Root Directory</span>
    </div>
  `;

  function renderNodes(nodes, depth = 0) {
    let subHtml = '';
    nodes.forEach(node => {
      const isActive = currentExplorerFolderId === node.id;
      const padLeft = depth * 14 + 10;
      subHtml += `
        <div class="nav-item ${isActive ? 'active' : ''}" style="cursor:pointer;padding-left:${padLeft}px;" onclick="loadFoldersExplorer(${node.id})">
          <span class="nav-icon">📂</span>
          <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">${escapeHtml(node.folder_name)}</span>
          <span class="nav-badge">${node.file_count || 0}</span>
        </div>
      `;
      if (node.children && node.children.length > 0) {
        subHtml += renderNodes(node.children, depth + 1);
      }
    });
    return subHtml;
  }

  html += renderNodes(tree, 0);
  html += '</div>';
  container.innerHTML = html;
}

function renderBreadcrumbs(breadcrumbs, container) {
  if (!container) return;
  let html = `<span style="cursor:pointer;color:#38bdf8;" onclick="loadFoldersExplorer(null)">Root</span>`;
  breadcrumbs.forEach((b, idx) => {
    html += ` <span style="color:#64748b;">/</span> `;
    if (idx === breadcrumbs.length - 1) {
      html += `<span style="font-weight:700;color:#fff;">${escapeHtml(b.name)}</span>`;
    } else {
      html += `<span style="cursor:pointer;color:#38bdf8;" onclick="loadFoldersExplorer(${b.id})">${escapeHtml(b.name)}</span>`;
    }
  });
  container.innerHTML = html;
}

function renderRootFolderView(contentContainer, breadcrumbsContainer) {
  if (breadcrumbsContainer) {
    breadcrumbsContainer.innerHTML = '<span style="font-weight:700;color:#fff;">Root Directory</span>';
  }
  if (!contentContainer) return;

  const rootFolders = allUserFolders.filter(f => f.parent_folder_id === null);

  let html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
      <h2 style="font-size:1.25rem;font-weight:700;color:#fff;">Root Folders</h2>
      <button class="btn btn-primary btn-sm" onclick="openCreateFolderModal(null)">+ New Root Folder</button>
    </div>
  `;

  if (rootFolders.length === 0) {
    html += `
      <div style="text-align:center;padding:3rem;background:rgba(22,31,51,0.4);border:1px dashed rgba(255,255,255,0.08);border-radius:14px;">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">📁</div>
        <div style="font-weight:600;color:#fff;">No folders created yet</div>
        <div style="color:#94a3b8;font-size:0.85rem;margin-bottom:1rem;">Organize your engineering files and documents into custom folders.</div>
        <button class="btn btn-primary btn-sm" onclick="openCreateFolderModal(null)">Create First Folder</button>
      </div>
    `;
  } else {
    html += `<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(220px, 1fr));gap:1rem;">`;
    rootFolders.forEach(f => {
      html += `
        <div class="glass-card glass-card-interactive" style="cursor:pointer;display:flex;flex-direction:column;gap:0.75rem;" onclick="loadFoldersExplorer(${f.id})">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:2rem;color:#6366f1;">📁</span>
            <span class="nav-badge">${f.file_count || 0} files</span>
          </div>
          <div>
            <div style="font-weight:600;color:#fff;font-size:0.95rem;">${escapeHtml(f.folder_name)}</div>
            <div style="font-size:0.75rem;color:#94a3b8;">${f.subfolder_count || 0} subfolders</div>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  contentContainer.innerHTML = html;
}

function renderFolderContents(folder, subfolders, files, container) {
  if (!container) return;

  let html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;gap:0.75rem;">
      <div>
        <h2 style="font-size:1.35rem;font-weight:700;color:#fff;display:flex;align-items:center;gap:0.5rem;">
          <span>📂</span> ${escapeHtml(folder.folder_name)}
        </h2>
        <span style="font-size:0.78rem;color:#94a3b8;">Location: ${escapeHtml(folder.full_path)}</span>
      </div>
      <div style="display:flex;gap:0.5rem;">
        <button class="btn btn-secondary btn-sm" onclick="openCreateFolderModal(${folder.id})">+ New Subfolder</button>
        <button class="btn btn-secondary btn-sm" onclick="openRenameFolderModal(${folder.id}, '${escapeHtml(folder.folder_name)}')">Rename</button>
        <button class="btn btn-danger btn-sm" onclick="deleteFolderAction(${folder.id})">Delete Folder</button>
      </div>
    </div>
  `;

  // Subfolders Section
  if (subfolders && subfolders.length > 0) {
    html += `
      <div style="margin-bottom:1.75rem;">
        <h3 style="font-size:0.9rem;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:0.75rem;letter-spacing:0.05em;">Subfolders</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(200px, 1fr));gap:0.85rem;">
    `;
    subfolders.forEach(sf => {
      html += `
        <div class="glass-card glass-card-interactive" style="cursor:pointer;display:flex;align-items:center;gap:0.75rem;padding:0.85rem;" onclick="loadFoldersExplorer(${sf.id})">
          <span style="font-size:1.5rem;color:#38bdf8;">📁</span>
          <div style="overflow:hidden;flex:1;">
            <div style="font-weight:600;color:#fff;font-size:0.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(sf.folder_name)}</div>
            <div style="font-size:0.72rem;color:#94a3b8;">${sf.file_count || 0} files</div>
          </div>
        </div>
      `;
    });
    html += `</div></div>`;
  }

  // Files in this folder Section
  html += `
    <div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
        <h3 style="font-size:0.9rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Contained Documents</h3>
        <button class="btn btn-primary btn-sm" onclick="openModal('uploadModal'); document.getElementById('uploadFolderSelect').value = '${folder.id}';">
          📤 Upload Here
        </button>
      </div>
  `;

  if (!files || files.length === 0) {
    html += `
      <div style="text-align:center;padding:2.5rem;background:rgba(10,13,20,0.4);border:1px dashed rgba(255,255,255,0.06);border-radius:10px;color:#94a3b8;">
        This folder is currently empty.
      </div>
    `;
  } else {
    html += `
      <div class="file-table-container">
        <table class="file-table">
          <thead>
            <tr>
              <th>File Name</th>
              <th>Category</th>
              <th>Size</th>
              <th>Uploaded</th>
              <th style="text-align:right;">Action</th>
            </tr>
          </thead>
          <tbody>
    `;
    files.forEach(f => {
      html += `
        <tr>
          <td>
            <div style="font-weight:600;color:#fff;cursor:pointer;" onclick="openFilePreview(${f.id})">
              📄 ${escapeHtml(f.original_name)}
            </div>
          </td>
          <td><span style="font-size:0.78rem;color:#94a3b8;">${f.category}</span></td>
          <td><span style="font-size:0.8rem;color:#94a3b8;">${f.formatted_size}</span></td>
          <td><span style="font-size:0.8rem;color:#94a3b8;">${f.relative_date}</span></td>
          <td style="text-align:right;">
            <div style="display:inline-flex;gap:0.35rem;">
              <button class="btn btn-secondary btn-sm" onclick="openFilePreview(${f.id})">Preview</button>
              <a href="/api/files/${f.id}/download" class="btn btn-secondary btn-sm">Download</a>
            </div>
          </td>
        </tr>
      `;
    });
    html += `</tbody></table></div>`;
  }

  html += `</div>`;
  container.innerHTML = html;
}

// Modal Triggers
function openCreateFolderModal(parentId = null) {
  const modal = document.getElementById('createFolderModal');
  const parentInput = document.getElementById('createFolderParentId');
  const nameInput = document.getElementById('createFolderNameInput');
  if (parentInput) parentInput.value = parentId || '';
  if (nameInput) nameInput.value = '';
  openModal('createFolderModal');
}

async function handleCreateFolderSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('createFolderNameInput').value.trim();
  const parentId = document.getElementById('createFolderParentId').value || null;

  if (!name) return;

  try {
    const res = await fetch('/api/folders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_name: name, parent_folder_id: parentId })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('createFolderModal');
      loadFoldersExplorer(currentExplorerFolderId);
    } else {
      showToast(data.error || 'Failed to create folder.', 'error');
    }
  } catch (e) {
    showToast('Network error creating folder.', 'error');
  }
}

function openRenameFolderModal(folderId, currentName) {
  const modal = document.getElementById('renameFolderModal');
  const idInput = document.getElementById('renameFolderId');
  const nameInput = document.getElementById('renameFolderNameInput');
  if (idInput) idInput.value = folderId;
  if (nameInput) nameInput.value = currentName;
  openModal('renameFolderModal');
}

async function handleRenameFolderSubmit(e) {
  e.preventDefault();
  const folderId = document.getElementById('renameFolderId').value;
  const name = document.getElementById('renameFolderNameInput').value.trim();
  if (!name) return;

  try {
    const res = await fetch(`/api/folders/${folderId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_name: name })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeModal('renameFolderModal');
      loadFoldersExplorer(currentExplorerFolderId);
    } else {
      showToast(data.error || 'Rename failed.', 'error');
    }
  } catch (e) {
    showToast('Network error.', 'error');
  }
}

async function deleteFolderAction(folderId) {
  if (!confirm('Are you sure you want to delete this folder? Any files inside will safely be moved to Root.')) return;

  try {
    const res = await fetch(`/api/folders/${folderId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      loadFoldersExplorer(null);
    } else {
      showToast(data.error || 'Failed to delete folder.', 'error');
    }
  } catch (e) {
    showToast('Delete error.', 'error');
  }
}

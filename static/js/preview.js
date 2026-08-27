/**
 * AbhiApp - Universal File Preview Module
 */

async function openFilePreview(fileId) {
  const modal = document.getElementById('previewModal');
  const container = document.getElementById('previewModalBody');
  const title = document.getElementById('previewModalTitle');
  const downloadLink = document.getElementById('previewModalDownloadBtn');

  if (!modal || !container) return;

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#94a3b8;gap:0.75rem;">
      <div style="font-size:2.5rem;animation:spin 1s linear infinite;">⏳</div>
      <div>Loading preview...</div>
    </div>
  `;

  if (title) title.textContent = 'Loading Document...';
  if (downloadLink) downloadLink.href = `/api/files/${fileId}/download`;

  openModal('previewModal');

  try {
    const res = await fetch(`/api/files/${fileId}`);
    const data = await res.json();
    if (!data.success) {
      container.innerHTML = `<div style="color:#f43f5e;padding:2rem;">${data.error || 'Cannot preview file.'}</div>`;
      return;
    }

    const file = data.file;
    if (title) title.textContent = file.original_name;

    // 1. PDF Preview
    if (file.is_pdf) {
      container.innerHTML = `
        <iframe src="/api/files/${file.id}/preview#toolbar=1" class="pdf-preview-iframe"></iframe>
      `;
    }
    // 2. Image Lightbox
    else if (file.is_image) {
      container.innerHTML = `
        <div class="image-lightbox-wrapper">
          <img src="/api/files/${file.id}/preview" class="image-lightbox-img" alt="${escapeHtml(file.original_name)}">
        </div>
      `;
    }
    // 3. Text & Code Syntax Viewer
    else if (file.is_text) {
      const textRes = await fetch(`/api/files/${file.id}/preview`);
      const textData = await textRes.json();
      
      if (textData.success) {
        container.innerHTML = `
          <div class="code-viewer-container">
            <div class="code-viewer-toolbar">
              <span class="code-language-tag">${file.file_extension.replace('.', '')} Source</span>
              <button class="btn btn-secondary btn-sm" onclick="copyCodeContent()">📋 Copy Content</button>
            </div>
            <pre class="code-pre-block" id="codeViewerTextContent">${escapeHtml(textData.content)}</pre>
          </div>
        `;
      } else {
        container.innerHTML = `<div style="color:#f43f5e;padding:2rem;">Could not read text content.</div>`;
      }
    }
    // 4. Engineering CAD Inspector Card (AutoCAD & SolidWorks)
    else if (file.is_cad) {
      const cad = file.cad_details || { type: 'Engineering CAD File', software: 'CAD Suite', nature: 'Engineering Model' };
      const extUpper = file.file_extension.replace('.', '').toUpperCase();

      container.innerHTML = `
        <div class="cad-inspector-card">
          <div class="cad-header-section">
            <div class="cad-big-badge">${extUpper}</div>
            <div class="cad-title-group">
              <div class="cad-file-title">${escapeHtml(file.original_name)}</div>
              <div class="cad-tech-type">${cad.type}</div>
            </div>
          </div>

          <div class="cad-spec-grid">
            <div class="cad-spec-item">
              <span class="cad-spec-label">Native Software</span>
              <span class="cad-spec-value">${cad.software}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Data Format</span>
              <span class="cad-spec-value">${cad.nature}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">File Size</span>
              <span class="cad-spec-value">${file.formatted_size}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Folder Location</span>
              <span class="cad-spec-value">${escapeHtml(file.folder_path || '/')}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Upload Timestamp</span>
              <span class="cad-spec-value">${file.uploaded_at || 'N/A'}</span>
            </div>
            <div class="cad-spec-item">
              <span class="cad-spec-label">Vault Status</span>
              <span class="cad-spec-value" style="color:#10b981;">● Stored & Verified</span>
            </div>
          </div>

          ${file.description ? `
            <div style="background:rgba(10,13,20,0.4);padding:0.85rem;border-radius:8px;border:1px solid rgba(255,255,255,0.06);">
              <span class="cad-spec-label">Description / Engineering Specs</span>
              <div style="color:#cbd5e1;font-size:0.85rem;margin-top:0.25rem;">${escapeHtml(file.description)}</div>
            </div>
          ` : ''}

          <div class="cad-notice-box">
            <span style="font-size:1.2rem;">📐</span>
            <div>
              <strong>Engineering CAD File Specification:</strong> This is a high-precision binary CAD file. To maintain 100% geometric integrity without loss of parametric layers or tolerance data, download the file directly to your local CAD workstation.
            </div>
          </div>

          <div class="cad-actions-row">
            <a href="/api/files/${file.id}/download" class="btn btn-primary" style="flex:1;">
              <span>⬇️</span> Download ${extUpper} File (${file.formatted_size})
            </a>
          </div>
        </div>
      `;
    }
    // 5. Generic Document Info
    else {
      container.innerHTML = `
        <div style="text-align:center;padding:3rem 1.5rem;max-width:500px;">
          <div style="font-size:3.5rem;margin-bottom:1rem;">📁</div>
          <div style="font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:0.35rem;">${escapeHtml(file.original_name)}</div>
          <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:1.5rem;">${file.category} &bull; ${file.formatted_size}</div>
          <a href="/api/files/${file.id}/download" class="btn btn-primary" style="width:100%;">
            ⬇️ Download Original File
          </a>
        </div>
      `;
    }

  } catch (e) {
    container.innerHTML = `<div style="color:#f43f5e;padding:2rem;">Error loading file preview.</div>`;
  }
}

function copyCodeContent() {
  const el = document.getElementById('codeViewerTextContent');
  if (el) {
    navigator.clipboard.writeText(el.innerText).then(() => {
      showToast('Code copied to clipboard!', 'success');
    }).catch(() => {
      showToast('Failed to copy code.', 'error');
    });
  }
}

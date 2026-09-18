import { parseWorkspace, filterDocuments, buildDemoWorkspace, formatBytes } from './library.js';

let currentWorkspace = null;
let activeTheme = 'all';
let searchQuery = '';
let statusFilter = 'all';

// DOM elements
const fileInput = document.getElementById('file-input');
const importBtn = document.getElementById('import-btn');
const demoBtn = document.getElementById('demo-btn');
const dropzone = document.getElementById('dropzone');
const themeList = document.getElementById('theme-list');
const docList = document.getElementById('doc-list');
const searchInput = document.getElementById('search-input');
const statusSelect = document.getElementById('status-select');
const statThemes = document.getElementById('stat-themes');
const statDocs = document.getElementById('stat-docs');
const statRead = document.getElementById('stat-read');
const statForms = document.getElementById('stat-forms');
const formsSection = document.getElementById('forms-section');
const formsBadges = document.getElementById('forms-badges');

function updateStats() {
  if (!currentWorkspace) return;
  const totals = currentWorkspace.totals || {};
  statThemes.textContent = totals.theme_count ?? currentWorkspace.themes.length;
  statDocs.textContent = totals.document_count ?? currentWorkspace.documents.length;
  statRead.textContent = totals.read_document_count ?? currentWorkspace.documents.filter(d => d.isRead).length;
  statForms.textContent = totals.form_count ?? currentWorkspace.forms.length;

  if (currentWorkspace.forms.length > 0) {
    formsSection.hidden = false;
    formsBadges.innerHTML = currentWorkspace.forms.map(f => `
      <span class="tag-badge" style="background: var(--badge-bg); color: var(--badge-text);">
        📄 ${escapeHtml(f.title || f.name)} (${f.fieldCount} Felder)
      </span>
    `).join('');
  } else {
    formsSection.hidden = true;
  }
}

function renderThemes() {
  if (!currentWorkspace) return;
  const totalCount = currentWorkspace.documents.length;
  let html = `
    <li class="theme-item ${activeTheme === 'all' ? 'active' : ''}" data-theme="all">
      <span>Alle Dokumente</span>
      <span class="count-pill">${totalCount}</span>
    </li>
  `;

  for (const t of currentWorkspace.themes) {
    const isActive = activeTheme === t.name;
    html += `
      <li class="theme-item ${isActive ? 'active' : ''}" data-theme="${escapeHtml(t.name)}">
        <span>${escapeHtml(t.name)}</span>
        <span class="count-pill">${t.documentCount}</span>
      </li>
    `;
  }
  themeList.innerHTML = html;

  themeList.querySelectorAll('.theme-item').forEach(item => {
    item.addEventListener('click', () => {
      activeTheme = item.getAttribute('data-theme');
      renderThemes();
      renderDocuments();
    });
  });
}

function renderDocuments() {
  if (!currentWorkspace) {
    docList.innerHTML = '<div class="empty-state">Noch kein Arbeitsbereich geladen. Importiere eine JSON-Datei oder lade die Demo.</div>';
    return;
  }

  const docs = filterDocuments(currentWorkspace, {
    theme: activeTheme,
    query: searchQuery,
    status: statusFilter
  });

  if (docs.length === 0) {
    docList.innerHTML = '<div class="empty-state">Keine Dokumente gefunden, die den Filtern entsprechen.</div>';
    return;
  }

  docList.innerHTML = docs.map(doc => {
    const ext = doc.extension.replace('.', '') || 'DOC';
    const readHtml = doc.isRead 
      ? '<span class="read-indicator read">✓ Gelesen</span>' 
      : '<span class="read-indicator unread">○ Ungelesen</span>';
    
    const tagsHtml = doc.tags.map(t => `<span class="tag-badge">#${escapeHtml(t)}</span>`).join('');
    const notesHtml = doc.notes ? `<div class="doc-notes">${escapeHtml(doc.notes)}</div>` : '';
    const dateAdded = doc.added ? new Date(doc.added).toLocaleDateString() : '';

    return `
      <article class="doc-card">
        <div class="doc-header">
          <div class="doc-title">
            <span class="ext-badge">${escapeHtml(ext)}</span>
            <span>${escapeHtml(doc.filename)}</span>
          </div>
          ${readHtml}
        </div>
        ${notesHtml}
        <div class="doc-footer">
          <div class="tags-row">${tagsHtml}</div>
          <div>
            <span>${escapeHtml(doc.theme)}</span> • 
            <span>${formatBytes(doc.sizeBytes)}</span>
            ${dateAdded ? ` • <span>${dateAdded}</span>` : ''}
          </div>
        </div>
      </article>
    `;
  }).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function loadSnapshot(data) {
  try {
    currentWorkspace = parseWorkspace(data);
    activeTheme = 'all';
    dropzone.hidden = true;
    updateStats();
    renderThemes();
    renderDocuments();
    // Cache snapshot locally in browser session
    try {
      localStorage.setItem('dokuzen_last_snapshot', JSON.stringify(data));
    } catch (e) {
      console.warn("Could not cache to localStorage", e);
    }
  } catch (err) {
    alert("Fehler beim Laden des Arbeitsbereichs: " + err.message);
  }
}

// Event listeners
importBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', event => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = JSON.parse(e.target.result);
      loadSnapshot(data);
    } catch (err) {
      alert("Ungültige JSON-Datei: " + err.message);
    }
  };
  reader.readAsText(file, "utf-8");
});

demoBtn.addEventListener('click', () => {
  const demo = buildDemoWorkspace();
  loadSnapshot(demo);
});

dropzone.addEventListener('dragover', e => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    try {
      const data = JSON.parse(ev.target.result);
      loadSnapshot(data);
    } catch (err) {
      alert("Ungültige JSON-Datei: " + err.message);
    }
  };
  reader.readAsText(file, "utf-8");
});

dropzone.addEventListener('click', () => fileInput.click());

searchInput.addEventListener('input', e => {
  searchQuery = e.target.value;
  renderDocuments();
});

statusSelect.addEventListener('change', e => {
  statusFilter = e.target.value;
  renderDocuments();
});

// Auto-restore cached snapshot or demo on launch
const cached = localStorage.getItem('dokuzen_last_snapshot');
if (cached) {
  try {
    loadSnapshot(JSON.parse(cached));
  } catch (e) {
    loadSnapshot(buildDemoWorkspace());
  }
} else {
  loadSnapshot(buildDemoWorkspace());
}

// Service worker registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(err => {
      console.log('SW Registration ignored in non-https/local dev:', err);
    });
  });
}

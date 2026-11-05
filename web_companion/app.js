import { parseWorkspace, filterDocuments, buildDemoWorkspace, formatBytes } from './library.js';

export const SUPPORTED_LANGUAGES = ['de', 'en', 'es', 'zh', 'ja', 'ru'];
export const DEFAULT_LANGUAGE = 'de';

export const TRANSLATIONS = {
  de: {
    app_title: 'DokuZen Companion',
    import_btn: 'JSON importieren',
    import_btn_title: 'JSON Arbeitsbereich importieren',
    demo_btn: 'Demo laden',
    demo_btn_title: 'Demo-Arbeitsbereich laden',
    dropzone_text: 'dokuzen-workspace-v1.json hierher ziehen oder klicken zum Auswählen',
    dropzone_aria: 'JSON-Datei hierher ziehen',
    stat_themes: 'Themen:',
    stat_docs: 'Dokumente:',
    stat_read: 'Gelesen:',
    stat_forms: 'Formulare:',
    themes_heading: 'Themen',
    all_documents: 'Alle Dokumente',
    search_placeholder: 'Dokument, Notiz oder #Tag suchen…',
    status_select_aria: 'Status-Filter',
    status_all: 'Alle Status',
    status_unread: 'Ungelesen',
    status_read: 'Gelesen',
    forms_heading: 'Formular-Vorlagen',
    fields_count: 'Felder',
    read_badge: '✓ Gelesen',
    unread_badge: '○ Ungelesen',
    empty_no_workspace: 'Noch kein Arbeitsbereich geladen. Importiere eine JSON-Datei oder lade die Demo.',
    empty_no_match: 'Keine Dokumente gefunden, die den Filtern entsprechen.',
    error_load: 'Fehler beim Laden des Arbeitsbereichs: ',
    error_invalid_json: 'Ungültige JSON-Datei: '
  },
  en: {
    app_title: 'DokuZen Companion',
    import_btn: 'Import JSON',
    import_btn_title: 'Import JSON workspace',
    demo_btn: 'Load Demo',
    demo_btn_title: 'Load demo workspace',
    dropzone_text: 'Drop dokuzen-workspace-v1.json here or click to select',
    dropzone_aria: 'Drop JSON file here',
    stat_themes: 'Themes:',
    stat_docs: 'Documents:',
    stat_read: 'Read:',
    stat_forms: 'Forms:',
    themes_heading: 'Themes',
    all_documents: 'All Documents',
    search_placeholder: 'Search document, note, or #tag…',
    status_select_aria: 'Status Filter',
    status_all: 'All Statuses',
    status_unread: 'Unread',
    status_read: 'Read',
    forms_heading: 'Form Templates',
    fields_count: 'fields',
    read_badge: '✓ Read',
    unread_badge: '○ Unread',
    empty_no_workspace: 'No workspace loaded yet. Import a JSON file or load the demo.',
    empty_no_match: 'No documents found matching the filters.',
    error_load: 'Error loading workspace: ',
    error_invalid_json: 'Invalid JSON file: '
  },
  es: {
    app_title: 'DokuZen Companion',
    import_btn: 'Importar JSON',
    import_btn_title: 'Importar espacio de trabajo JSON',
    demo_btn: 'Cargar Demo',
    demo_btn_title: 'Cargar espacio de trabajo de demostración',
    dropzone_text: 'Arrastre dokuzen-workspace-v1.json aquí o haga clic para seleccionar',
    dropzone_aria: 'Arrastre el archivo JSON aquí',
    stat_themes: 'Temas:',
    stat_docs: 'Documentos:',
    stat_read: 'Leídos:',
    stat_forms: 'Formularios:',
    themes_heading: 'Temas',
    all_documents: 'Todos los documentos',
    search_placeholder: 'Buscar documento, nota o #etiqueta…',
    status_select_aria: 'Filtro de estado',
    status_all: 'Todos los estados',
    status_unread: 'No leídos',
    status_read: 'Leídos',
    forms_heading: 'Plantillas de formulario',
    fields_count: 'campos',
    read_badge: '✓ Leído',
    unread_badge: '○ No leído',
    empty_no_workspace: 'Aún no se ha cargado ningún espacio de trabajo. Importe un archivo JSON o cargue la demo.',
    empty_no_match: 'No se encontraron documentos que coincidan con los filtros.',
    error_load: 'Error al cargar el espacio de trabajo: ',
    error_invalid_json: 'Archivo JSON no válido: '
  },
  zh: {
    app_title: 'DokuZen Companion',
    import_btn: '导入JSON',
    import_btn_title: '导入JSON工作区',
    demo_btn: '加载演示',
    demo_btn_title: '加载演示工作区',
    dropzone_text: '将 dokuzen-workspace-v1.json 拖至此处或点击选择',
    dropzone_aria: '拖入JSON文件',
    stat_themes: '主题：',
    stat_docs: '文档：',
    stat_read: '已读：',
    stat_forms: '表单：',
    themes_heading: '主题',
    all_documents: '全部文档',
    search_placeholder: '搜索文档、笔记或 #标签…',
    status_select_aria: '状态筛选',
    status_all: '所有状态',
    status_unread: '未读',
    status_read: '已读',
    forms_heading: '表单模板',
    fields_count: '个字段',
    read_badge: '✓ 已读',
    unread_badge: '○ 未读',
    empty_no_workspace: '尚未加载工作区。请导入 JSON 文件或加载演示。',
    empty_no_match: '未找到匹配筛选条件的文档。',
    error_load: '加载工作区时出错：',
    error_invalid_json: '无效的 JSON 文件：'
  },
  ja: {
    app_title: 'DokuZen Companion',
    import_btn: 'JSONをインポート',
    import_btn_title: 'JSONワークスペースをインポート',
    demo_btn: 'デモを読み込む',
    demo_btn_title: 'デモワークスペースを読み込む',
    dropzone_text: 'dokuzen-workspace-v1.json をここにドロップまたはクリックして選択',
    dropzone_aria: 'JSONファイルをドロップ',
    stat_themes: 'テーマ：',
    stat_docs: 'ドキュメント：',
    stat_read: '既読：',
    stat_forms: 'フォーム：',
    themes_heading: 'テーマ',
    all_documents: 'すべての文書',
    search_placeholder: '文書、メモ、#タグを検索…',
    status_select_aria: 'ステータスフィルター',
    status_all: 'すべてのステータス',
    status_unread: '未読',
    status_read: '既読',
    forms_heading: 'フォームテンプレート',
    fields_count: 'フィールド',
    read_badge: '✓ 既読',
    unread_badge: '○ 未読',
    empty_no_workspace: 'ワークスペースが読み込まれていません。JSONファイルをインポートするかデモを読み込んでください。',
    empty_no_match: 'フィルターに一致する文書が見つかりませんでした。',
    error_load: 'ワークスペースの読み込みエラー：',
    error_invalid_json: '無効なJSONファイル：'
  },
  ru: {
    app_title: 'DokuZen Companion',
    import_btn: 'Импорт JSON',
    import_btn_title: 'Импортировать рабочую область JSON',
    demo_btn: 'Загрузить демо',
    demo_btn_title: 'Загрузить демонстрационную область',
    dropzone_text: 'Перетащите dokuzen-workspace-v1.json сюда или нажмите для выбора',
    dropzone_aria: 'Перетащите JSON-файл сюда',
    stat_themes: 'Темы:',
    stat_docs: 'Документы:',
    stat_read: 'Прочитано:',
    stat_forms: 'Формы:',
    themes_heading: 'Темы',
    all_documents: 'Все документы',
    search_placeholder: 'Поиск документа, заметки или #тега…',
    status_select_aria: 'Фильтр статуса',
    status_all: 'Все статусы',
    status_unread: 'Непрочитанные',
    status_read: 'Прочитанные',
    forms_heading: 'Шаблоны форм',
    fields_count: 'полей',
    read_badge: '✓ Прочитано',
    unread_badge: '○ Не прочитано',
    empty_no_workspace: 'Рабочая область еще не загружена. Импортируйте JSON-файл или загрузите демо.',
    empty_no_match: 'Документы, соответствующие фильтрам, не найдены.',
    error_load: 'Ошибка загрузки рабочей области: ',
    error_invalid_json: 'Недопустимый JSON-файл: '
  }
};

let currentLanguage = DEFAULT_LANGUAGE;
let currentWorkspace = null;
let activeTheme = 'all';
let searchQuery = '';
let statusFilter = 'all';

// DOM elements
const getEl = id => typeof document !== 'undefined' ? document.getElementById(id) : null;
const fileInput = getEl('file-input');
const importBtn = getEl('import-btn');
const demoBtn = getEl('demo-btn');
const dropzone = getEl('dropzone');
const themeList = getEl('theme-list');
const docList = getEl('doc-list');
const searchInput = getEl('search-input');
const statusSelect = getEl('status-select');
const langSelect = getEl('lang-select');
const statThemes = getEl('stat-themes');
const statDocs = getEl('stat-docs');
const statRead = getEl('stat-read');
const statForms = getEl('stat-forms');
const formsSection = getEl('forms-section');
const formsBadges = getEl('forms-badges');

export function getTranslation(key, lang = currentLanguage) {
  const dict = TRANSLATIONS[lang] || TRANSLATIONS[DEFAULT_LANGUAGE];
  if (dict && key in dict) {
    return dict[key];
  }
  const fallback = TRANSLATIONS[DEFAULT_LANGUAGE];
  return (fallback && key in fallback) ? fallback[key] : key;
}

export function setLanguage(lang) {
  if (SUPPORTED_LANGUAGES.includes(lang)) {
    currentLanguage = lang;
    try {
      localStorage.setItem('dokuzen_companion_lang', lang);
    } catch (e) {
      console.warn("Could not save language to localStorage", e);
    }
    applyTranslations();
  }
}

export function getLanguage() {
  return currentLanguage;
}

export function applyTranslations() {
  document.documentElement.lang = currentLanguage;

  if (langSelect && langSelect.value !== currentLanguage) {
    langSelect.value = currentLanguage;
  }

  // Update elements with data-i18n
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = getTranslation(key);
  });

  // Update elements with data-i18n-title
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    el.title = getTranslation(key);
  });

  // Update elements with data-i18n-placeholder
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = getTranslation(key);
  });

  // Update elements with data-i18n-aria
  document.querySelectorAll('[data-i18n-aria]').forEach(el => {
    const key = el.getAttribute('data-i18n-aria');
    el.setAttribute('aria-label', getTranslation(key));
  });

  updateStats();
  renderThemes();
  renderDocuments();
}

function updateStats() {
  if (!currentWorkspace) return;
  const totals = currentWorkspace.totals || {};
  if (statThemes) statThemes.textContent = totals.theme_count ?? currentWorkspace.themes.length;
  if (statDocs) statDocs.textContent = totals.document_count ?? currentWorkspace.documents.length;
  if (statRead) statRead.textContent = totals.read_document_count ?? currentWorkspace.documents.filter(d => d.isRead).length;
  if (statForms) statForms.textContent = totals.form_count ?? currentWorkspace.forms.length;

  if (formsSection && formsBadges) {
    if (currentWorkspace.forms.length > 0) {
      formsSection.hidden = false;
      const fieldsWord = getTranslation('fields_count');
      formsBadges.innerHTML = currentWorkspace.forms.map(f => `
        <span class="tag-badge" style="background: var(--badge-bg); color: var(--badge-text);">
          📄 ${escapeHtml(f.title || f.name)} (${f.fieldCount} ${fieldsWord})
        </span>
      `).join('');
    } else {
      formsSection.hidden = true;
    }
  }
}

function renderThemes() {
  if (!currentWorkspace || !themeList) return;
  const totalCount = currentWorkspace.documents.length;
  const allDocsLabel = getTranslation('all_documents');
  let html = `
    <li class="theme-item ${activeTheme === 'all' ? 'active' : ''}" data-theme="all">
      <span>${allDocsLabel}</span>
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
  if (!docList) return;
  if (!currentWorkspace) {
    docList.innerHTML = `<div class="empty-state">${getTranslation('empty_no_workspace')}</div>`;
    return;
  }

  const docs = filterDocuments(currentWorkspace, {
    theme: activeTheme,
    query: searchQuery,
    status: statusFilter
  });

  if (docs.length === 0) {
    docList.innerHTML = `<div class="empty-state">${getTranslation('empty_no_match')}</div>`;
    return;
  }

  const readText = getTranslation('read_badge');
  const unreadText = getTranslation('unread_badge');

  docList.innerHTML = docs.map(doc => {
    const ext = doc.extension.replace('.', '') || 'DOC';
    const readHtml = doc.isRead
      ? `<span class="read-indicator read">${readText}</span>`
      : `<span class="read-indicator unread">${unreadText}</span>`;

    const tagsHtml = doc.tags.map(t => `<span class="tag-badge">#${escapeHtml(t)}</span>`).join('');
    const notesHtml = doc.notes ? `<div class="doc-notes">${escapeHtml(doc.notes)}</div>` : '';
    const dateAdded = doc.added ? new Date(doc.added).toLocaleDateString(currentLanguage) : '';

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
    if (dropzone) dropzone.hidden = true;
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
    alert(getTranslation('error_load') + err.message);
  }
}

// Event listeners
if (importBtn && fileInput) {
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
        alert(getTranslation('error_invalid_json') + err.message);
      }
    };
    reader.readAsText(file, "utf-8");
  });
}

if (demoBtn) {
  demoBtn.addEventListener('click', () => {
    const demo = buildDemoWorkspace();
    loadSnapshot(demo);
  });
}

if (dropzone && fileInput) {
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
        alert(getTranslation('error_invalid_json') + err.message);
      }
    };
    reader.readAsText(file, "utf-8");
  });

  dropzone.addEventListener('click', () => fileInput.click());
}

if (searchInput) {
  searchInput.addEventListener('input', e => {
    searchQuery = e.target.value;
    renderDocuments();
  });
}

if (statusSelect) {
  statusSelect.addEventListener('change', e => {
    statusFilter = e.target.value;
    renderDocuments();
  });
}

if (langSelect) {
  langSelect.addEventListener('change', e => {
    setLanguage(e.target.value);
  });
}

// Initialise language from localStorage or browser preferences
try {
  const savedLang = localStorage.getItem('dokuzen_companion_lang');
  if (savedLang && SUPPORTED_LANGUAGES.includes(savedLang)) {
    currentLanguage = savedLang;
  } else if (navigator && navigator.language) {
    const navCode = navigator.language.slice(0, 2).toLowerCase();
    if (SUPPORTED_LANGUAGES.includes(navCode)) {
      currentLanguage = navCode;
    }
  }
} catch (e) {
  // Ignore in sandboxed environment
}

// Initial render
if (typeof document !== 'undefined') {
  applyTranslations();
}

// Auto-restore cached snapshot or demo on launch
try {
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
} catch (e) {
  // Fallback for non-browser runner
}

// Service worker registration
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(err => {
      console.log('SW Registration ignored in non-https/local dev:', err);
    });
  });
}

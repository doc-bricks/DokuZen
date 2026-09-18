/**
 * library.js — DokuZen Web Companion core logic
 * Parses and queries dokuzen-workspace-v1.json snapshots.
 */

export const SCHEMA = "dokuzen-workspace-v1";
export const COMPAT_SCHEMA = "textbrain-workspace-v1";

export function parseWorkspace(json) {
  if (!json || (json.schema !== SCHEMA && json.schema !== COMPAT_SCHEMA)) {
    throw new Error(`Ungültiges Schema: ${json?.schema || "unbekannt"}. Erwartet: ${SCHEMA}`);
  }

  const themes = (json.themes || []).map(t => ({
    name: t.name || "Allgemein",
    documentCount: t.document_count ?? 0,
    readCount: t.read_count ?? 0,
    unreadCount: (t.document_count ?? 0) - (t.read_count ?? 0)
  }));

  const documents = (json.documents || []).map(d => ({
    filename: d.filename || "unnamed",
    extension: d.extension || "",
    theme: d.theme || "Allgemein",
    isRead: Boolean(d.is_read),
    readDate: d.read_date || null,
    tags: Array.isArray(d.tags) ? d.tags : [],
    notes: d.notes || "",
    sizeBytes: d.size_bytes ?? 0,
    added: d.added || null
  }));

  const forms = (json.forms || []).map(f => ({
    name: f.name || "Formular",
    fieldCount: f.field_count ?? 0,
    title: f.title || f.name || "Formular",
    pageSize: f.page_size || [210, 297]
  }));

  return {
    schema: json.schema,
    schemaVersion: json.schema_version,
    exportApp: json.export_app || "DokuZen",
    appVersion: json.app_version || "1.0.0",
    exportedAt: json.exported_at || "",
    sourcePlatform: json.source_platform || "desktop",
    settings: json.settings || {},
    themes,
    documents,
    forms,
    totals: json.totals || {
      theme_count: themes.length,
      document_count: documents.length,
      form_count: forms.length,
      read_document_count: documents.filter(d => d.isRead).length
    }
  };
}

export function filterDocuments(workspace, { theme = null, query = "", tag = null, status = "all" } = {}) {
  const q = (query || "").trim().toLowerCase();
  const selectedTag = (tag || "").trim().toLowerCase();

  return (workspace.documents || []).filter(doc => {
    if (theme && theme !== "all" && doc.theme !== theme) return false;
    if (status === "read" && !doc.isRead) return false;
    if (status === "unread" && doc.isRead) return false;
    if (selectedTag && !doc.tags.some(t => t.toLowerCase() === selectedTag)) return false;
    if (q) {
      const matchName = doc.filename.toLowerCase().includes(q);
      const matchNotes = doc.notes.toLowerCase().includes(q);
      const matchTag = doc.tags.some(t => t.toLowerCase().includes(q));
      if (!matchName && !matchNotes && !matchTag) return false;
    }
    return true;
  });
}

export function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function buildDemoWorkspace() {
  return parseWorkspace({
    schema: SCHEMA,
    schema_version: 1,
    export_app: "DokuZen",
    app_version: "1.0.1",
    exported_at: new Date().toISOString(),
    source_platform: "demo",
    redaction: {
      raw_documents_embedded: false,
      absolute_paths_included: false,
      secrets_included: false
    },
    settings: {
      theme: "light",
      language: "de",
      ocr_language: "deu+eng",
      duplicate_check: true,
      default_theme: "Allgemein"
    },
    themes: [
      { name: "Forschung", document_count: 3, read_count: 2 },
      { name: "Verträge", document_count: 2, read_count: 1 },
      { name: "Entwicklung", document_count: 2, read_count: 2 }
    ],
    documents: [
      { filename: "Kognitive_Architekturen_2026.pdf", extension: ".pdf", theme: "Forschung", is_read: true, read_date: "2026-09-10T14:30:00", tags: ["KI", "Architektur", "Research"], notes: "Exzellente Übersicht über Multi-Agent-Systeme", size_bytes: 2450120, added: "2026-09-01T09:00:00" },
      { filename: "Agenten_Governance_Whitepaper.pdf", extension: ".pdf", theme: "Forschung", is_read: false, read_date: null, tags: ["Governance", "Sicherheit"], notes: "Vor Veröffentlichung prüfen", size_bytes: 1890300, added: "2026-09-05T11:20:00" },
      { filename: "Synthese_Wissensnetze.pdf", extension: ".pdf", theme: "Forschung", is_read: true, read_date: "2026-09-12T16:00:00", tags: ["Graph", "Ontologie"], notes: "Grafiken zur ontologischen Verknüpfung", size_bytes: 1045900, added: "2026-09-08T15:10:00" },
      { filename: "Mietvertrag_Büro_2026.pdf", extension: ".pdf", theme: "Verträge", is_read: true, read_date: "2026-06-01T10:00:00", tags: ["Recht", "Immobilie"], notes: "Kündigungsfrist beachten", size_bytes: 980200, added: "2026-05-15T08:30:00" },
      { filename: "Geheimhaltungsvereinbarung_NDA.pdf", extension: ".pdf", theme: "Verträge", is_read: false, read_date: null, tags: ["Recht", "Partner"], notes: "Gegenzeichnung ausstehend", size_bytes: 420100, added: "2026-09-14T10:45:00" },
      { filename: "Architektur_DokuZen_V1.md", extension: ".md", theme: "Entwicklung", is_read: true, read_date: "2026-09-15T12:00:00", tags: ["DokuZen", "Design"], notes: "Schnittstellenspezifikation und PWA-Konzept", size_bytes: 65400, added: "2026-09-02T13:00:00" },
      { filename: "Release_Notes_1.0.1.txt", extension: ".txt", theme: "Entwicklung", is_read: true, read_date: "2026-09-16T18:00:00", tags: ["Release", "DokuZen"], notes: "Changelog für Version 1.0.1", size_bytes: 12800, added: "2026-09-16T17:30:00" }
    ],
    forms: [
      { name: "Klienten_Erfassungsbogen", field_count: 14, title: "Klienten-Erfassung", page_size: [210, 297] },
      { name: "Feedback_Formular_V2", field_count: 8, title: "Qualitäts-Feedback", page_size: [210, 297] }
    ],
    totals: {
      theme_count: 3,
      document_count: 7,
      form_count: 2,
      read_document_count: 5
    }
  });
}

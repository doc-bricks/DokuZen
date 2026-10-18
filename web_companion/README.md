# DokuZen Web Companion (PWA)

[Deutsch](README_de.md) | **English**

The **DokuZen Web Companion** is an offline-first Progressive Web Application (PWA) that enables users to browse, search, and read exported DokuZen workspace snapshots on mobile devices and secondary workstations without requiring Python or native desktop dependencies.

---

## 🏛️ Architecture & Local-First Principles

1. **100% Client-Side Execution:** All parsing and rendering occur strictly within the user's browser using vanilla modern JavaScript (`app.js`, `library.js`). No external server, telemetry, or network egress occurs.
2. **Service Worker Offline Cache (`sw.js`):** Assets are cached on first load. Once installed or opened, the application is fully functional without internet connectivity.
3. **Hermetic Snapshot Ingestion:** Reads structured JSON workspace files generated via DokuZen's *Offline Workspace Export* dialog, validated against schema rules that exclude absolute paths, secrets, and raw binaries.
4. **Zero-Egress Security Invariant:** In accordance with the project's core security policy (`SECURITY.md`), no personal data or document content is transmitted outside the local device.

---

## 🚀 Usage & Deployment

### Local Inspection
Open `index.html` directly in any modern web browser or serve via a local static file server:

```bash
# Optional local test server
python -m http.server 8080 --directory web_companion
```

### Loading Workspace Snapshots
1. Export a workspace snapshot from the DokuZen desktop application (`Tools` -> `Export Workspace`).
2. Open the Web Companion and drop or select the `.json` snapshot file.
3. Browse document metadata, thematic libraries, and sanitised text contents.

---

## 🔒 Security & Privacy

- **Local-Only:** Never establishes outbound HTTP/WebSocket connections.
- **Sanitisation:** Verifies that snapshot payloads conform to schema constraints (`validate_workspace_snapshot`).
- **No Third-Party CDNs:** All stylesheets (`style.css`), scripts, and icons are bundled locally.

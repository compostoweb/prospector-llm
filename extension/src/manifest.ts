import { defineManifest } from "@crxjs/vite-plugin";

const apiHostPermissions = [
  "http://localhost:8000/*",
  "https://localhost:8000/*",
  "https://*.compostoweb.com.br/*",
];

export default defineManifest({
  manifest_version: 3,
  name: "Prospector LinkedIn Capture",
  version: "0.1.0",
  description: "Captura e importa posts do LinkedIn para o Prospector.",
  permissions: ["storage", "identity", "activeTab", "scripting", "sidePanel"],
  host_permissions: [
    "https://www.linkedin.com/*",
    "https://*.linkedin.com/*",
    ...apiHostPermissions,
  ],
  background: {
    service_worker: "src/background/index.ts",
    type: "module",
  },
  action: {
    default_title: "Prospector",
  },
  side_panel: {
    default_path: "src/sidepanel/index.html",
  },
  options_page: "src/options/index.html",
  content_scripts: [
    {
      matches: ["https://www.linkedin.com/*", "https://linkedin.com/*"],
      js: ["src/content/linkedin-feed.ts"],
      run_at: "document_idle",
    },
  ],
});

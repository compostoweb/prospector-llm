import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { PopupApp } from "../popup/app";
import "../popup/popup.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root do side panel nao encontrado.");
}

createRoot(root).render(
  <StrictMode>
    <PopupApp surfaceMode="sidepanel" />
  </StrictMode>,
);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { PopupApp } from "./app";
import "./popup.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root do popup nao encontrado.");
}

createRoot(root).render(
  <StrictMode>
    <PopupApp />
  </StrictMode>,
);

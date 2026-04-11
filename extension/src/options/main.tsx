import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { OptionsApp } from "./app";
import "./options.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root das options nao encontrado.");
}

createRoot(root).render(
  <StrictMode>
    <OptionsApp />
  </StrictMode>,
);

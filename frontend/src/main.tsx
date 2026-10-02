import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AppProviders } from "@/app-providers";
import { App } from "@/app";
import "@/index.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Application root element is missing.");
}

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <AppProviders>
        <App />
      </AppProviders>
    </BrowserRouter>
  </StrictMode>,
);

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Keep previously shared one-page links useful after the move to dedicated pages.
const legacyPages: Record<string, string> = {
  "#services": "/services/", "#process": "/approach/", "#pricing": "/pricing/",
  "#about": "/about/", "#contact": "/contact/",
};
const destination = legacyPages[window.location.hash];
if (["/", "/index.html"].includes(window.location.pathname) && destination) {
  window.location.replace(destination + window.location.search);
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

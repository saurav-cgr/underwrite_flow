import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./app";
import "./tokens.css";
import "./styles.css";
import "./components.css";
import "./responsive.css";
import "./details.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

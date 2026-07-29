import React from "react";
import { createRoot } from "react-dom/client";
import Home from "./page";
import UrbanismePage from "./urbanisme/page";
import AgriculturePage from "./agriculture/page";
import RisquesPage from "./risques/page";
import HabitatPage from "./habitat/page";
import SecuriteRoutierePage from "./securite-routiere/page";
import "./globals.css";

const basePath = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
const pathname = window.location.pathname.replace(basePath, "") || "/";
const routes: Record<string, React.ComponentType> = {
  "/": Home,
  "/urbanisme": UrbanismePage,
  "/agriculture": AgriculturePage,
  "/risques": RisquesPage,
  "/habitat": HabitatPage,
  "/securite-routiere": SecuriteRoutierePage,
};
const Page = routes[pathname.replace(/\/$/, "") || "/"] || Home;

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><Page /></React.StrictMode>,
);

"use client";

import { useEffect, useRef, useState } from "react";
import { ToolHeader } from "../components/ToolHeader";

const layerCatalog = [
  { id: "cultures", label: "Cultures déclarées", detail: "RPG 2024 · types de cultures", layer: "LANDUSE.AGRICULTURE2024", color: "linear-gradient(135deg,#f7e86a 0 25%,#00d822 25% 50%,#e54225 50% 75%,#099184 75%)", active: true },
  { id: "prairies", label: "Prairies permanentes", detail: "RPG 2024 · surfaces en herbe", layer: "IGNF_RPG_PRAIRIES-PERMANENTES_2024", color: "#ffda73", active: false },
  { id: "haies", label: "Haies et bocage", detail: "BD Haie IGN · continuités", layer: "IGNF_BD-HAIE-V1_2020", color: "#fff000", active: false },
  { id: "znieff1", label: "ZNIEFF de type I", detail: "Secteurs de fort intérêt écologique", layer: "Patrinat_ZNIEFF1", color: "#008b2d", active: false },
  { id: "znieff2", label: "ZNIEFF de type II", detail: "Grands ensembles naturels", layer: "Patrinat_ZNIEFF2", color: "#86ce8d", active: false },
];

const cultureNames: Record<string, string> = {
  BTH: "Blé tendre", BTN: "Blé tendre", BDH: "Blé dur", ORH: "Orge d’hiver", ORP: "Orge de printemps",
  MIS: "Maïs", MIE: "Maïs ensilage", MID: "Maïs doux", COL: "Colza", TOU: "Tournesol", SOJ: "Soja",
  PPH: "Prairie permanente", PTR: "Prairie temporaire", LU5: "Luzerne", J6S: "Jachère", VIG: "Vigne",
  VRG: "Verger", PTC: "Pois protéagineux", BET: "Betterave", POM: "Pomme de terre", LEG: "Légumes",
};

type CropYear = { year: number; code: string; name: string; surface: number; group?: string; feature?: any };
type AgricultureMode = "all" | "bio";
type BioParcel = { culture: string; group: string; surface: number; year: number };
type BioStat = { label: string; surface: number };
type EnvironmentItem = { label: string; names: string[] };

function wmtsUrl(layer: string) {
  return `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/png`;
}

export default function AgriculturePage() {
  const mapNode = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const overlaysRef = useRef<Record<string, any>>({});
  const bioLayerRef = useRef<any>(null);
  const bioDataRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const parcelRef = useRef<any>(null);
  const [activeLayers, setActiveLayers] = useState<string[]>(["cultures"]);
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("Val-d’Oise");
  const [message, setMessage] = useState("Commencez par afficher les informations qui répondent à votre question.");
  const [cropHistory, setCropHistory] = useState<CropYear[]>([]);
  const [environment, setEnvironment] = useState<EnvironmentItem[]>([]);
  const [agricultureMode, setAgricultureMode] = useState<AgricultureMode>("all");
  const [bioParcel, setBioParcel] = useState<BioParcel | null>(null);
  const [bioDataReady, setBioDataReady] = useState(false);
  const [bioStats, setBioStats] = useState<BioStat[]>([]);
  const [bioTotal, setBioTotal] = useState(0);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [mapZoom, setMapZoom] = useState(10);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  useEffect(() => {
    if (!mapNode.current || mapRef.current) return;
    const launch = () => {
      const L = (window as any).L; if (!L || !mapNode.current || mapRef.current) return;
      const map = L.map(mapNode.current, { zoomControl: false, maxBoundsViscosity: .65 }).setView([49.075, 2.105], 10);
      L.control.zoom({ position: "bottomright" }).addTo(map);
      map.createPane("baseTiles"); map.getPane("baseTiles").style.zIndex = "190";
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { pane: "baseTiles", maxZoom: 19, attribution: "© OpenStreetMap contributors" }).addTo(map);
      map.on("zoomend", () => setMapZoom(map.getZoom()));
      layerCatalog.forEach((item) => {
        const layer = L.tileLayer(wmtsUrl(item.layer), { minZoom: 6, maxZoom: 19, opacity: item.id === "cultures" ? .72 : .78, attribution: "© IGN · ASP · PatriNat" });
        overlaysRef.current[item.id] = layer;
        if (item.active) layer.addTo(map);
      });
      fetch(`${(import.meta.env.BASE_URL || "/").replace(/\/$/, "")}/data/cartobio-val-doise.geojson`).then((response) => response.json()).then((data) => {
        bioDataRef.current = data;
        const totals = new Map<string, number>();
        data.features?.forEach((feature: any) => {
          const label = feature.properties?.groupe_culture || "Autres";
          totals.set(label, (totals.get(label) || 0) + Number(feature.properties?.surface_ha || 0));
        });
        setBioTotal([...totals.values()].reduce((sum, surface) => sum + surface, 0));
        setBioStats([...totals].map(([label, surface]) => ({ label, surface })).sort((a, b) => b.surface - a.surface).slice(0, 5));
        setBioDataReady(true);
      }).catch(() => undefined);
      fetch("https://geo.api.gouv.fr/departements/95/communes?fields=nom,code,contour&format=geojson&geometry=contour").then((r) => r.json()).then((communes) => {
        const holes: any[] = [];
        communes.features?.forEach((feature: any) => {
          const geometry = feature.geometry;
          if (geometry?.type === "Polygon" && geometry.coordinates?.[0]) holes.push(geometry.coordinates[0]);
          if (geometry?.type === "MultiPolygon") geometry.coordinates?.forEach((polygon: any) => { if (polygon?.[0]) holes.push(polygon[0]); });
        });
        L.geoJSON({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]], ...holes] } }, {
          style: { stroke: false, fillColor: "#f4f7fb", fillOpacity: .82, fillRule: "evenodd" }, interactive: false,
        }).addTo(map);
        const territory = L.geoJSON(communes, { style: { color: "#667085", weight: .75, opacity: .58, fillOpacity: 0 }, interactive: false }).addTo(map);
        const bounds = territory.getBounds(); if (bounds.isValid()) { map.fitBounds(bounds, { padding: [25, 25] }); map.setMaxBounds(bounds.pad(.28)); }
      }).catch(() => undefined);
      map.on("click", (event: any) => locatePoint(event.latlng.lng, event.latlng.lat));
      mapRef.current = map;
    };
    if ((window as any).L) launch(); else {
      if (!document.getElementById("leaflet-css")) { const link = document.createElement("link"); link.id = "leaflet-css"; link.rel = "stylesheet"; link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"; document.head.appendChild(link); }
      const existing = document.querySelector<HTMLScriptElement>('script[data-leaflet="true"]');
      if (existing) existing.addEventListener("load", launch, { once: true }); else { const script = document.createElement("script"); script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"; script.dataset.leaflet = "true"; script.onload = launch; document.body.appendChild(script); }
    }
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    Object.entries(overlaysRef.current).forEach(([id, layer]) => {
      const shouldShow = agricultureMode === "all" && activeLayers.includes(id);
      if (shouldShow && !map.hasLayer(layer)) layer.addTo(map);
      if (!shouldShow && map.hasLayer(layer)) map.removeLayer(layer);
    });
    if (bioLayerRef.current) { map.removeLayer(bioLayerRef.current); bioLayerRef.current = null; }
    if (agricultureMode === "bio" && bioDataRef.current) {
      const L = (window as any).L;
      bioLayerRef.current = L.geoJSON(bioDataRef.current, {
        style: { color: "#18753c", weight: 1.4, fillColor: "#55a66b", fillOpacity: .55 },
        onEachFeature: (feature: any, layer: any) => layer.on("click", (event: any) => {
          L.DomEvent.stopPropagation(event);
          const properties = feature.properties || {};
          setBioParcel({ culture: properties.culture_nom || "Culture biologique", group: properties.groupe_culture || "Non renseigné", surface: Number(properties.surface_ha || 0), year: Number(properties.annee || 2024) });
          setCropHistory([]); setLocation("Parcelle certifiée bio"); setMessage("Parcelle CartoBio sélectionnée."); setDetailsOpen(true); loadEnvironment(event.latlng.lng, event.latlng.lat);
        }),
      }).addTo(map);
    }
  }, [agricultureMode, activeLayers, bioDataReady]);

  function toggleLayer(id: string) {
    if (agricultureMode === "bio") return;
    const layer = overlaysRef.current[id]; const map = mapRef.current; if (!layer || !map) return;
    setActiveLayers((current) => {
      if (current.includes(id)) { map.removeLayer(layer); return current.filter((value) => value !== id); }
      layer.addTo(map); return [...current, id];
    });
  }

  function changeAgricultureMode(mode: AgricultureMode) {
    setAgricultureMode(mode); setBioParcel(null);
    setMessage(mode === "bio" ? "Les parcelles certifiées bio sont affichées en vert." : "Commencez par afficher les informations qui répondent à votre question.");
  }

  function closeDetails() {
    const map = mapRef.current;
    if (map && markerRef.current) map.removeLayer(markerRef.current);
    if (map && parcelRef.current) map.removeLayer(parcelRef.current);
    markerRef.current = null;
    parcelRef.current = null;
    setDetailsOpen(false);
    setQuery("");
    setLocation("Val-d’Oise");
    setCropHistory([]);
    setEnvironment([]);
    setBioParcel(null);
    setAnalysisLoading(false);
    setMessage(agricultureMode === "bio" ? "Les parcelles certifiées bio sont affichées en vert." : "Commencez par afficher les informations qui répondent à votre question.");
  }

  async function loadEnvironment(lon: number, lat: number) {
    const geom = encodeURIComponent(JSON.stringify({ type: "Point", coordinates: [lon, lat] }));
    const sources = [
      ["ZNIEFF de type I", "znieff1"], ["ZNIEFF de type II", "znieff2"],
      ["Natura 2000 · habitats", "natura-habitat"], ["Natura 2000 · oiseaux", "natura-oiseaux"],
    ];
    try {
      const responses = await Promise.all(sources.map(([, endpoint]) => fetch(`https://apicarto.ign.fr/api/nature/${endpoint}?geom=${geom}`)));
      const collections = await Promise.all(responses.map((response) => response.ok ? response.json() : { features: [] }));
      setEnvironment(sources.map(([label], index) => ({ label, names: (collections[index].features || []).map((feature: any) => feature.properties?.nom_site || feature.properties?.nom || feature.properties?.site_name || "Zone identifiée") })));
    } catch { setEnvironment([]); }
  }

  async function locatePoint(lon: number, lat: number) {
    const L = (window as any).L; const map = mapRef.current;
    if (L && map) { if (markerRef.current) map.removeLayer(markerRef.current); markerRef.current = L.circleMarker([lat, lon], { radius: 7, color: "#e1000f", fillColor: "#fff", fillOpacity: 1, weight: 3 }).addTo(map); }
    setMessage("Lecture du RPG et du contexte environnemental…"); setAnalysisLoading(true); setCropHistory([]); setBioParcel(null); setEnvironment([]); setDetailsOpen(true); loadEnvironment(lon, lat);
    try {
      const geom = encodeURIComponent(JSON.stringify({ type: "Point", coordinates: [lon, lat] }));
      const [addressResponse, ...responses] = await Promise.all([
        fetch(`https://api-adresse.data.gouv.fr/reverse/?lon=${lon}&lat=${lat}&limit=1`),
        fetch(`https://apicarto.ign.fr/api/rpg/v2?annee=2024&geom=${geom}`),
        fetch(`https://apicarto.ign.fr/api/rpg/v2?annee=2023&geom=${geom}`),
        fetch(`https://apicarto.ign.fr/api/rpg/v2?annee=2022&geom=${geom}`),
      ]);
      const data = await addressResponse.json(); const p = data.features?.[0]?.properties;
      setLocation(p ? `${p.city} · ${p.postcode}` : `${lat.toFixed(5)}, ${lon.toFixed(5)}`);
      const rpgData = await Promise.all(responses.slice(0, 3).map((response) => response.ok ? response.json() : { features: [] }));
      const history = rpgData.map((collection, index) => {
        const feature = collection.features?.[0]; const props = feature?.properties || {}; const code = props.code_cultu || "—";
        return feature ? { year: 2024 - index, code, name: cultureNames[code] || `Culture ${code}`, surface: Number(props.surf_parc || 0), group: props.code_group, feature } : null;
      }).filter(Boolean) as CropYear[];
      setCropHistory(history);
      if (parcelRef.current && map) map.removeLayer(parcelRef.current);
      if (history[0]?.feature && L && map) parcelRef.current = L.geoJSON(history[0].feature, { style: { color: "#000091", weight: 4, fillColor: "#fff", fillOpacity: .18 } }).addTo(map);
      setMessage(history.length ? "Parcelle RPG identifiée. Les informations détaillées sont affichées ci-dessous." : "Aucune parcelle déclarée au RPG n’a été trouvée à ce point.");
    } catch { setLocation(`${lat.toFixed(5)}, ${lon.toFixed(5)}`); setMessage("Le point est repéré, mais une source n’a pas répondu."); }
    finally { setAnalysisLoading(false); }
  }

  async function search(event: React.FormEvent) {
    event.preventDefault(); if (!query.trim()) return;
    setMessage("Recherche du lieu…");
    try {
      const response = await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(query)}&limit=1&autocomplete=0`); const data = await response.json(); const feature = data.features?.[0];
      if (!feature) { setMessage("Lieu non trouvé dans la Base Adresse Nationale."); return; }
      const [lon, lat] = feature.geometry.coordinates; setQuery(feature.properties.label); mapRef.current?.setView([lat, lon], 15); await locatePoint(lon, lat);
    } catch { setMessage("La recherche est momentanément indisponible."); }
  }

  return <main className="agri-tool">
    <ToolHeader title="Observatoire agricole" subtitle="Cultures · prairies · haies · environnement" />
    <div className="agri-layout">
      <aside className="agri-panel">
        <div className="agri-intro"><span>Observatoire 03</span><h1>Lire les espaces agricoles</h1><p>Repérez les productions, les prairies et les continuités bocagères, puis croisez-les avec les secteurs d’intérêt écologique.</p></div>
        <form className="agri-search" onSubmit={search}><label htmlFor="agri-address">Rechercher une commune ou une adresse</label><div><input id="agri-address" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Marines, Cergy, 12 rue…" /><button>Localiser</button></div></form>
        <fieldset className="agriculture-mode" aria-label="Type d’agriculture"><div>
          <label><input type="radio" name="agriculture-mode" value="all" checked={agricultureMode === "all"} onChange={() => changeAgricultureMode("all")} /><span>Toutes les agricultures</span></label>
          <label><input type="radio" name="agriculture-mode" value="bio" checked={agricultureMode === "bio"} onChange={() => changeAgricultureMode("bio")} /><span>Bio uniquement</span></label>
        </div></fieldset>
        {agricultureMode === "bio" && bioStats.length > 0 && <section className="bio-chart"><div><strong>Surfaces bio</strong><small>{bioTotal.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} ha · principales cultures</small></div>{bioStats.map((item) => <div className="bio-chart-row" key={item.label}><span>{item.label}</span><i><em style={{ width: `${item.surface / bioStats[0].surface * 100}%` }} /></i><b>{item.surface.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} ha</b></div>)}</section>}
        {agricultureMode === "all" && <section className="agri-layers"><div className="agri-section-title"><span>Choisir les informations</span><small>{activeLayers.length} couche(s) affichée(s)</small></div>{layerCatalog.map((item) => <label className="agri-layer" key={item.id}><input type="checkbox" checked={activeLayers.includes(item.id)} onChange={() => toggleLayer(item.id)} /><i style={{ background: item.color }} /><span><strong>{item.label}</strong><small>{item.detail}</small></span></label>)}</section>}
        <a className="bio-link" href="https://www.agencebio.org/cartobio/" target="_blank" rel="noreferrer"><span><small>Agriculture biologique</small><strong>Explorer les parcelles certifiées bio</strong></span><b>↗</b></a>
      </aside>
      <section className="agri-map-wrap"><div className="agri-zoom-level"><strong>{mapZoom >= 14 ? "Détail agricole" : "Vue départementale"}</strong><span>zoom {mapZoom}</span></div><div className="agri-map-note"><strong>{mapZoom >= 12 ? "Cliquez sur une parcelle" : "Zoomez pour explorer"}</strong><span>{mapZoom >= 12 ? "La fiche détaillée s’ouvre à droite." : "Les cultures et les parcelles bio deviennent plus lisibles."}</span></div><div ref={mapNode} className="agri-map" aria-label="Carte interactive des espaces agricoles du Val-d’Oise" /></section>
    </div>
    {detailsOpen && <aside className="observatory-drawer" aria-label="Détail agricole"><div className="observatory-drawer-head"><button onClick={closeDetails} aria-label="Fermer et effacer la sélection">×</button><small>Secteur observé</small><h2>{location}</h2><p>{message}</p></div><div className="observatory-drawer-body">
      {(analysisLoading || cropHistory.length > 0 || bioParcel) && <section className="crop-analysis"><div className="agri-section-title"><span>Lecture de la parcelle</span><small>{bioParcel ? "CartoBio · anonymisé" : "RPG public · anonymisé"}</small></div>{analysisLoading ? <p className="agri-loading">Analyse des millésimes agricoles…</p> : <>{bioParcel ? <div className="crop-primary"><small>Parcelle certifiée bio · {bioParcel.year}</small><strong>{bioParcel.culture}</strong><span>{bioParcel.surface.toLocaleString("fr-FR")} ha · {bioParcel.group}</span></div> : <><div className="crop-primary"><small>Culture déclarée en 2024</small><strong>{cropHistory[0]?.name}</strong><span>{cropHistory[0]?.surface.toLocaleString("fr-FR")} ha · code {cropHistory[0]?.code}</span></div><div className="crop-history"><strong>Historique cultural</strong>{cropHistory.map((crop) => <div key={crop.year}><b>{crop.year}</b><span>{crop.name}</span><i><em style={{ width: `${Math.min(100, Math.max(12, crop.surface * 5))}%` }} /></i><small>{crop.surface.toLocaleString("fr-FR")} ha</small></div>)}</div></>}<p className="ownership-note"><b>Exploitant non publié.</b> Les données parcellaires sont anonymisées.</p></>}</section>}
      {environment.length > 0 && <section className="agri-environment"><div className="agri-section-title"><span>Contexte environnemental</span><small>au point sélectionné</small></div>{environment.map((item) => <div key={item.label}><span>{item.label}</span><b className={item.names.length ? "inside" : ""}>{item.names.length ? item.names.join(" · ") : "Hors zone"}</b></div>)}</section>}
    </div></aside>}
  </main>;
}

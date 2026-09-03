"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type FeatureCollection = { type: "FeatureCollection"; features: any[] };
type AddressResult = { label: string; city?: string; citycode?: string; postcode?: string; coordinates: [number, number] };
type ParcelResult = { address: string; addressLabel: string; commune: string; codeInsee: string; parcel?: any; zones: any[]; servitudes: any[]; risks: any[]; buildings: any[]; publicLand?: [string,string,string]; mos?: { mos2021?: number; mos2025?: number; surface?: number } };

const emptyCollection: FeatureCollection = { type: "FeatureCollection", features: [] };

function pointGeometry(lon: number, lat: number) {
  return encodeURIComponent(JSON.stringify({ type: "Point", coordinates: [lon, lat] }));
}

function nearbyGeometry(lon: number, lat: number) {
  const dx = 0.00055;
  const dy = 0.00038;
  return encodeURIComponent(JSON.stringify({
    type: "Polygon",
    coordinates: [[[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy], [lon - dx, lat + dy], [lon - dx, lat - dy]]],
  }));
}

function geometryCenter(geometry: any): [number, number] {
  const points: number[][] = [];
  const collect = (value: any) => {
    if (Array.isArray(value) && typeof value[0] === "number") points.push(value);
    else if (Array.isArray(value)) value.forEach(collect);
  };
  collect(geometry?.coordinates);
  if (!points.length) return [0, 0];
  return [points.reduce((sum, p) => sum + p[0], 0) / points.length, points.reduce((sum, p) => sum + p[1], 0) / points.length];
}

function closestParcel(collection: FeatureCollection, lon: number, lat: number): FeatureCollection {
  if (collection.features.length < 2) return collection;
  const selected = [...collection.features].sort((a, b) => {
    const [ax, ay] = geometryCenter(a.geometry); const [bx, by] = geometryCenter(b.geometry);
    return ((ax - lon) ** 2 + (ay - lat) ** 2) - ((bx - lon) ** 2 + (by - lat) ** 2);
  })[0];
  return { type: "FeatureCollection", features: selected ? [selected] : [] };
}

function firstValue(object: any, keys: string[], fallback = "Non renseigné") {
  for (const key of keys) if (object?.[key] !== undefined && object?.[key] !== null && object?.[key] !== "") return String(object[key]);
  return fallback;
}

const mosLabels: Record<number, string> = {
  1:"Bois ou forêts",2:"Coupes ou clairères en forêts",3:"Peupleraies",4:"Espaces ouverts à végétation arborée ou herbacée",5:"Berges",6:"Terres labourées",7:"Prairies",8:"Vergers, pépinières",9:"Maraîchage, horticulture",10:"Cultures intensives sous serres",11:"Eau fermée",12:"Cours d’eau",13:"Parcs ou jardins publics",14:"Autres espaces verts publics",15:"Jardins familiaux",16:"Jardins de l’habitat",17:"Terrains de sport en plein air",18:"Tennis découverts",19:"Baignade",20:"Golfs",21:"Hippodromes",22:"Camping, caravaning",23:"Parcs liés aux activités de loisirs",24:"Esplanades et places",25:"Cimetières",26:"Surfaces engazonnées avec ou sans arbustes",27:"Terrains vacants",28:"Habitat pavillonnaire",29:"Ensemble d’habitat pavillonnaire",30:"Habitat rural",31:"Habitat continu bas",32:"Habitat collectif continu haut",33:"Habitat collectif discontinu",34:"Prisons",35:"Habitat autre",36:"Activités en tissu urbain mixte",37:"Grandes emprises industrielles",38:"Zones d’activités économiques",39:"Entreposage à l’air libre",40:"Entrepôts logistiques",41:"Stockage de données",42:"Grandes surfaces commerciales",43:"Autres commerces",44:"Stations-services",45:"Bureaux",46:"Production d’eau",47:"Assainissement",48:"Électricité",49:"Gaz",50:"Pétrole",51:"Chaleur",52:"Extraction de matériaux",53:"Tri et valorisation des déchets",54:"Stockage de déchets",55:"Installations sportives couvertes",56:"Centres équestres",57:"Piscines couvertes",58:"Piscines de plein air",59:"Circuits sportifs",60:"Enseignement du premier degré",61:"Enseignement secondaire",62:"Enseignement supérieur",63:"Centre de formation professionnelle",64:"Hôpitaux, cliniques",65:"Autres équipements de santé",66:"Grands centres de congrès et d’exposition",67:"Équipements culturels et de loisirs",68:"Sièges de grandes administrations",69:"Équipements de sécurité civile",70:"Équipements à accès public limité",71:"Lieux de culte",72:"Autres équipements de proximité",73:"Emprise ferrée",74:"Voies routières",75:"Parkings de surface",76:"Parkings en étages",77:"Gares routières, dépôts de bus",78:"Installations aéroportuaires",79:"Chantiers",
};

function numberValue(value: unknown) { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0; }
function uniqueValues(values: unknown[]) { return [...new Set(values.flatMap((value) => Array.isArray(value) ? value : value ? [value] : []).map(String))]; }
function formatNumber(value: number, unit = "") { return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(value)}${unit}`; }
function formatPdfNumber(value:number){ return Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g," "); }
function streetOnly(address: string) { return address.replace(/\s+\d{5}\s+.+$/u, "").trim() || address; }
function classifyOwners(owners: string[]) {
  if (owners.some((owner) => /\bETAT\b|MINISTERE|DIRECTION (DEPARTEMENTALE|REGIONALE|GENERALE)|PREFECTURE/i.test(owner))) return "Foncier de l’État détecté";
  if (owners.some((owner) => /COMMUNE|DEPARTEMENT|REGION|COMMUNAUTE|METROPOLE|SYNDICAT|ETABLISSEMENT PUBLIC|OFFICE PUBLIC/i.test(owner))) return "Foncier public local détecté";
  return owners.length ? "Personne morale identifiée" : "Non disponible en données ouvertes";
}
function mosColor(code: number) {
  if (code <= 5) return "#18753c";
  if (code <= 10) return "#e3b341";
  if (code <= 12) return "#0098d8";
  if (code <= 27) return "#62b467";
  if (code <= 35) return "#e07a9a";
  if (code <= 54) return "#a05a9c";
  if (code <= 72) return "#5576b9";
  if (code <= 78) return "#737b87";
  return "#e1000f";
}
function publicLandColor(code: string) { return ({ "1":"#e1000f", "2":"#6f4c9b", "3":"#000091", "4":"#18753c", "5":"#0098d8", "6":"#e3b341", "9":"#7b61a8" } as Record<string,string>)[code] || "#687787"; }
function zoneColor(feature: any) { const zone=firstValue(feature?.properties,["typezone","libelle","libelle_zone"],"").toUpperCase(); if(zone.startsWith("AU"))return "#e3a008"; if(zone.startsWith("U"))return "#df4f70"; if(zone.startsWith("A"))return "#d6a721"; if(zone.startsWith("N"))return "#27864d"; return "#3478b8"; }
function supCode(feature:any){ return firstValue(feature?.properties,["suptype","categorie"],"").toUpperCase() || String(feature?.properties?.partition||"").split("_").at(-1)?.toUpperCase() || "SUP"; }
function supDescription(code:string){ const labels:Record<string,string>={A1:"Protection des bois et forêts",A2:"Canalisations souterraines d’irrigation",A3:"Aménagement des eaux et canaux d’irrigation",A4:"Passage le long des cours d’eau",A5:"Canalisations publiques d’eau et d’assainissement",A6:"Écoulement des eaux nuisibles",A7:"Forêts de protection",A8:"Protection des plantations",A9:"Zone agricole protégée",A10:"Protection des terres agricoles",AC1:"Protection des monuments historiques",AC2:"Sites classés ou inscrits",AC3:"Réserves naturelles",AC4:"Patrimoine architectural et urbain",AS1:"Protection des eaux potables et minérales",AS2:"Protection des établissements conchylicoles",EL3:"Halage et marchepied",EL5:"Visibilité sur les voies publiques",EL7:"Alignement des voies publiques",EL11:"Accès aux routes express et déviations",I1:"Canalisations d’hydrocarbures",I3:"Canalisations de gaz",I4:"Transport et distribution d’électricité",I5:"Canalisations de produits chimiques",I6:"Mines et carrières",I9:"Réseaux de chaleur et de froid",INT1:"Voisinage des cimetières",JS1:"Protection des équipements sportifs",PM1:"Plan de prévention des risques naturels, miniers ou technologiques",PM2:"Installations classées et risques technologiques",PM3:"Plan de prévention des risques technologiques",PT1:"Protection des centres radioélectriques",PT2:"Protection contre les obstacles radioélectriques",PT3:"Réseaux de télécommunication",T1:"Voies ferrées",T2:"Survol par téléphérique",T3:"Tréfonds ferroviaires",T4:"Balisage aéronautique",T5:"Dégagement aéronautique",T6:"Installations de navigation aérienne",T7:"Servitudes aéronautiques extérieures"}; return labels[code]||`Servitude d’utilité publique ${code}`; }
function supFamily(code:string){ if(/^AC|^AR|^INT|^JS/.test(code))return "Patrimoine et équipements"; if(/^PM/.test(code))return "Risques"; if(/^A[2-6]$|^AS/.test(code))return "Eau"; if(/^I|^PT/.test(code))return "Réseaux et énergie"; if(/^EL|^T/.test(code))return "Transports"; if(/^A/.test(code))return "Agriculture et environnement"; return "Autres servitudes"; }
function supColor(feature:any){ const colors:Record<string,string>={"Patrimoine et équipements":"#6f4c9b",Risques:"#e1000f",Eau:"#0098d8","Réseaux et énergie":"#e3a008",Transports:"#0053b3","Agriculture et environnement":"#18753c","Autres servitudes":"#687787"}; return colors[supFamily(supCode(feature))]; }
function supTitle(feature:any){ const p=feature?.properties||{}, code=supCode(feature); return firstValue(p,["nomsuplitt","nomreg"],"") || supDescription(code); }
function escapeHtml(value:unknown){ return String(value??"").replace(/[&<>"']/g,(character)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[character]||character)); }
const publicBuildingNatures = new Set(["Mairie","Préfecture","Sous-préfecture","Hôtel de région","Hôtel de département","Établissement de santé","Établissement pénitentiaire"]);
function isPublicBuildingFeature(feature:any){
  const properties=feature?.properties||{};
  const nature=String(properties.nature||""), usage1=String(properties.usage_1||""), usage2=String(properties.usage_2||"");
  return publicBuildingNatures.has(nature) || usage1==="Religieux" || usage2==="Religieux" || usage1==="Sportif" || usage2==="Sportif";
}
function dpeColor(classe:string){ return ({A:"#008941",B:"#3cb44a",C:"#a8c936",D:"#e3b341",E:"#e07a2c",F:"#e1541f",G:"#c1121f"} as Record<string,string>)[String(classe||"").toUpperCase()] || "#687787"; }
function publicRiskColor(count:number){ if(count>=4)return "#c1121f"; if(count>=2)return "#e1541f"; if(count>=1)return "#e3b341"; return "#687787"; }

export default function UrbanismePage() {
  const basePath = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
  const mapNode = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const layersRef = useRef<any[]>([]);
  const parcelTilesRef = useRef<any>(null);
  const buildingTilesRef = useRef<any>(null);
  const buildingVectorRef = useRef<any>(null);
  const buildingRequestRef = useRef<AbortController | null>(null);
  const pluTilesRef = useRef<any>(null);
  const supTilesRef = useRef<any>(null);
  const pluOverviewLayerRef = useRef<any>(null);
  const supOverviewLayerRef = useRef<any>(null);
  const mosLayerRef = useRef<any>(null);
  const mosOverviewLayerRef = useRef<any>(null);
  const publicLandLayerRef = useRef<any>(null);
  const publicLandDataRef = useRef<Record<string,[string,string,string]> | null>(null);
  const publicRequestRef = useRef<AbortController | null>(null);
  const publicDepartmentLoadingRef = useRef(false);
  const publicDepartmentLoadedRef = useRef(false);
  const communesDataRef = useRef<FeatureCollection | null>(null);
  const departmentBoundsRef = useRef<any>(null);
  const departmentMaskRef = useRef<any>(null);
  const mosRequestRef = useRef<AbortController | null>(null);
  const gpuRequestRef = useRef<AbortController | null>(null);
  const dpePublicLayerRef = useRef<any>(null);
  const dpePublicRequestRef = useRef<AbortController | null>(null);
  const publicRisksLayerRef = useRef<any>(null);
  const publicRisksRequestRef = useRef<AbortController | null>(null);
  const markerRef = useRef<any>(null);
  const communeFocusLayerRef = useRef<any>(null);
  const selectionPointRef = useRef<[number, number] | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [mapZoom, setMapZoom] = useState(10);
  const [result, setResult] = useState<ParcelResult | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [layerFeedback, setLayerFeedback] = useState("Vue départementale : choisissez une adresse ou une commune.");
  const [communes, setCommunes] = useState<any[]>([]);
  const [communeCode, setCommuneCode] = useState("");
  const [communeQuery, setCommuneQuery] = useState("");
  const [communeSuggestionsOpen, setCommuneSuggestionsOpen] = useState(false);
  const [activeCommune, setActiveCommune] = useState("");
  const [layers, setLayers] = useState({ parcels: false, buildings: false, mos: false, plu: false, servitudes: false, publicLand: false, dpePublic: false, publicRisks: false });
  const [publicLandFilter, setPublicLandFilter] = useState<"state"|"all">("state");
  const publicLandFilterRef = useRef<"state"|"all">("state");
  const [publicDataReady, setPublicDataReady] = useState(false);
  const [layerLoading, setLayerLoading] = useState({ buildings:false, mos:false, plu:false, servitudes:false, publicLand:false, dpePublic:false, publicRisks:false });
  const [services, setServices] = useState<Record<string,"checking"|"online"|"error">>({ Adresse:"checking", Cadastre:"checking", Urbanisme:"checking", Risques:"checking", Bâti:"checking", MOS:"checking", Foncier:"checking" });
  const [message, setMessage] = useState("Recherchez une adresse ou cliquez sur la carte.");
  const layersStateRef = useRef(layers);
  useEffect(() => { layersStateRef.current = layers; }, [layers]);
  useEffect(() => {
    const probes: Record<string,string> = { Adresse:"https://api-adresse.data.gouv.fr/search/?q=Pontoise&limit=1", Cadastre:`https://apicarto.ign.fr/api/cadastre/parcelle?geom=${pointGeometry(2.1,49.05)}`, Urbanisme:`https://apicarto.ign.fr/api/gpu/zone-urba?geom=${pointGeometry(2.1,49.05)}`, Risques:"https://georisques.gouv.fr/api/v1/gaspar/risques?latlon=2.1,49.05", Bâti:"https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet/parcelle?parcelle_id=eq.95018000AH0001", MOS:"https://geoweb.iau-idf.fr/agsmap1/rest/services/OPENDATA/OpendataIAU4/MapServer/25/query?f=json&where=1%3D0&returnCountOnly=true", Foncier:`${basePath}/data/foncier-public-95.json` };
    Object.entries(probes).forEach(([name,url]) => fetch(url).then((response) => setServices((current) => ({...current,[name]:response.ok ? "online" : "error"}))).catch(() => setServices((current) => ({...current,[name]:"error"}))));
  }, []);

  useEffect(() => {
    if (!mapNode.current || mapRef.current) return;
    const launch = () => {
      const L = (window as any).L;
      if (!L || !mapNode.current || mapRef.current) return;
      const map = L.map(mapNode.current, { zoomControl: false, maxBoundsViscosity: .65 }).fitBounds([[48.89, 1.60], [49.25, 2.60]], { padding: [8, 8] });
      map.createPane("departmentMaskPane"); map.getPane("departmentMaskPane").style.zIndex="450";
      L.control.zoom({ position: "bottomright" }).addTo(map);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { className: "urban-base-tiles", maxZoom: 20, opacity: .38, attribution: "© OpenStreetMap contributors" }).addTo(map);
      parcelTilesRef.current = L.tileLayer("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=CADASTRALPARCELS.PARCELLAIRE_EXPRESS&STYLE=PCI%20vecteur&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/png", {
        className: "parcel-tiles", minZoom: 11, maxZoom: 19, opacity: .82, attribution: "© IGN · DGFiP",
      }).addTo(map);
      buildingTilesRef.current = L.tileLayer("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=BUILDINGS.BUILDINGS&STYLE=normal&TILEMATRIXSET=PM_6_18&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/png", {
        className: "building-tiles", minZoom: 11, maxZoom: 18, opacity: .95, attribution: "© IGN · BD TOPO",
      }).addTo(map);
      pluOverviewLayerRef.current=L.tileLayer.wms("https://data.geopf.fr/wms-v/ows",{layers:"document",format:"image/png",transparent:true,version:"1.3.0",opacity:.72,attribution:"© Géoportail de l’urbanisme"});
      supOverviewLayerRef.current=L.tileLayer.wms("https://data.geopf.fr/wms-v/ows",{layers:"sup",format:"image/png",transparent:true,version:"1.3.0",opacity:.48,attribution:"© Géoportail de l’urbanisme"});
      pluOverviewLayerRef.current.on("loading",()=>setLayerLoading((current)=>({...current,plu:true})));pluOverviewLayerRef.current.on("load",()=>setLayerLoading((current)=>({...current,plu:false})));
      supOverviewLayerRef.current.on("loading",()=>setLayerLoading((current)=>({...current,servitudes:true})));supOverviewLayerRef.current.on("load",()=>setLayerLoading((current)=>({...current,servitudes:false})));
      const refreshGpuLayers = async () => {
        const wantsZones=layersStateRef.current.plu, wantsSup=layersStateRef.current.servitudes;
        if (!wantsZones && pluTilesRef.current) { map.removeLayer(pluTilesRef.current); pluTilesRef.current=null; }
        if (!wantsSup && supTilesRef.current) { map.removeLayer(supTilesRef.current); supTilesRef.current=null; }
        if(!wantsZones&&pluOverviewLayerRef.current&&map.hasLayer(pluOverviewLayerRef.current))map.removeLayer(pluOverviewLayerRef.current);
        if(!wantsSup&&supOverviewLayerRef.current&&map.hasLayer(supOverviewLayerRef.current))map.removeLayer(supOverviewLayerRef.current);
        if (!wantsZones && !wantsSup) return;
        if(map.getZoom()<11){
          if(wantsZones&&!map.hasLayer(pluOverviewLayerRef.current))pluOverviewLayerRef.current.addTo(map);
          if(wantsSup&&!map.hasLayer(supOverviewLayerRef.current))supOverviewLayerRef.current.addTo(map);
          setLayerFeedback(wantsZones?"Vue synthétique du PLU. Les géométries précises et infobulles apparaissent au niveau 11.":"Vue synthétique des servitudes. Les géométries précises et infobulles apparaissent au niveau 11.");return;
        }
        if(wantsZones&&pluOverviewLayerRef.current&&map.hasLayer(pluOverviewLayerRef.current))map.removeLayer(pluOverviewLayerRef.current);
        if(wantsSup&&supOverviewLayerRef.current&&map.hasLayer(supOverviewLayerRef.current))map.removeLayer(supOverviewLayerRef.current);
        setLayerLoading((current)=>({...current,plu:wantsZones,servitudes:wantsSup}));
        const bounds=map.getBounds();
        const geometry=encodeURIComponent(JSON.stringify({type:"Polygon",coordinates:[[[bounds.getWest(),bounds.getSouth()],[bounds.getEast(),bounds.getSouth()],[bounds.getEast(),bounds.getNorth()],[bounds.getWest(),bounds.getNorth()],[bounds.getWest(),bounds.getSouth()]]]}));
        gpuRequestRef.current?.abort(); const controller=new AbortController(); gpuRequestRef.current=controller;
        try {
          const [zoneResponse,supSurfaceResponse,supLineResponse,supPointResponse]=await Promise.all([
            wantsZones?fetch(`https://apicarto.ign.fr/api/gpu/zone-urba?geom=${geometry}`,{signal:controller.signal}):Promise.resolve(null),
            wantsSup?fetch(`https://apicarto.ign.fr/api/gpu/assiette-sup-s?geom=${geometry}`,{signal:controller.signal}):Promise.resolve(null),
            wantsSup?fetch(`https://apicarto.ign.fr/api/gpu/assiette-sup-l?geom=${geometry}`,{signal:controller.signal}):Promise.resolve(null),
            wantsSup?fetch(`https://apicarto.ign.fr/api/gpu/assiette-sup-p?geom=${geometry}`,{signal:controller.signal}):Promise.resolve(null),
          ]);
          const zoneData:FeatureCollection=zoneResponse?.ok?await zoneResponse.json():emptyCollection;
          const supCollections=await Promise.all([supSurfaceResponse,supLineResponse,supPointResponse].map(async(response)=>response?.ok?await response.json():emptyCollection));
          const supData:FeatureCollection={type:"FeatureCollection",features:supCollections.flatMap((collection:any)=>collection.features||[])};
          const previousZones=pluTilesRef.current,previousSup=supTilesRef.current;
          const detailedTooltips=map.getZoom()>=13;
          if(wantsZones){ const nextZones=L.geoJSON(zoneData,{style:(feature:any)=>({color:zoneColor(feature),weight:1.5,fillColor:zoneColor(feature),fillOpacity:.26}),onEachFeature:(feature:any,layer:any)=>{if(!detailedTooltips)return;layer.bindTooltip(`<div class="simple-map-tooltip"><b>Zone ${escapeHtml(firstValue(feature.properties,["libelle","typezone","libelle_zone"],"GPU"))}</b><span>${escapeHtml(firstValue(feature.properties,["partition","nomfic"],"Document d’urbanisme"))}</span></div>`,{sticky:true,className:"urban-map-tooltip"});}}).addTo(map);if(previousZones&&map.hasLayer(previousZones))map.removeLayer(previousZones);pluTilesRef.current=nextZones;if(pluOverviewLayerRef.current&&map.hasLayer(pluOverviewLayerRef.current))map.removeLayer(pluOverviewLayerRef.current); }
          if(wantsSup){ const nextSup=L.geoJSON(supData,{style:(feature:any)=>({color:supColor(feature),weight:2.5,fillColor:supColor(feature),fillOpacity:.10,dashArray:feature.geometry?.type?.includes("Polygon")?"7 5":undefined}),pointToLayer:(feature:any,latlng:any)=>L.circleMarker(latlng,{radius:6,color:supColor(feature),weight:2,fillColor:supColor(feature),fillOpacity:.65}),onEachFeature:(feature:any,layer:any)=>{if(!detailedTooltips)return;const p=feature.properties||{},code=supCode(feature);layer.bindTooltip(`<div class="sup-tooltip"><b>${escapeHtml(code)} · ${escapeHtml(supTitle(feature))}</b><span>${escapeHtml(supFamily(code))}</span><small>${escapeHtml(firstValue(p,["typeass"],"Assiette de servitude"))}${p.srcgeoass?` · Source géométrique : ${escapeHtml(p.srcgeoass)}`:""}</small><small>Identifiant : ${escapeHtml(firstValue(p,["idass"],"non renseigné"))}</small></div>`,{sticky:true,className:"sup-map-tooltip"});}}).addTo(map);if(previousSup&&map.hasLayer(previousSup))map.removeLayer(previousSup);supTilesRef.current=nextSup;if(supOverviewLayerRef.current&&map.hasLayer(supOverviewLayerRef.current))map.removeLayer(supOverviewLayerRef.current); }
          parcelTilesRef.current?.bringToFront(); buildingTilesRef.current?.bringToFront();
          const parts=[]; if(wantsZones)parts.push(`${zoneData.features.length} zone${zoneData.features.length>1?"s":""}`); if(wantsSup)parts.push(`${supData.features.length} servitude${supData.features.length>1?"s":""}`); setLayerFeedback(`${parts.join(" · ")} dans cette vue.${detailedTooltips?" Survolez une géométrie puis cliquez sur une parcelle pour le détail.":" Zoomez au niveau 13 pour afficher les infobulles au survol."}`);
        } catch(error:any){ if(error?.name!=="AbortError")setLayerFeedback("Le Géoportail de l’urbanisme ne répond pas momentanément."); }
        finally { if(gpuRequestRef.current===controller)setLayerLoading((current)=>({...current,plu:false,servitudes:false})); }
      };
      const refreshBuildings = async () => {
        if(!layersStateRef.current.buildings){if(buildingVectorRef.current&&map.hasLayer(buildingVectorRef.current))map.removeLayer(buildingVectorRef.current);buildingRequestRef.current?.abort();setLayerLoading((current)=>({...current,buildings:false}));return;}
        if(map.getZoom()<13)return;
        setLayerLoading((current)=>({...current,buildings:true}));const bounds=map.getBounds(),bbox=[bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth(),"EPSG:4326"].join(",");buildingRequestRef.current?.abort();const controller=new AbortController();buildingRequestRef.current=controller;
        try{const base=`https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3%3Abatiment&srsName=EPSG%3A4326&BBOX=${bbox}`;const hits=await fetch(`${base}&RESULTTYPE=hits`,{signal:controller.signal}).then((response)=>response.text());const total=numberValue(hits.match(/numberMatched="(\d+)"/)?.[1]),features:any[]=[];let offset=0;while(offset<total){const response=await fetch(`${base}&outputFormat=application%2Fjson&COUNT=5000&STARTINDEX=${offset}`,{signal:controller.signal});if(!response.ok)throw new Error("Bâtiments indisponibles");const page=await response.json(),pageFeatures=page.features||[];features.push(...pageFeatures);offset+=pageFeatures.length;setLayerFeedback(`Chargement complet des bâtiments : ${features.length.toLocaleString("fr-FR")} / ${total.toLocaleString("fr-FR")}…`);if(!pageFeatures.length)break;}if(controller.signal.aborted)return;const previous=buildingVectorRef.current;buildingVectorRef.current=L.geoJSON({type:"FeatureCollection",features},{renderer:L.canvas({padding:.5}),style:{color:"#596274",weight:.7,fillColor:"#a7adb7",fillOpacity:.58},onEachFeature:(feature:any,layer:any)=>{const p=feature.properties||{};layer.bindTooltip(`<div class="simple-map-tooltip"><b>${escapeHtml(p.usage_1||p.nature||"Bâtiment")}</b><span>${p.hauteur?`${escapeHtml(p.hauteur)} m de hauteur`:"Hauteur non renseignée"}${p.nombre_d_etages?` · ${escapeHtml(p.nombre_d_etages)} étage(s)`:""}</span><small>${escapeHtml(p.nature||"Nature non renseignée")}${p.nombre_de_logements?` · ${escapeHtml(p.nombre_de_logements)} logement(s)`:""}</small></div>`,{sticky:true,className:"urban-map-tooltip"});}}).addTo(map);if(previous&&map.hasLayer(previous))map.removeLayer(previous);setLayerFeedback(`Bâtiments complets : ${features.length.toLocaleString("fr-FR")} objets chargés avec leurs informations.`);}catch(error:any){if(error?.name!=="AbortError")setLayerFeedback("La BD TOPO ne répond pas momentanément.");}finally{if(buildingRequestRef.current===controller)setLayerLoading((current)=>({...current,buildings:false}));}
      };
      const refreshMos = async () => {
        if (!layersStateRef.current.mos) {
          if (mosLayerRef.current && map.hasLayer(mosLayerRef.current)) map.removeLayer(mosLayerRef.current);
          if (mosOverviewLayerRef.current && map.hasLayer(mosOverviewLayerRef.current)) map.removeLayer(mosOverviewLayerRef.current);
          return;
        }
        const bounds = map.getBounds();
        if (map.getZoom() < 13) {
          if (mosLayerRef.current && map.hasLayer(mosLayerRef.current)) map.removeLayer(mosLayerRef.current);
          setLayerLoading((current)=>({...current,mos:false}));
          const size=map.getSize();
          const exportUrl=`https://geoweb.iau-idf.fr/agsmap1/rest/services/OPENDATA/OpendataIAU4/MapServer/export?bbox=${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}&bboxSR=4326&imageSR=4326&size=${Math.round(size.x)},${Math.round(size.y)}&format=png32&transparent=true&layers=show:25&f=image`;
          if(mosOverviewLayerRef.current){mosOverviewLayerRef.current.setUrl(exportUrl);mosOverviewLayerRef.current.setBounds(bounds);if(!map.hasLayer(mosOverviewLayerRef.current))mosOverviewLayerRef.current.addTo(map);}
          else{mosOverviewLayerRef.current=L.imageOverlay(exportUrl,bounds,{opacity:.6,attribution:"© IAU Île-de-France"}).addTo(map);}
          setLayerFeedback("Vue départementale du MOS 2025 sur tout le Val-d’Oise. Le détail par surface et les infobulles apparaissent au niveau 13.");
          return;
        }
        if (mosOverviewLayerRef.current && map.hasLayer(mosOverviewLayerRef.current)) map.removeLayer(mosOverviewLayerRef.current);
        setLayerLoading((current)=>({...current,mos:true}));
        mosRequestRef.current?.abort();
        const controller = new AbortController(); mosRequestRef.current = controller;
        const envelope = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");
        try {
          const countResponse=await fetch(`https://geoweb.iau-idf.fr/agsmap1/rest/services/OPENDATA/OpendataIAU4/MapServer/25/query?f=json&geometry=${envelope}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&returnCountOnly=true`,{signal:controller.signal});
          const total=countResponse.ok?numberValue((await countResponse.json()).count):0,features:any[]=[];let offset=0;
          while(offset<total){const response=await fetch(`https://geoweb.iau-idf.fr/agsmap1/rest/services/OPENDATA/OpendataIAU4/MapServer/25/query?f=geojson&geometry=${envelope}&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326&spatialRel=esriSpatialRelIntersects&outFields=mos2025,mos2021,insee&returnGeometry=true&resultRecordCount=1000&resultOffset=${offset}&orderByFields=objectid`,{signal:controller.signal});if(!response.ok)throw new Error("MOS page indisponible");const page=await response.json(),pageFeatures=page.features||[];features.push(...pageFeatures);offset+=pageFeatures.length;setLayerFeedback(`Chargement complet du MOS : ${features.length.toLocaleString("fr-FR")} / ${total.toLocaleString("fr-FR")} surfaces…`);if(!pageFeatures.length)break;}
          if(controller.signal.aborted)return;const data={type:"FeatureCollection",features};
          const previousMosLayer=mosLayerRef.current;
          mosLayerRef.current = L.geoJSON(data, { renderer:L.canvas({padding:.5}), style: (feature: any) => ({ color: mosColor(numberValue(feature?.properties?.mos2025)), weight: .8, fillColor: mosColor(numberValue(feature?.properties?.mos2025)), fillOpacity: .52 }), onEachFeature: (feature: any, layer: any) => {const p=feature.properties||{},current=numberValue(p.mos2025),previous=numberValue(p.mos2021);layer.bindTooltip(`<div class="mos-tooltip"><b>${escapeHtml(mosLabels[current]||"Occupation du sol")}</b><span>MOS 2025 · poste ${current||"non renseigné"}</span><small>${previous===current?"Occupation stable depuis 2021":`En 2021 : ${escapeHtml(mosLabels[previous]||`poste ${previous}`)}`}</small>${p.insee?`<small>Commune INSEE : ${escapeHtml(p.insee)}</small>`:""}</div>`,{sticky:true,className:"mos-map-tooltip"});} }).addTo(map);
          if(previousMosLayer&&map.hasLayer(previousMosLayer))map.removeLayer(previousMosLayer);setLayerFeedback(`MOS complet : ${features.length.toLocaleString("fr-FR")} surfaces chargées dans cette vue.`);
          mosLayerRef.current.bringToBack();
          parcelTilesRef.current?.bringToFront(); buildingTilesRef.current?.bringToFront();
        } catch (error: any) { if (error?.name !== "AbortError") console.warn("MOS indisponible", error); }
        finally { if(mosRequestRef.current===controller)setLayerLoading((current)=>({...current,mos:false})); }
      };
      const refreshPublicLand = async () => {
        if (!layersStateRef.current.publicLand) {
          if (publicLandLayerRef.current && map.hasLayer(publicLandLayerRef.current)) map.removeLayer(publicLandLayerRef.current);
          publicRequestRef.current?.abort();publicDepartmentLoadingRef.current=false;setLayerLoading((current)=>({...current,publicLand:false}));
          return;
        }
        if(publicDepartmentLoadedRef.current&&publicLandLayerRef.current){if(!map.hasLayer(publicLandLayerRef.current))publicLandLayerRef.current.addTo(map);setLayerFeedback(`Foncier public complet : ${publicLandLayerRef.current.getLayers().length.toLocaleString("fr-FR")} parcelles chargées dans le Val-d’Oise.`);return;}
        if(publicDepartmentLoadingRef.current)return;
        setLayerLoading((current)=>({...current,publicLand:true}));
        try {
          if (!publicLandDataRef.current) publicLandDataRef.current = await fetch(`${basePath}/data/foncier-public-95.json`).then((response) => response.json());
          setPublicDataReady(true);
          const bounds = departmentBoundsRef.current;if(!bounds){setLayerFeedback("Préparation de l’emprise complète du Val-d’Oise…");return;}
          publicDepartmentLoadingRef.current=true;
          publicRequestRef.current?.abort();const publicController=new AbortController();publicRequestRef.current=publicController;
          const columns=Math.max(1,Math.ceil((bounds.getEast()-bounds.getWest())/.08)),rows=Math.max(1,Math.ceil((bounds.getNorth()-bounds.getSouth())/.05)),requestFeatures=new Map<string,any>(),cells:Array<[number,number,number,number]>=[];let completed=0,cursor=0;
          for(let row=0;row<rows;row++)for(let column=0;column<columns;column++)cells.push([bounds.getWest()+(bounds.getEast()-bounds.getWest())*column/columns,bounds.getWest()+(bounds.getEast()-bounds.getWest())*(column+1)/columns,bounds.getSouth()+(bounds.getNorth()-bounds.getSouth())*row/rows,bounds.getSouth()+(bounds.getNorth()-bounds.getSouth())*(row+1)/rows]);
          const worker=async()=>{while(cursor<cells.length){const [west,east,south,north]=cells[cursor++],geom=encodeURIComponent(JSON.stringify({type:"Polygon",coordinates:[[[west,south],[east,south],[east,north],[west,north],[west,south]]] }));const response=await fetch(`https://apicarto.ign.fr/api/cadastre/parcelle?geom=${geom}`,{signal:publicController.signal});if(response.ok){const data:FeatureCollection=await response.json();(data.features||[]).forEach((feature:any)=>{const id=String(feature.properties?.idu||feature.id||"");if(publicLandDataRef.current?.[id])requestFeatures.set(id,feature);});}completed++;setLayerFeedback(`Chargement complet du foncier public : ${completed} / ${cells.length} secteurs…`);}};
          await Promise.all(Array.from({length:Math.min(6,cells.length)},()=>worker()));
          if(publicController.signal.aborted)return;const publicFeatures=[...requestFeatures.values()];
          publicLandLayerRef.current=L.geoJSON({type:"FeatureCollection",features:publicFeatures},{renderer:L.canvas({padding:.5}),style:(feature:any) => { const info=publicLandDataRef.current?.[String(feature.properties?.idu || feature.id || "")],visible=publicLandFilterRef.current==="all"||info?.[0]==="1"; return { color:publicLandColor(info?.[0] || ""), weight:visible?2:0, opacity:visible?1:0, fillColor:publicLandColor(info?.[0] || ""), fillOpacity:visible?.52:0 }; }, onEachFeature:(feature:any,layer:any) => { const info=publicLandDataRef.current?.[String(feature.properties?.idu || feature.id || "")]; if(info) layer.bindTooltip(`<div class="simple-map-tooltip"><b>${escapeHtml(info[1])}</b><span>${escapeHtml(info[2] || "Propriétaire public")}</span></div>`,{sticky:true,className:"urban-map-tooltip"}); }});
          publicDepartmentLoadedRef.current=true;publicLandLayerRef.current.addTo(map);setLayerFeedback(`Foncier public complet : ${publicFeatures.length.toLocaleString("fr-FR")} parcelles chargées dans tout le Val-d’Oise.`);
          parcelTilesRef.current?.bringToFront(); buildingTilesRef.current?.bringToFront();
        } catch (error:any) { if(error?.name!=="AbortError"){console.warn("Foncier public indisponible", error);setLayerFeedback("Le référentiel du foncier public ne répond pas momentanément.");} }
        finally { publicDepartmentLoadingRef.current=false;setLayerLoading((current)=>({...current,publicLand:false})); }
      };
      const fetchPublicBuildings = async (bounds:any, signal:AbortSignal) => {
        const bbox=[bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth(),"EPSG:4326"].join(",");
        const response=await fetch(`https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3%3Abatiment&srsName=EPSG%3A4326&BBOX=${bbox}&outputFormat=application%2Fjson&COUNT=2000`,{signal});
        if(!response.ok)throw new Error("Bâtiments indisponibles");
        const data=await response.json();
        return (data.features||[]).filter(isPublicBuildingFeature);
      };
      const refreshDpePublic = async () => {
        if (!layersStateRef.current.dpePublic) {
          if (dpePublicLayerRef.current && map.hasLayer(dpePublicLayerRef.current)) map.removeLayer(dpePublicLayerRef.current);
          dpePublicRequestRef.current?.abort();setLayerLoading((current)=>({...current,dpePublic:false}));
          return;
        }
        if (map.getZoom() < 16) {
          if (dpePublicLayerRef.current && map.hasLayer(dpePublicLayerRef.current)) map.removeLayer(dpePublicLayerRef.current);
          setLayerFeedback("Zoomez au niveau 16 pour afficher le DPE des bâtiments publics, bâtiment par bâtiment.");
          return;
        }
        setLayerLoading((current)=>({...current,dpePublic:true}));
        dpePublicRequestRef.current?.abort();const controller=new AbortController();dpePublicRequestRef.current=controller;
        try {
          const buildings=(await fetchPublicBuildings(map.getBounds(),controller.signal)).slice(0,60);
          setLayerFeedback(`Recherche du DPE pour ${buildings.length} bâtiment${buildings.length>1?"s":""} public${buildings.length>1?"s":""} dans cette vue…`);
          const results:any[]=[];let cursor=0;
          const worker=async()=>{while(cursor<buildings.length){const feature=buildings[cursor++];const[lon,lat]=geometryCenter(feature.geometry);let dpeClasse="";try{const parcelResponse=await fetch(`https://apicarto.ign.fr/api/cadastre/parcelle?geom=${pointGeometry(lon,lat)}`,{signal:controller.signal});const parcelData:FeatureCollection=parcelResponse.ok?await parcelResponse.json():emptyCollection;const parcelId=firstValue(parcelData.features?.[0]?.properties,["idu"],"");if(parcelId){const bdnbResponse=await fetch(`https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet/parcelle?parcelle_id=eq.${encodeURIComponent(parcelId)}`,{signal:controller.signal});const bdnbData=bdnbResponse.ok?await bdnbResponse.json():[];const entry=Array.isArray(bdnbData)?bdnbData[0]:null;dpeClasse=entry?.classe_bilan_dpe||entry?.classe_conso_energie_arrete_2012||"";}}catch(error:any){if(error?.name==="AbortError")return;}results.push({...feature,properties:{...feature.properties,dpe_classe:dpeClasse||"Non renseigné"}});}};
          await Promise.all(Array.from({length:Math.min(5,buildings.length)},()=>worker()));
          if(controller.signal.aborted)return;
          const previous=dpePublicLayerRef.current;
          dpePublicLayerRef.current=L.geoJSON({type:"FeatureCollection",features:results},{style:(feature:any)=>({color:dpeColor(feature.properties?.dpe_classe),weight:2,fillColor:dpeColor(feature.properties?.dpe_classe),fillOpacity:.6}),onEachFeature:(feature:any,layer:any)=>{const p=feature.properties||{};layer.bindTooltip(`<div class="simple-map-tooltip"><b>${escapeHtml(p.nature||p.usage_1||"Bâtiment public")}</b><span>DPE : ${escapeHtml(p.dpe_classe||"Non renseigné")}</span></div>`,{sticky:true,className:"urban-map-tooltip"});}}).addTo(map);
          if(previous&&map.hasLayer(previous))map.removeLayer(previous);
          setLayerFeedback(`DPE des bâtiments publics : ${results.length} bâtiment${results.length>1?"s":""} affiché${results.length>1?"s":""} dans cette vue.`);
        } catch(error:any){ if(error?.name!=="AbortError")setLayerFeedback("Le DPE des bâtiments publics n’est pas disponible pour le moment."); }
        finally { if(dpePublicRequestRef.current===controller)setLayerLoading((current)=>({...current,dpePublic:false})); }
      };
      const refreshPublicRisks = async () => {
        if (!layersStateRef.current.publicRisks) {
          if (publicRisksLayerRef.current && map.hasLayer(publicRisksLayerRef.current)) map.removeLayer(publicRisksLayerRef.current);
          publicRisksRequestRef.current?.abort();setLayerLoading((current)=>({...current,publicRisks:false}));
          return;
        }
        if (map.getZoom() < 16) {
          if (publicRisksLayerRef.current && map.hasLayer(publicRisksLayerRef.current)) map.removeLayer(publicRisksLayerRef.current);
          setLayerFeedback("Zoomez au niveau 16 pour afficher les risques des bâtiments publics, bâtiment par bâtiment.");
          return;
        }
        setLayerLoading((current)=>({...current,publicRisks:true}));
        publicRisksRequestRef.current?.abort();const controller=new AbortController();publicRisksRequestRef.current=controller;
        try {
          const buildings=(await fetchPublicBuildings(map.getBounds(),controller.signal)).slice(0,80);
          setLayerFeedback(`Recherche des risques Géorisques pour ${buildings.length} bâtiment${buildings.length>1?"s":""} public${buildings.length>1?"s":""} dans cette vue…`);
          const results:any[]=[];let cursor=0;
          const worker=async()=>{while(cursor<buildings.length){const feature=buildings[cursor++];const[lon,lat]=geometryCenter(feature.geometry);let riskCount=0,riskNames="";try{const response=await fetch(`https://georisques.gouv.fr/api/v1/gaspar/risques?latlon=${lon},${lat}`,{signal:controller.signal});const data=response.ok?await response.json():{data:[]};const riskDetails=(data.data||[]).flatMap((entry:any)=>entry.risques_detail||[]);riskCount=riskDetails.length;riskNames=uniqueValues(riskDetails.map((risk:any)=>risk.libelle_risque_long||risk.libelle_risque_jo||risk.risque)).join(", ");}catch(error:any){if(error?.name==="AbortError")return;}results.push({...feature,properties:{...feature.properties,risk_count:riskCount,risk_names:riskNames}});}};
          await Promise.all(Array.from({length:Math.min(6,buildings.length)},()=>worker()));
          if(controller.signal.aborted)return;
          const previous=publicRisksLayerRef.current;
          publicRisksLayerRef.current=L.geoJSON({type:"FeatureCollection",features:results},{style:(feature:any)=>{const color=publicRiskColor(numberValue(feature.properties?.risk_count));return{color,weight:2,fillColor:color,fillOpacity:.55};},onEachFeature:(feature:any,layer:any)=>{const p=feature.properties||{};layer.bindTooltip(`<div class="simple-map-tooltip"><b>${escapeHtml(p.nature||p.usage_1||"Bâtiment public")}</b><span>${numberValue(p.risk_count)} risque${numberValue(p.risk_count)>1?"s":""} recensé${numberValue(p.risk_count)>1?"s":""}</span>${p.risk_names?`<small>${escapeHtml(p.risk_names)}</small>`:""}</div>`,{sticky:true,className:"urban-map-tooltip"});}}).addTo(map);
          if(previous&&map.hasLayer(previous))map.removeLayer(previous);
          setLayerFeedback(`Risques des bâtiments publics : ${results.length} bâtiment${results.length>1?"s":""} analysé${results.length>1?"s":""} dans cette vue.`);
        } catch(error:any){ if(error?.name!=="AbortError")setLayerFeedback("Géorisques ne répond pas pour les bâtiments publics."); }
        finally { if(publicRisksRequestRef.current===controller)setLayerLoading((current)=>({...current,publicRisks:false})); }
      };
      const adaptLayerReadability=()=>{const zoom=map.getZoom();parcelTilesRef.current?.setOpacity(zoom>=15?.92:zoom>=13?.68:.48);buildingTilesRef.current?.setOpacity(zoom>=16?.9:zoom>=14?.62:.38);if(mosLayerRef.current?.setStyle)mosLayerRef.current.setStyle((feature:any)=>({color:mosColor(numberValue(feature?.properties?.mos2025)),weight:zoom>=14?.8:.5,fillColor:mosColor(numberValue(feature?.properties?.mos2025)),fillOpacity:zoom>=14?.52:.34}));if(pluTilesRef.current?.setStyle)pluTilesRef.current.setStyle((feature:any)=>({color:zoneColor(feature),weight:zoom>=14?1.5:1,fillColor:zoneColor(feature),fillOpacity:zoom>=14?.26:.18}));if(supTilesRef.current?.setStyle)supTilesRef.current.setStyle((feature:any)=>({color:supColor(feature),weight:zoom>=14?2.5:1.7,fillColor:supColor(feature),fillOpacity:zoom>=14?.10:.055,dashArray:feature.geometry?.type?.includes("Polygon")?"7 5":undefined}));};
      map.on("zoomend", () => { setMapZoom(map.getZoom()); adaptLayerReadability(); refreshBuildings(); refreshMos(); refreshPublicLand(); refreshGpuLayers(); refreshDpePublic(); refreshPublicRisks(); });
      map.on("moveend", () => { refreshBuildings(); refreshMos(); refreshPublicLand(); refreshGpuLayers(); refreshDpePublic(); refreshPublicRisks(); });
      fetch("https://geo.api.gouv.fr/departements/95/communes?fields=nom,code,contour&format=geojson&geometry=contour")
        .then((response) => response.json())
        .then((communes) => {
          communesDataRef.current=communes;
          setCommunes([...(communes.features || [])].sort((a:any,b:any) => String(a.properties?.nom || "").localeCompare(String(b.properties?.nom || ""), "fr")));
          const territory = L.geoJSON(communes, { style: { color: "#64748b", weight: .7, fillColor: "#000091", fillOpacity: .025 }, interactive: false }).addTo(map);
          const bounds = territory.getBounds();
          if (bounds.isValid()) { departmentBoundsRef.current=bounds;map.fitBounds(bounds, { padding: [10, 10] }); map.setMaxBounds(bounds.pad(.28)); }
          if(layersStateRef.current.publicLand)map.fire("moveend");
        }).catch(() => undefined);
      fetch("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ADMINEXPRESS-COG-CARTO-PE.LATEST%3Adepartement&outputFormat=application%2Fjson&CQL_FILTER=code_insee%3D%2795%27&srsName=EPSG%3A4326").then((response)=>response.json()).then((data)=>{const geometry=data.features?.[0]?.geometry;if(!geometry)return;const polygons=geometry.type==="MultiPolygon"?geometry.coordinates:[geometry.coordinates];const holes=polygons.map((polygon:any)=>polygon[0].map(([lon,lat]:number[])=>[lat,lon]));const world=[[-85,-180],[-85,180],[85,180],[85,-180]];departmentMaskRef.current=L.polygon([world,...holes],{pane:"departmentMaskPane",stroke:false,fillColor:"#f4f6fb",fillOpacity:.82,fillRule:"evenodd",interactive:false}).addTo(map);L.geoJSON(data,{pane:"departmentMaskPane",style:{color:"#000091",weight:3,fill:false},interactive:false}).addTo(map);}).catch(()=>undefined);
      map.on("click", (event: any) => inspectMapPoint(event.latlng.lng, event.latlng.lat));
      mapRef.current = map;
      refreshMos(); refreshGpuLayers();
    };
    if ((window as any).L) launch();
    else {
      if (!document.getElementById("leaflet-css")) {
        const link = document.createElement("link"); link.id = "leaflet-css"; link.rel = "stylesheet"; link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"; document.head.appendChild(link);
      }
      const existing = document.querySelector<HTMLScriptElement>('script[data-leaflet="true"]');
      if (existing) existing.addEventListener("load", launch, { once: true });
      else { const script = document.createElement("script"); script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"; script.dataset.leaflet = "true"; script.onload = launch; document.body.appendChild(script); }
    }
  }, []);

  useEffect(() => {
    const map = mapRef.current; if (!map) return;
    const toggleMapLayer = (layer: any, visible: boolean) => { if (!layer) return; if (visible && !map.hasLayer(layer)) layer.addTo(map); if (!visible && map.hasLayer(layer)) map.removeLayer(layer); };
    toggleMapLayer(parcelTilesRef.current, layers.parcels);
    toggleMapLayer(buildingTilesRef.current, layers.buildings);
    if (!layers.mos && mosLayerRef.current && map.hasLayer(mosLayerRef.current)) map.removeLayer(mosLayerRef.current);
    if (!layers.mos && mosOverviewLayerRef.current && map.hasLayer(mosOverviewLayerRef.current)) map.removeLayer(mosOverviewLayerRef.current);
    if (!layers.publicLand && publicLandLayerRef.current && map.hasLayer(publicLandLayerRef.current)) map.removeLayer(publicLandLayerRef.current);
    if (!layers.plu && pluTilesRef.current) { map.removeLayer(pluTilesRef.current); pluTilesRef.current=null; }
    if (!layers.servitudes && supTilesRef.current) { map.removeLayer(supTilesRef.current); supTilesRef.current=null; }
    if (!layers.plu && pluOverviewLayerRef.current && map.hasLayer(pluOverviewLayerRef.current)) map.removeLayer(pluOverviewLayerRef.current);
    if (!layers.servitudes && supOverviewLayerRef.current && map.hasLayer(supOverviewLayerRef.current)) map.removeLayer(supOverviewLayerRef.current);
    if (!layers.dpePublic && dpePublicLayerRef.current && map.hasLayer(dpePublicLayerRef.current)) map.removeLayer(dpePublicLayerRef.current);
    if (!layers.publicRisks && publicRisksLayerRef.current && map.hasLayer(publicRisksLayerRef.current)) map.removeLayer(publicRisksLayerRef.current);
    if (layers.buildings || layers.mos || layers.publicLand || layers.plu || layers.servitudes || layers.dpePublic || layers.publicRisks) map.fire("moveend");
    if (result && selectionPointRef.current) {
      const [lon, lat] = selectionPointRef.current;
      drawResults(lon, lat, result.parcel ? { type: "FeatureCollection", features: [result.parcel] } : emptyCollection, { type: "FeatureCollection", features: result.zones }, { type: "FeatureCollection", features: result.servitudes });
    }
  }, [layers]);

  useEffect(() => {
    publicLandFilterRef.current = publicLandFilter;
    const group = publicLandLayerRef.current;
    if (!group?.eachLayer) return;
    let visibleCount = 0;
    group.eachLayer((layer:any) => {
      const feature = layer.feature, id=String(feature?.properties?.idu||feature?.id||""), info=publicLandDataRef.current?.[id];
      const visible = publicLandFilter === "all" || info?.[0] === "1";
      layer.options.interactive = visible;
      layer.setStyle({color:publicLandColor(info?.[0]||""),weight:visible?2:0,opacity:visible?1:0,fillColor:publicLandColor(info?.[0]||""),fillOpacity:visible?.52:0});
      if (visible) visibleCount++;
    });
    setLayerFeedback(publicLandFilter==="state"?`Foncier de l’État : ${visibleCount.toLocaleString("fr-FR")} parcelles affichées.`:`Foncier public : ${visibleCount.toLocaleString("fr-FR")} parcelles affichées.`);
  }, [publicLandFilter]);

  async function inspectMapPoint(lon: number, lat: number) {
    setLoading(true);
    setMessage("Recherche de l’adresse la plus proche…");
    let address = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    let addressMeta: Partial<AddressResult> = {};
    try {
      const response = await fetch(`https://api-adresse.data.gouv.fr/reverse/?lon=${lon}&lat=${lat}&limit=1`);
      const data = response.ok ? await response.json() : { features: [] };
      const feature = data.features?.[0];
      if (feature) {
        const properties = feature.properties;
        address = properties.label;
        addressMeta = { label: properties.label, city: properties.city, citycode: properties.citycode, postcode: properties.postcode, coordinates: feature.geometry.coordinates };
        setQuery(properties.label);
        setActiveCommune(properties.city || ""); setCommuneCode(properties.citycode || "");
      }
    } catch { /* Les coordonnées restent disponibles si la BAN ne répond pas. */ }
    await inspectPoint(lon, lat, address, addressMeta, "Adresse la plus proche");
  }

  async function inspectPoint(lon: number, lat: number, address: string, addressMeta?: Partial<AddressResult>, addressLabel = "Adresse recherchée") {
    setLoading(true); setResult(null); setMessage("Interrogation du cadastre, du GPU et de Géorisques…");
    const geom = pointGeometry(lon, lat);
    try {
      const [parcelResponse, zonesResponse, supSurfaceResponse, supLineResponse, supPointResponse, risksResponse] = await Promise.all([
        fetch(`https://apicarto.ign.fr/api/cadastre/parcelle?geom=${geom}`),
        fetch(`https://apicarto.ign.fr/api/gpu/zone-urba?geom=${geom}`),
        fetch(`https://apicarto.ign.fr/api/gpu/assiette-sup-s?geom=${geom}`),
        fetch(`https://apicarto.ign.fr/api/gpu/assiette-sup-l?geom=${geom}`),
        fetch(`https://apicarto.ign.fr/api/gpu/assiette-sup-p?geom=${geom}`),
        fetch(`https://georisques.gouv.fr/api/v1/gaspar/risques?latlon=${lon},${lat}`),
      ]);
      let parcelData: FeatureCollection = parcelResponse.ok ? await parcelResponse.json() : emptyCollection;
      if (!parcelData.features?.length) {
        const nearbyResponse = await fetch(`https://apicarto.ign.fr/api/cadastre/parcelle?geom=${nearbyGeometry(lon, lat)}`);
        parcelData = nearbyResponse.ok ? closestParcel(await nearbyResponse.json(), lon, lat) : emptyCollection;
      }
      const zoneData: FeatureCollection = zonesResponse.ok ? await zonesResponse.json() : emptyCollection;
      const supCollections=await Promise.all([supSurfaceResponse,supLineResponse,supPointResponse].map(async(response)=>response.ok?await response.json():emptyCollection));
      const supData:FeatureCollection={type:"FeatureCollection",features:supCollections.flatMap((collection:any)=>collection.features||[])};
      const risksData = risksResponse.ok ? await risksResponse.json() : { data: [] };
      drawResults(lon, lat, parcelData, zoneData, supData);
      const parcel = parcelData.features?.[0];
      const props = parcel?.properties || {};
      const parcelId = firstValue(props, ["idu"], "");
      const [parcelLon, parcelLat] = geometryCenter(parcel?.geometry);
      const [buildingsResponse, mosResponse] = await Promise.all([
        parcelId ? fetch(`https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet/parcelle?parcelle_id=eq.${encodeURIComponent(parcelId)}`) : Promise.resolve(null),
        fetch(`https://geoweb.iau-idf.fr/agsmap1/rest/services/OPENDATA/OpendataIAU4/MapServer/25/query?f=geojson&geometry=${parcelLon || lon},${parcelLat || lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false`),
      ]);
      const buildings = buildingsResponse?.ok ? await buildingsResponse.json() : [];
      if (!publicLandDataRef.current) publicLandDataRef.current = await fetch(`${basePath}/data/foncier-public-95.json`).then((response) => response.json()).catch(() => ({}));
      setPublicDataReady(true);
      const publicLand = publicLandDataRef.current?.[parcelId];
      const mosData = mosResponse.ok ? await mosResponse.json() : emptyCollection;
      const mosProps = mosData.features?.[0]?.properties || {};
      const riskDetails = (risksData.data || []).flatMap((entry: any) => entry.risques_detail || []);
      setResult({ address, addressLabel, commune: addressMeta?.city || firstValue(props, ["nom_com", "nom_commune"]), codeInsee: addressMeta?.citycode || firstValue(props, ["code_insee", "code_dep"], "—"), parcel, zones: zoneData.features || [], servitudes: supData.features || [], risks: riskDetails, buildings: Array.isArray(buildings) ? buildings : [], publicLand, mos: { mos2021: numberValue(mosProps.mos2021), mos2025: numberValue(mosProps.mos2025), surface: numberValue(mosProps["st_area(shape)"]) } }); setDetailsOpen(true);
      setMessage(parcel ? "Informations disponibles pour le point sélectionné." : "Aucune parcelle trouvée à cet emplacement.");
    } catch {
      setMessage("Une source publique n’a pas répondu. Vous pouvez réessayer dans quelques instants.");
    } finally { setLoading(false); }
  }

  function drawResults(lon: number, lat: number, parcels: FeatureCollection, zones: FeatureCollection, servitudes: FeatureCollection) {
    selectionPointRef.current = [lon, lat];
    const L = (window as any).L; const map = mapRef.current; if (!L || !map) return;
    layersRef.current.forEach((layer) => map.removeLayer(layer)); layersRef.current = [];
    if (markerRef.current) map.removeLayer(markerRef.current);
    const selectedOwners = uniqueValues(result?.buildings.map((building) => building.l_denomination_proprietaire) || []);
    const selectedIsPublic = /État|public/.test(classifyOwners(selectedOwners));
    const parcelStyle = layersStateRef.current.publicLand ? { color: selectedIsPublic ? "#18753c" : "#6b7280", weight: 4, fillColor: selectedIsPublic ? "#5ecf8b" : "#d1d5db", fillOpacity: .48 } : { color: "#000091", weight: 4, fillColor: "#4fd1ff", fillOpacity: .32 };
    const configs = [
      [layersStateRef.current.servitudes ? servitudes : emptyCollection, { color: "#6f4c9b", weight: 2, fillColor: "#6f4c9b", fillOpacity: .12, dashArray: "6 4" }],
      [layersStateRef.current.plu ? zones : emptyCollection, { color: "#18753c", weight: 2, fillColor: "#18753c", fillOpacity: .10 }],
      [parcels, parcelStyle],
    ] as const;
    configs.forEach(([data, style]) => { if (data.features.length) { const layer = L.geoJSON(data, { style }).addTo(map); layersRef.current.push(layer); } });
    markerRef.current = L.circleMarker([lat, lon], { radius: 6, color: "#e1000f", fillColor: "#fff", fillOpacity: 1, weight: 3 }).addTo(map);
    map.setMinZoom(10);
    const parcelLayer = layersRef.current.at(-1); if (parcelLayer?.getBounds?.().isValid()) map.fitBounds(parcelLayer.getBounds(), { padding: [40, 40], maxZoom: 19 }); else map.setView([lat, lon], 17);
    setLayerFeedback(`Parcelle sélectionnée · niveau ${Math.max(13, map.getZoom())}. Les couches activées restent affichées.`);
  }

  function resetSearch() {
    const map = mapRef.current;
    if (map) {
      layersRef.current.forEach((layer) => map.removeLayer(layer));
      layersRef.current = [];
      if (markerRef.current) map.removeLayer(markerRef.current);
    markerRef.current = null;
      selectionPointRef.current = null;
      if (communeFocusLayerRef.current) map.removeLayer(communeFocusLayerRef.current);
      communeFocusLayerRef.current = null;
      map.setMinZoom(9); const bounds=departmentBoundsRef.current; if(bounds?.isValid()) map.fitBounds(bounds,{padding:[10,10]}); else map.fitBounds([[48.89,1.60],[49.25,2.60]],{padding:[8,8]});
    }
    setQuery("");
    setResult(null);
    setDetailsOpen(false);
    setCommuneCode("");
    setCommuneQuery("");
    setActiveCommune("");
    setLoading(false);
    setMessage("Recherchez une adresse ou cliquez sur la carte.");
    setLayerFeedback("Vue départementale : choisissez une adresse ou une commune.");
  }

  function closeParcelDetails() {
    const map = mapRef.current;
    if (map) {
      layersRef.current.forEach((layer) => map.removeLayer(layer));
      layersRef.current = [];
      if (markerRef.current) map.removeLayer(markerRef.current);
    }
    markerRef.current = null;
    selectionPointRef.current = null;
    setResult(null);
    setDetailsOpen(false);
    setMessage("Sélection fermée. Cliquez sur une autre parcelle ou lancez une nouvelle recherche.");
    setLayerFeedback("Aucune parcelle sélectionnée. Les couches actives restent affichées.");
  }

  function exploreCommune(code = communeCode) {
    const feature = communes.find((item) => String(item.properties?.code) === code);
    const map = mapRef.current; const L = (window as any).L;
    if (!feature || !map || !L) return;
    if (communeFocusLayerRef.current) map.removeLayer(communeFocusLayerRef.current);
    communeFocusLayerRef.current = L.geoJSON(feature, { style: { color: "#000091", weight: 3, fillColor: "#000091", fillOpacity: .04 }, interactive: false }).addTo(map);
    const bounds = communeFocusLayerRef.current.getBounds();
    if (bounds.isValid()) { map.setMinZoom(10); map.fitBounds(bounds, { padding: [45,45], maxZoom: 15 }); }
    setActiveCommune(feature.properties?.nom || "Commune choisie");
    setCommuneQuery(feature.properties?.nom || ""); setCommuneSuggestionsOpen(false);
    setResult(null); setDetailsOpen(false); setMessage("Commune cadrée : cliquez directement sur une parcelle.");
    setLayerFeedback("Vue communale active : vous pouvez prendre du recul sans perdre les couches affichées.");
  }

  function toggleLayer(key: keyof typeof layers) {
    const enable = !layers[key]; const map = mapRef.current;
    setLayers((current) => {
      const next={...current,[key]:!current[key]};
      layersStateRef.current=next;
      return next;
    });
    if (enable && map) {
      map.setMinZoom(10);
      if (map.getZoom() < 11) {
        setLayerFeedback("Passage automatique au niveau 11 : chargement de la vue départementale…");
        window.requestAnimationFrame(() => map.flyTo(map.getCenter(), 11, { duration:.65 }));
      } else {
        setLayerFeedback(`Couche ajoutée au niveau ${map.getZoom()} : votre cadrage est conservé.`);
      }
    }
  }

  async function searchAddress(event: React.FormEvent) {
    event.preventDefault(); if (!query.trim()) return;
    setLoading(true); setMessage("Recherche de l’adresse…");
    try {
      const response = await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(query)}&limit=1&autocomplete=0`);
      const data = await response.json(); const feature = data.features?.[0];
      if (!feature) { setMessage("Adresse non trouvée."); setLoading(false); return; }
      const [lon, lat] = feature.geometry.coordinates; const p = feature.properties;
      setActiveCommune(p.city || ""); setCommuneCode(p.citycode || "");
      setQuery(p.label); await inspectPoint(lon, lat, p.label, { label: p.label, city: p.city, citycode: p.citycode, postcode: p.postcode, coordinates: [lon, lat] });
    } catch { setLoading(false); setMessage("La recherche d’adresse est momentanément indisponible."); }
  }

  async function openParcelPdf() {
    if (!result) return;
    const viewer = window.open("", "_blank");
    if(viewer){viewer.document.title="Préparation de la fiche parcellaire";viewer.document.body.innerHTML='<main style="font-family:Arial,sans-serif;display:grid;place-items:center;min-height:90vh;color:#000091"><div style="text-align:center"><h1 style="font-size:24px">Préparation de la fiche parcellaire</h1><p style="color:#596274">Les données et la mise en page du PDF sont en cours de génération…</p></div></main>';}
    const { jsPDF } = await import("jspdf");
    const pdf = new jsPDF({ unit:"mm", format:"a4", orientation:"portrait" });
    const navy:[number,number,number]=[0,0,145], deep:[number,number,number]=[7,0,71], ink:[number,number,number]=[30,39,58], muted:[number,number,number]=[91,103,123];
    const logoData = await fetch(`${basePath}/prefet-val-doise-logo.png`).then((response)=>response.blob()).then((blob)=>new Promise<string>((resolve,reject)=>{ const reader=new FileReader(); reader.onload=()=>resolve(String(reader.result)); reader.onerror=reject; reader.readAsDataURL(blob); })).catch(()=>"");
    pdf.setFillColor(246,248,253); pdf.rect(0,0,210,297,"F");
    pdf.setFillColor(...navy); pdf.rect(0,0,210,5,"F");
    pdf.setFillColor(255,255,255); pdf.rect(0,5,210,39,"F");
    if (logoData) pdf.addImage(logoData,"PNG",14,10,29,21.6,undefined,"FAST");
    pdf.setDrawColor(214,221,233); pdf.line(48,11,48,37);
    pdf.setTextColor(...muted); pdf.setFont("helvetica","bold"); pdf.setFontSize(7); pdf.text("DIRECTION DÉPARTEMENTALE DES TERRITOIRES",55,17);
    pdf.setTextColor(...deep); pdf.setFontSize(17); pdf.text("Fiche d’identité parcellaire",55,27);
    pdf.setTextColor(...muted); pdf.setFont("helvetica","normal"); pdf.setFontSize(7); pdf.text("Val-d’Oise · lecture foncière et réglementaire",55,34);
    pdf.setTextColor(...navy); pdf.setFont("helvetica","bold"); pdf.setFontSize(7); pdf.text("DOCUMENT DE CONSULTATION",196,15,{align:"right"});
    pdf.setTextColor(...muted); pdf.setFont("helvetica","normal"); pdf.text(new Date().toLocaleDateString("fr-FR"),196,21,{align:"right"});

    pdf.setFillColor(0,0,145); pdf.roundedRect(14,51,182,29,4,4,"F");
    pdf.setTextColor(198,220,255); pdf.setFont("helvetica","bold"); pdf.setFontSize(7); pdf.text("PARCELLE SÉLECTIONNÉE",21,60);
    pdf.setTextColor(255,255,255); pdf.setFontSize(16); pdf.text(pdf.splitTextToSize(streetOnly(result.address),118),21,69);
    pdf.setFontSize(9); pdf.text(`${result.commune} · ${firstValue(parcelProps,["section"],"")} ${firstValue(parcelProps,["numero"],"—")}`,188,68,{align:"right"});
    pdf.setFont("helvetica","normal"); pdf.setFontSize(7); pdf.text(`${firstValue(parcelProps,["contenance"],"—")} m²`,188,74,{align:"right"});

    const metric=(x:number,value:string,label:string,color:[number,number,number])=>{ pdf.setFillColor(255,255,255); pdf.roundedRect(x,86,57.3,19,3,3,"F"); pdf.setDrawColor(196,205,219); pdf.setLineWidth(.35); pdf.roundedRect(x,86,57.3,19,3,3,"S"); pdf.setFillColor(...color); pdf.roundedRect(x+5,90,3,11,1.5,1.5,"F"); pdf.setTextColor(...deep); pdf.setFont("helvetica","bold"); pdf.setFontSize(11); pdf.text(value,x+12,94); pdf.setTextColor(...muted); pdf.setFont("helvetica","normal"); pdf.setFontSize(6.2); pdf.text(label,x+12,100); };
    metric(14,`${buildingCount}`,`bâtiment${buildingCount>1?"s":""} recensé${buildingCount>1?"s":""}`,[74,85,104]);
    metric(76.3,`${formatPdfNumber(builtFootprint)} m²`,"surface occupée par les bâtiments",[0,0,145]);
    metric(138.6,formatNumber(coverageRatio," %"),"taux d’emprise",[24,117,60]);

    const block=(x:number,y:number,w:number,h:number,title:string,index:string,accent:[number,number,number],background:[number,number,number],rows:[string,string][])=>{ pdf.setFillColor(...background); pdf.roundedRect(x,y,w,h,2.5,2.5,"F"); pdf.setDrawColor(...accent); pdf.setLineWidth(.45); pdf.roundedRect(x,y,w,h,2.5,2.5,"S"); pdf.setFillColor(...accent); pdf.roundedRect(x,y,w,5,2.5,2.5,"F"); pdf.rect(x,y+2.5,w,2.5,"F"); pdf.setTextColor(...accent); pdf.setFont("helvetica","bold"); pdf.setFontSize(6.3); pdf.text(index,x+6,y+11); pdf.setTextColor(...deep); pdf.setFontSize(10); pdf.text(title,x+15,y+11); let ry=y+18; rows.forEach(([label,value])=>{ pdf.setTextColor(...muted); pdf.setFont("helvetica","normal"); pdf.setFontSize(6); pdf.text(label,x+6,ry); pdf.setTextColor(...ink); pdf.setFont("helvetica","bold"); const lines=pdf.splitTextToSize(value,w-38); pdf.text(lines,x+31,ry); ry+=Math.max(5.3,lines.length*3.2); }); };
    const zoneLabel=result.zones.map((z)=>firstValue(z.properties,["libelle","typezone","libelle_zone"],"Zone GPU")).join(", ")||"Non retourné";
    const riskLabel=uniqueValues(result.risks.map((r)=>r.libelle_risque_long||r.libelle_risque)).join(" · ")||"Aucun risque retourné";
    const useLabel=uniqueValues(result.buildings.map((b)=>b.usage_principal_bdnb_open)).join(", ")||"Non renseigné";
    block(14,110,88,32,"Parcelle cadastrale","01",navy,[239,246,255],[["Référence",`${firstValue(parcelProps,["section"],"")} ${firstValue(parcelProps,["numero"],"—")}`],["Contenance",`${firstValue(parcelProps,["contenance"],"—")} m²`],["Commune",result.commune]]);
    block(108,110,88,38,"Bâtiments","02",[74,85,104],[241,244,249],[["Usage",useLabel],["Construction",String(oldestBuilding||"Non renseignée")],["Hauteur",maxHeight?formatNumber(maxHeight," m"):"Non renseignée"],["Logements",String(dwellingCount||"Non renseigné")]]);
    block(14,147,88,31,"Propriété foncière","03",[24,117,60],[238,248,241],[["Lecture",ownerCategory],["Référentiel",result.publicLand?"DGFiP FPMU 2025":"Donnée privée non diffusée"]]);
    block(108,153,88,27,"Occupation du sol · MOS","04",[227,179,65],[255,248,231],[["Occupation",result.mos?.mos2025?mosLabels[result.mos.mos2025]||`Poste ${result.mos.mos2025}`:"Non renseignée"],["Évolution",result.mos?.mos2021===result.mos?.mos2025?"Stable depuis 2021":"Changement depuis 2021"]]);
    block(14,185,88,30,"Règles d’urbanisme","05",[24,117,60],[240,248,243],[["Zonage PLU",zoneLabel],["Servitudes",`${result.servitudes.length} assiette(s) intersectée(s)`]]);
    block(108,185,88,30,"Risques recensés","06",[225,0,15],[255,241,240],[["Synthèse",riskLabel]]);

    pdf.setFillColor(255,255,255); pdf.roundedRect(14,228,182,25,3,3,"F"); pdf.setDrawColor(170,181,199); pdf.roundedRect(14,228,182,25,3,3,"S");
    pdf.setTextColor(...deep); pdf.setFont("helvetica","bold"); pdf.setFontSize(8); pdf.text("Sources et portée de la fiche",20,236);
    pdf.setTextColor(...muted); pdf.setFont("helvetica","normal"); pdf.setFontSize(6.3); pdf.text(pdf.splitTextToSize("DGFiP · IGN Cadastre et BD TOPO · Géoportail de l’urbanisme · BDNB · Institut Paris Region · Géorisques. Cette lecture est indicative : les documents opposables et les services officiels restent la référence.",168),20,243);
    pdf.setDrawColor(214,221,233); pdf.line(14,282,196,282); pdf.setTextColor(...muted); pdf.setFontSize(6); pdf.text("DDT du Val-d’Oise · Atlas territorial",14,288); pdf.setTextColor(...navy); pdf.setFont("helvetica","bold"); pdf.text("Géoportail de l’urbanisme · Géorisques · Cadastre",196,288,{align:"right"});
    if(result.servitudes.length){
      const annexHeader=()=>{ pdf.setFillColor(246,248,253);pdf.rect(0,0,210,297,"F");pdf.setFillColor(...navy);pdf.rect(0,0,210,5,"F");pdf.setTextColor(...deep);pdf.setFont("helvetica","bold");pdf.setFontSize(16);pdf.text("Servitudes concernant la parcelle",14,19);pdf.setTextColor(...muted);pdf.setFont("helvetica","normal");pdf.setFontSize(7);pdf.text(`${streetOnly(result.address)} · ${result.commune}`,14,26);pdf.setDrawColor(214,221,233);pdf.line(14,34,196,34);};
      pdf.addPage();annexHeader();let sy=44;
      result.servitudes.forEach((servitude,index)=>{const code=supCode(servitude),p=servitude.properties||{},title=`${code} · ${supTitle(servitude)}`,detail=`${supDescription(code)} · ${firstValue(p,["typeass"],"Emprise non renseignée")}`,meta=`Identifiant GPU : ${firstValue(p,["idass"],"non renseigné")}${p.srcgeoass?` · Source : ${p.srcgeoass}`:""}${p.fichier?` · Acte : ${p.fichier}`:""}`;const titleLines=pdf.splitTextToSize(title,160),detailLines=pdf.splitTextToSize(detail,160),metaLines=pdf.splitTextToSize(meta,160),h=Math.max(26,11+titleLines.length*4+detailLines.length*3.5+metaLines.length*3.2);if(sy+h>279){pdf.addPage();annexHeader();sy=44;}const hex=supColor(servitude).replace("#","");const rgb:[number,number,number]=[parseInt(hex.slice(0,2),16),parseInt(hex.slice(2,4),16),parseInt(hex.slice(4,6),16)];pdf.setFillColor(255,255,255);pdf.roundedRect(14,sy,182,h,3,3,"F");pdf.setFillColor(...rgb);pdf.roundedRect(14,sy,4,h,2,2,"F");pdf.setTextColor(...deep);pdf.setFont("helvetica","bold");pdf.setFontSize(9);pdf.text(titleLines,23,sy+8);let ty=sy+9+titleLines.length*4;pdf.setTextColor(...ink);pdf.setFont("helvetica","normal");pdf.setFontSize(7);pdf.text(detailLines,23,ty);ty+=detailLines.length*3.5+3;pdf.setTextColor(...muted);pdf.setFontSize(6.2);pdf.text(metaLines,23,ty);pdf.setTextColor(...rgb);pdf.setFont("helvetica","bold");pdf.text(String(index+1).padStart(2,"0"),190,sy+8,{align:"right"});sy+=h+4;});
    }
    const url = URL.createObjectURL(pdf.output("blob"));
    if (viewer) viewer.location.replace(url);
    else window.open(url, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(url), 120000);
  }

  const parcelProps = result?.parcel?.properties || {};
  const buildingCount = result?.buildings.length || 0;
  const builtFootprint = result?.buildings.reduce((sum, building) => sum + numberValue(building.surface_emprise_sol), 0) || 0;
  const parcelArea = numberValue(parcelProps.contenance);
  const coverageRatio = parcelArea ? (builtFootprint / parcelArea) * 100 : 0;
  const publicOwners = uniqueValues(result?.buildings.map((building) => building.l_denomination_proprietaire) || []);
  const ownerCategory = result?.publicLand ? `${result.publicLand[1]} — ${result.publicLand[2]}` : classifyOwners(publicOwners);
  const oldestBuilding = result?.buildings.map((building) => numberValue(building.annee_construction)).filter(Boolean).sort((a,b) => a-b)[0];
  const maxHeight = Math.max(0, ...(result?.buildings.map((building) => numberValue(building.hauteur_mean)) || []));
  const dwellingCount = result?.buildings.reduce((sum, building) => sum + numberValue(building.nb_log), 0) || 0;
  const dpeClasses = uniqueValues(result?.buildings.map((building) => building.classe_bilan_dpe || (building.classe_conso_energie_arrete_2012 !== "N" ? building.classe_conso_energie_arrete_2012 : null)) || []);
  const stateLandByCommune = useMemo(() => {
    if (!publicDataReady || !publicLandDataRef.current) return [] as {code:string;name:string;count:number}[];
    const counts:Record<string,number>={};
    Object.entries(publicLandDataRef.current).forEach(([id,info])=>{if(info[0]==="1"){const code=id.slice(0,5);counts[code]=(counts[code]||0)+1;}});
    return communes.map((feature:any)=>({code:String(feature.properties?.code||""),name:String(feature.properties?.nom||"Commune"),count:counts[String(feature.properties?.code||"")]||0})).filter((item)=>item.count>0).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,"fr"));
  }, [communes,publicDataReady]);
  const loadingLabels=Object.entries(layerLoading).filter(([,waiting])=>waiting).map(([key])=>({buildings:"bâtiments",mos:"MOS 2025",plu:"zonage PLU",servitudes:"servitudes",publicLand:"foncier public",dpePublic:"DPE bâtiments publics",publicRisks:"risques bâtiments publics"}[key]));
  return (
    <main className="urban-tool">
      <header className="urban-observatory-header">
        <img src={`${basePath}/prefet-val-doise-logo.png`} alt="Préfet du Val-d’Oise — Liberté Égalité Fraternité"/>
        <div><span>Cadastre · urbanisme · foncier · Val-d’Oise</span><h1>Urbanisme à la parcelle</h1><p><strong>Val-d’Oise</strong> · bâti · MOS · PLU · servitudes · risques</p></div>
        <div className="urban-header-actions"><div className="header-service-state"><i className={Object.values(services).every((state)=>state==="online")?"online":"checking"}/><span><strong>{Object.values(services).filter((state)=>state==="online").length}/7 sources connectées</strong><small>Données publiques actualisées</small></span></div></div>
      </header>
      <div className="urban-layout">
        <aside className="urban-panel">
          <div className="urban-panel-title"><h2>Rechercher et comprendre<br/><span>une parcelle</span></h2></div>
          <form className="urban-search" onSubmit={searchAddress}><div><input id="urban-address" aria-label="Adresse ou référence cadastrale" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Adresse dans le Val-d’Oise…" /><button disabled={loading}>{loading ? "…" : "Rechercher"}</button></div></form>
          <div className="commune-autocomplete"><label htmlFor="urban-commune">Explorer directement une commune</label><div><input id="urban-commune" value={communeQuery} placeholder="Commencez à saisir : Pontoise…" autoComplete="off" onFocus={()=>setCommuneSuggestionsOpen(true)} onChange={(event)=>{setCommuneQuery(event.target.value);setCommuneSuggestionsOpen(true);setCommuneCode("");}}/>{communeSuggestionsOpen && communeQuery.trim().length>0 && <div className="commune-suggestions">{communes.filter((item)=>String(item.properties?.nom||"").toLocaleLowerCase("fr").includes(communeQuery.toLocaleLowerCase("fr"))).slice(0,6).map((item)=><button key={item.properties?.code} type="button" onClick={()=>{setCommuneCode(item.properties.code);exploreCommune(item.properties.code);}}><strong>{item.properties?.nom}</strong><small>Val-d’Oise · {item.properties?.code}</small></button>)}</div>}</div>{activeCommune && <p><i/>Vous explorez <strong>{activeCommune}</strong><button type="button" onClick={resetSearch}>Quitter</button></p>}</div>
          <div className={`urban-message ${loading ? "loading" : ""}`}><i />{message}</div>
          {(result || query) && !loading && <button className="reset-search" type="button" onClick={resetSearch}><span aria-hidden="true">↺</span> Nouvelle recherche</button>}
          <section className="urban-layer-panel" aria-labelledby="urban-layer-title">
            <div className="urban-layer-head"><span><small>Lecture de la carte</small><strong id="urban-layer-title">Informations affichées</strong></span><b>Niveau {mapZoom}</b></div>
            <div className="urban-layer-list">
              {([
                ["parcels","Parcelles","Limites cadastrales IGN","#000091"],
                ["buildings","Bâtiments","Empreintes BD TOPO affichées en gris","#444b55"],
                ["mos","MOS 2025","Occupation du sol en couleurs","#e07a9a"],
                ["plu","Zonage PLU","Carte GPU continue + détail au clic","#18753c"],
                ["servitudes","Servitudes","Carte GPU continue + détail au clic","#6f4c9b"],
                ["publicLand","Foncier public","État, collectivités, HLM et établissements","#008941"],
                ["dpePublic","DPE - Bâtiments publics","Classe énergétique des équipements publics, niveau 16","#e07a2c"],
                ["publicRisks","Bâtiments publics - risques","Risques Géorisques par équipement public, niveau 16","#c1121f"],
              ] as const).map(([key,label,description,color]) => {const waiting=key in layerLoading&&layerLoading[key as keyof typeof layerLoading];return <button key={key} type="button" role="switch" className={`urban-layer-toggle ${waiting?"is-loading":""}`} onClick={() => toggleLayer(key)} aria-checked={layers[key]} aria-busy={waiting}><i style={{background:color}}/><span><strong>{label}{waiting&&<em className="layer-spinner" aria-hidden="true"/>}</strong><small>{waiting?"Chargement des données…":description}</small></span><b aria-hidden="true"><em/></b></button>})}
            </div>
            {layers.dpePublic && <div className="mos-mini-legend"><strong>DPE des bâtiments publics</strong><span><i style={{background:"#008941"}}/>A</span><span><i style={{background:"#3cb44a"}}/>B</span><span><i style={{background:"#a8c936"}}/>C</span><span><i style={{background:"#e3b341"}}/>D</span><span><i style={{background:"#e07a2c"}}/>E</span><span><i style={{background:"#e1541f"}}/>F</span><span><i style={{background:"#c1121f"}}/>G</span><small>Mairies, préfectures, établissements de santé, lieux de culte et équipements sportifs (BD TOPO), classe DPE issue de la BDNB.</small></div>}
            {layers.publicRisks && <div className="mos-mini-legend"><strong>Risques des bâtiments publics</strong><span><i style={{background:"#687787"}}/>Aucun risque recensé</span><span><i style={{background:"#e3b341"}}/>1 risque</span><span><i style={{background:"#e1541f"}}/>2-3 risques</span><span><i style={{background:"#c1121f"}}/>4 risques ou plus</span><small>Risques Géorisques interrogés au centre de chaque équipement public visible à l’écran.</small></div>}
            {(layers.parcels||layers.buildings)&&<div className="base-layer-legend"><strong>Repères cadastraux</strong>{layers.parcels&&<span><i className="parcel-symbol"/>Limite parcellaire bleue</span>}{layers.buildings&&<span><i className="building-symbol"/>Bâtiment en gris plein</span>}<small>Ces formes grises sont uniquement les empreintes bâties, jamais du zonage. Cliquez dans une parcelle pour afficher sa fiche complète.</small></div>}
            {layers.mos && <div className="mos-mini-legend"><strong>MOS 2025</strong><span><i style={{background:"#18753c"}}/>Nature et forêts</span><span><i style={{background:"#e3b341"}}/>Agriculture</span><span><i style={{background:"#0098d8"}}/>Eau</span><span><i style={{background:"#62b467"}}/>Espaces ouverts</span><span><i style={{background:"#e07a9a"}}/>Habitat</span><span><i style={{background:"#a05a9c"}}/>Activités</span><span><i style={{background:"#5576b9"}}/>Équipements</span><span><i style={{background:"#737b87"}}/>Transports</span><small>Survolez une surface pour lire le poste détaillé parmi les 79 catégories et son évolution depuis 2021.</small></div>}
            {layers.plu && <div className="zone-mini-legend"><span><i style={{background:"#df4f70"}}/>U · urbaine</span><span><i style={{background:"#e3a008"}}/>AU · à urbaniser</span><span><i style={{background:"#d6a721"}}/>A · agricole</span><span><i style={{background:"#27864d"}}/>N · naturelle</span></div>}
            {layers.servitudes && <div className="sup-family-legend"><strong>Familles de servitudes</strong><span><i style={{background:"#e1000f"}}/>Risques</span><span><i style={{background:"#0098d8"}}/>Eau</span><span><i style={{background:"#e3a008"}}/>Réseaux et énergie</span><span><i style={{background:"#0053b3"}}/>Transports</span><span><i style={{background:"#6f4c9b"}}/>Patrimoine</span><span><i style={{background:"#18753c"}}/>Environnement</span><small>Survolez une zone, une ligne ou un point pour connaître la catégorie, l’objet et l’identifiant GPU.</small></div>}
            {layers.publicLand && <div className="public-land-controls"><strong>Quel foncier afficher ?</strong><div><button type="button" className={publicLandFilter==="state"?"active":""} onClick={()=>setPublicLandFilter("state")}><i style={{background:"#e1000f"}}/>État uniquement</button><button type="button" className={publicLandFilter==="all"?"active":""} onClick={()=>setPublicLandFilter("all")}>Tout le foncier public</button></div><label>Afficher le foncier de l’État par commune<select defaultValue="" onChange={(event)=>{if(event.target.value)exploreCommune(event.target.value);}}><option value="">Choisir une commune…</option>{stateLandByCommune.map((item)=><option key={item.code} value={item.code}>{item.name} · {item.count.toLocaleString("fr-FR")} parcelles</option>)}</select></label>{publicLandFilter==="all"&&<div className="public-mini-legend"><span><i style={{background:"#e1000f"}}/>État</span><span><i style={{background:"#6f4c9b"}}/>Région</span><span><i style={{background:"#000091"}}/>Département</span><span><i style={{background:"#18753c"}}/>Commune</span><span><i style={{background:"#0098d8"}}/>HLM</span><span><i style={{background:"#7b61a8"}}/>Établissement</span></div>}</div>}
            <p className="public-land-note"><i/>Référentiel présumé : parcelles de personnes morales classées État, région, département, communes, HLM, SEM et établissements publics — millésime 2025.</p>
          </section>
          <details className="urban-services"><summary><span><strong>Sources publiques</strong><small>{Object.values(services).filter((state)=>state==="online").length}/7 services disponibles</small></span><b>{Object.values(services).every((state)=>state==="online")?"Connecté":"Vérification"}</b></summary><div className="urban-service-grid">{Object.entries(services).map(([name,state])=><span key={name}><i className={state}/><strong>{name}</strong><small>{state==="online"?"Disponible":state==="error"?"Indisponible":"Connexion…"}</small></span>)}</div></details>
        </aside>
        <section className="urban-map-wrap">
          {loadingLabels.length>0&&<div className="map-data-loader" role="status" aria-live="polite"><i/><span><strong>Chargement de la carte</strong><small>{loadingLabels.join(" · ")}</small></span></div>}
          {layers.mos&&<aside className="mos-map-legend" aria-label="Légende du MOS 2025"><strong>MOS 2025 · occupation du sol</strong><div><span><i style={{background:"#18753c"}}/>Nature et forêts</span><span><i style={{background:"#e3b341"}}/>Agriculture</span><span><i style={{background:"#0098d8"}}/>Eau</span><span><i style={{background:"#62b467"}}/>Espaces ouverts</span><span><i style={{background:"#e07a9a"}}/>Habitat</span><span><i style={{background:"#a05a9c"}}/>Activités</span><span><i style={{background:"#5576b9"}}/>Équipements</span><span><i style={{background:"#737b87"}}/>Transports</span></div><small>Survolez une surface pour afficher son usage détaillé et son évolution depuis 2021.</small></aside>}
          <div className={`map-guidance ${mapZoom >= 11 ? "ready" : "zoom-required"}`} role="status" aria-live="polite"><strong>{mapZoom >= 11 ? "Explorez les données affichées" : "Zoomez pour afficher les parcelles"}</strong><span>{mapZoom >= 11 ? layerFeedback : "Utilisez les boutons + / −, la molette de la souris ou pincez l’écran. Dès le niveau 11, les couches activées apparaissent sur tout le Val-d’Oise ; le détail précis et le clic sur une parcelle arrivent au niveau 13."}</span></div>
          <div className="urban-legend">{result && <span><i className="parcel"/>Sélection</span>}{layers.buildings && <span><i className="building"/>Bâtiments</span>}{layers.mos && <span><i className="mos"/>MOS</span>}{layers.plu && <span><i className="zone"/>PLU</span>}{layers.servitudes && <span><i className="sup"/>SUP</span>}{layers.publicLand && <span><i className="public"/>Foncier public</span>}</div><div ref={mapNode} className="urban-map" aria-label="Carte interactive d’urbanisme à la parcelle" />
        </section>
      </div>
      <footer className="urban-footer"><span><strong>Cadastre + GPU + BDNB + MOS + DGFiP</strong> · lecture parcellaire du Val-d’Oise</span><span>DDT Val-d’Oise · Leaflet 1.9.4</span></footer>
      {result && detailsOpen && <aside className="observatory-drawer" aria-label="Détail de la parcelle"><div className="observatory-drawer-head"><div className="print-brand"><img src={`${basePath}/prefet-val-doise-logo.png`} alt="Préfet du Val-d’Oise"/><span><b>Fiche d’identité parcellaire</b><small>DDT du Val-d’Oise · {new Date().toLocaleDateString("fr-FR")}</small></span></div><div className="drawer-actions"><button className="print-parcel" onClick={openParcelPdf}>Consulter la fiche PDF</button><button onClick={closeParcelDetails} aria-label="Fermer et désélectionner la parcelle">×</button></div><small>{result.addressLabel} · {result.commune}</small><h2 className="drawer-address">{streetOnly(result.address)}</h2><div className="parcel-id-print">Parcelle {firstValue(parcelProps,["section"],"")} {firstValue(parcelProps,["numero"],"—")}</div></div><div className="observatory-drawer-body urban-results">
        <section><div className="result-heading"><span>01</span><h2>Parcelle cadastrale</h2></div><dl><div><dt>Référence</dt><dd>{firstValue(parcelProps,["section"],"")} {firstValue(parcelProps,["numero"],"—")}</dd></div><div><dt>Contenance</dt><dd>{firstValue(parcelProps,["contenance"],"—")} m²</dd></div></dl>{result.addressLabel === "Adresse la plus proche" && <p className="address-caution">Adresse BAN la plus proche du point cliqué.</p>}</section>
        <section className="building-summary"><div className="result-heading"><span>02</span><h2>Bâti présent</h2></div>{buildingCount ? <><div className="parcel-kpis"><div><strong>{buildingCount}</strong><span>groupe{buildingCount > 1 ? "s" : ""} de bâtiments</span></div><div><strong>{formatNumber(builtFootprint," m²")}</strong><span>emprise bâtie estimée</span></div><div><strong>{formatNumber(coverageRatio," %")}</strong><span>taux d’emprise</span></div></div><dl><div><dt>Usage principal</dt><dd>{uniqueValues(result.buildings.map((building) => building.usage_principal_bdnb_open)).join(", ") || "Non renseigné"}</dd></div><div><dt>Construction la plus ancienne</dt><dd>{oldestBuilding || "Non renseignée"}</dd></div><div><dt>Hauteur maximale estimée</dt><dd>{maxHeight ? formatNumber(maxHeight," m") : "Non renseignée"}</dd></div><div><dt>Logements recensés</dt><dd>{dwellingCount || "Non renseigné"}</dd></div><div><dt>DPE disponible</dt><dd>{dpeClasses.length ? dpeClasses.join(", ") : "Non disponible"}</dd></div></dl><p className="source-caption">Source : BDNB Open, CSTB. Les groupes de bâtiments peuvent agréger plusieurs constructions.</p></> : <p className="empty-result">Aucun bâtiment rattaché à cette parcelle dans la BDNB Open.</p>}</section>
        <section><div className="result-heading"><span>03</span><h2>Propriété et foncier public</h2></div><div className={`ownership-status ${result.publicLand || publicOwners.length ? "known" : "unknown"}`}><small>{result.publicLand ? "Propriétaire public présumé" : "Catégorie détectée"}</small><strong>{ownerCategory}</strong></div>{!result.publicLand && publicOwners.length ? <div className="owner-list">{publicOwners.map((owner) => <span key={owner}>{owner}</span>)}</div> : !result.publicLand && <p className="empty-result">Le nom des propriétaires privés n’est pas diffusé en open data. L’absence de nom ne signifie pas que la parcelle est sans propriétaire.</p>}<p className="source-caption">Source ouverte : DGFiP, Fichiers des parcelles des personnes morales 2025. Le Référentiel foncier public Cerema avec accès métier reste la référence exhaustive.</p></section>
        <section><div className="result-heading"><span>04</span><h2>Occupation du sol — MOS 2025</h2></div>{result.mos?.mos2025 ? <><div className="mos-reading"><small>Usage observé en 2025</small><strong>{mosLabels[result.mos.mos2025] || `Poste MOS ${result.mos.mos2025}`}</strong><span>{result.mos.mos2021 === result.mos.mos2025 ? "Usage stable depuis 2021" : `Évolution depuis : ${mosLabels[result.mos?.mos2021 || 0] || `poste ${result.mos?.mos2021}`}`}</span></div><p className="source-caption">Source : Institut Paris Region, MOS 2021–2025, nomenclature détaillée à 79 postes.</p></> : <p className="empty-result">Occupation du sol non retournée à cet emplacement.</p>}</section>
        <section><div className="result-heading"><span>05</span><h2>Zonage d’urbanisme</h2></div>{result.zones.length ? result.zones.map((zone,index)=><div className="result-chip green" key={zone.id || index}><b>Zone {firstValue(zone.properties,["libelle","typezone","libelle_zone"],"GPU")}</b><small>{firstValue(zone.properties,["partition","nomfic"],"Document opposable")}</small></div>) : <p className="empty-result">Aucun zonage retourné par le GPU.</p>}{result.zones.length>0&&result.servitudes.length>0&&<p className="urbanism-cross-reading"><strong>À retenir</strong> Cette parcelle relève de {result.zones.map((zone)=>`la zone ${firstValue(zone.properties,["libelle","typezone","libelle_zone"],"GPU")}`).join(" et ")} et elle est également concernée par {result.servitudes.length} servitude{result.servitudes.length>1?"s":""}. Leur objet précis est détaillé dans le bloc suivant.</p>}</section>
        <section><div className="result-heading"><span>06</span><h2>Servitudes concernant la parcelle</h2></div><p className="result-count"><strong>{result.servitudes.length}</strong> assiette{result.servitudes.length>1?"s":""} intersectée{result.servitudes.length>1?"s":""} — liste complète retournée par le GPU</p>{result.servitudes.length?result.servitudes.map((sup,index)=>{const code=supCode(sup),p=sup.properties||{};return <div className="result-chip sup-detail" style={{borderLeftColor:supColor(sup)}} key={sup.id||`${code}-${index}`}><b>{code} · {supTitle(sup)}</b><span>{supDescription(code)}</span><small><strong>Famille :</strong> {supFamily(code)} · <strong>Emprise :</strong> {firstValue(p,["typeass"],"non renseignée")}</small><small><strong>Identifiant GPU :</strong> {firstValue(p,["idass"],"non renseigné")}{p.srcgeoass?` · Source géométrique : ${p.srcgeoass}`:""}</small>{p.fichier&&<small><strong>Acte associé :</strong> {p.fichier}</small>}</div>}) : <p className="empty-result">Aucune assiette surfacique, linéaire ou ponctuelle retournée pour cette parcelle.</p>}</section>
        <section><div className="result-heading"><span>07</span><h2>Risques recensés</h2></div>{result.risks.length ? <div className="risk-list">{result.risks.map((risk,index)=><span key={index}>{risk.libelle_risque_long || risk.libelle_risque || "Risque"}</span>)}</div> : <p className="empty-result">Aucun risque Gaspar retourné pour ce point.</p>}</section>
        <div className="urban-official-links"><strong>Vérifier auprès des services officiels</strong><a href="https://www.geoportail-urbanisme.gouv.fr/" target="_blank" rel="noreferrer">Géoportail de l’urbanisme ↗</a><a href="https://www.georisques.gouv.fr/" target="_blank" rel="noreferrer">Géorisques ↗</a><a href="https://www.cadastre.gouv.fr/" target="_blank" rel="noreferrer">Cadastre ↗</a></div>
        <p className="legal-note">Cette lecture est indicative. Les documents opposables et les services officiels restent la référence.</p>
      </div></aside>}
    </main>
  );
}

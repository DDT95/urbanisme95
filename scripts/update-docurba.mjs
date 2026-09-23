import { mkdir, writeFile } from "node:fs/promises";

const endpoint = "https://docurba.beta.gouv.fr/api/communes?departement=95";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === '"') {
      if (quoted && text[index + 1] === '"') {
        value += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      row.push(value);
      value = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && text[index + 1] === "\n") index += 1;
      row.push(value);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      value = "";
    } else {
      value += character;
    }
  }
  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }

  const [headers, ...records] = rows;
  return records.map((cells) => Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""])));
}

const response = await fetch(endpoint);
if (!response.ok) throw new Error(`Docurba a répondu ${response.status}`);

const records = parseCsv(await response.text());
const communes = Object.fromEntries(records.map((record) => [record.code_insee, {
  codeInsee: record.code_insee,
  commune: record.com_nom,
  epci: record.epci_nom,
  collectivitePorteuse: record.cp_nom,
  competence: record.cp_type,
  etat: record.plan_libelle_code_etat_simplifie,
  etatDetaille: record.plan_libelle_code_etat_complet,
  documentOpposable: record.pa_type_document,
  procedureEnCours: record.pc_type_procedure,
  documentEnCours: record.pc_type_document,
  datePrescription: record.pc_date_prescription,
  dateArret: record.pc_date_arret_projet,
  dateApprobation: record.pa_date_approbation,
  dateExecutoire: record.pa_date_executoire,
  pluih: record.pa_pluih === "True" || record.pc_pluih === "True",
  pluiValantScot: record.pa_plui_valant_scot === "True" || record.pc_plui_valant_scot === "True",
  objets: record.pc_objets || record.pa_objets,
}]).sort(([left], [right]) => left.localeCompare(right)));

const output = {
  source: endpoint,
  generatedAt: new Date().toISOString(),
  anneeCog: records[0]?.annee_cog ?? "",
  count: Object.keys(communes).length,
  communes,
};

await mkdir(new URL("../public/data/", import.meta.url), { recursive: true });
await writeFile(new URL("../public/data/docurba-95.json", import.meta.url), `${JSON.stringify(output, null, 2)}\n`, "utf8");
console.log(`${output.count} communes Docurba enregistrées dans public/data/docurba-95.json`);

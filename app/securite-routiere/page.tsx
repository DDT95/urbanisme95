import { ToolHeader } from "../components/ToolHeader";

export default function SecuriteRoutierePage() {
  return (
    <main className="road-safety-page">
      <ToolHeader title="Sécurité routière" subtitle="Accidents · gravité · réseau · prévention" />
      <section className="road-safety-intro">
        <p className="eyebrow">Observatoire 09</p>
        <h1>Comprendre l’accidentalité routière</h1>
        <p>Cette entrée est désormais indépendante de l’observatoire des transports. Elle accueillera la carte des accidents corporels, leur gravité, les usagers impliqués et les secteurs de vigilance du Val-d’Oise.</p>
        <div className="road-safety-status"><span>Module en préparation</span><strong>Transports et sécurité routière sont maintenant deux observatoires distincts.</strong></div>
      </section>
    </main>
  );
}

import Link from "next/link";

export function ToolHeader({ title, subtitle }: { title: string; subtitle: string }) {
  const basePath = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
  return (
    <header className="tool-header">
      <Link className="tool-logo" href="/" target="_blank" rel="noreferrer" aria-label="Ouvrir l’Atlas territorial dans un nouvel onglet">
        <img src={`${basePath}/prefet-val-doise-logo.png`} alt="Préfet du Val-d’Oise" />
      </Link>
      <div className="tool-title"><span>{subtitle}</span><strong>{title}</strong></div>
      <nav><Link href="/" target="_blank" rel="noreferrer">← Atlas</Link><Link href="/urbanisme" target="_blank" rel="noreferrer">Urbanisme ↗</Link><a href="https://ddt95.github.io/agriculture95/" target="_blank" rel="noreferrer">Agriculture ↗</a><a href="https://ddt95.github.io/eau95/" target="_blank" rel="noreferrer">Eau ↗</a><a href="https://ddt95.github.io/observatoire_risques_95/" target="_blank" rel="noreferrer">Risques ↗</a><a href="https://ddt95.github.io/observatoire_bati/" target="_blank" rel="noreferrer">Habitat ↗</a><a href="https://ddt95.github.io/transport95/?v=1ac3c80" target="_blank" rel="noreferrer">Transports ↗</a><Link href="/securite-routiere" target="_blank" rel="noreferrer">Sécurité routière ↗</Link></nav>
    </header>
  );
}

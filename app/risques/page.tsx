export default function RisquesPage() {
  return (
    <main className="embedded-tool">
      <iframe
        className="habitat-frame"
        src="https://ddt95.github.io/observatoire_risques_95/"
        title="Observatoire des risques du Val-d’Oise"
        allow="geolocation"
      />
    </main>
  );
}


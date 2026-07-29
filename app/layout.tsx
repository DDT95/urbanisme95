import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Urbanisme à la parcelle — DDT 95",
  description: "Cadastre, bâti, MOS, PLU, servitudes, risques et foncier public dans le Val-d’Oise.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}

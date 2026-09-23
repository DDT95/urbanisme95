# Urbanisme à la parcelle — DDT 95

Observatoire cartographique autonome de la Direction départementale des territoires du Val-d’Oise.

Il réunit le cadastre, le bâti, le MOS, le zonage PLU, les servitudes, les risques, le foncier public et la situation communale Docurba, avec génération d’une fiche parcellaire PDF.

## Développement

```bash
npm install
npm run data:docurba
npm run dev
```

L’export Docurba du Val-d’Oise est converti en JSON local dans `public/data/docurba-95.json`. La publication GitHub Pages le régénère automatiquement chaque lundi.

## Publication

La branche `main` est publiée automatiquement par GitHub Actions sur :

https://ddt95.github.io/urbanisme95/

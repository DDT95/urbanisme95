# Parcellaire DDT95 — plugin QGIS

Outil QGIS pour générer l'état parcellaire et le plan parcellaire à partir
d'un CSV de parcelles et d'une base PostgreSQL Fichiers Fonciers, sans
jamais modifier de SQL à la main.

**Statut actuel : Phase 2 (prototype backend)** — CSV → import → 3 tables
PostgreSQL → couches QGIS → bilan. Les mises en page/atlas PDF (Phase 3-4)
ne sont pas encore branchées : il n'existait pas de projet QGIS existant à
inspecter dans ce dépôt (voir échange initial). Le bouton « Exporter les
PDF » est présent mais désactivé en attendant.

## ⚠️ À vérifier avant la première exécution réelle

Je n'ai pas d'accès à votre base PostgreSQL depuis cet environnement. Les
requêtes générées supposent que les colonnes des tables Fichiers Fonciers
suivent la nomenclature MAJIC standard (`idpar`, `ccosec`, `dnupla`,
`ddenom`, `dlign3`...`dlign6`, etc.). **Un seul fichier centralise ces
hypothèses** :

```
parcellaire_ddt95/core/column_mapping.py
```

Avant de lancer une commande sur des données réelles :

1. Ouvrez le plugin, choisissez votre connexion et votre millésime.
2. Cliquez sur **« Diagnostiquer les tables sources »** : le plugin
   compare les colonnes attendues avec celles réellement présentes dans
   `x_ff<AAAA>_dep.d95_fftp_<AAAA>_pnb10_parcelle`,
   `..._pnb21_suf` et `..._proprietaire_droit_non_ano`, et signale les
   écarts dans le compte rendu.
3. Corrigez `column_mapping.py` si nécessaire (un seul endroit à modifier).
4. Vérifiez aussi le SRID des géométries (`SRID = 2154` par défaut,
   Lambert-93) dans le même fichier.

## Installation

### Sur Mac (développement/test)

1. Repérez le dossier de profils QGIS :
   `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Copiez (ou créez un lien symbolique vers) le dossier
   `qgis-plugin/parcellaire_ddt95/` à cet endroit.
3. Dans QGIS : Extensions → Gérer/Installer les extensions → Installées →
   cochez « Parcellaire DDT95 ».
4. Le bouton apparaît dans le menu Base de données et dans la barre
   d'outils.

### Sur Windows (poste professionnel)

1. Compressez le dossier `parcellaire_ddt95/` en `.zip` (le `.zip` doit
   contenir directement `parcellaire_ddt95/metadata.txt`, pas un dossier
   parent supplémentaire).
2. Dans QGIS : Extensions → Gérer/Installer les extensions → Installer
   depuis un ZIP → sélectionnez le fichier.
3. Activez l'extension.

Aucune dépendance Python externe n'est requise : le plugin n'utilise que
l'API PyQGIS native (`qgis.core`, `qgis.PyQt`) et la bibliothèque standard
Python (`csv`, `re`). Aucun chemin Mac (`/Users/...`) n'est codé en dur,
aucun mot de passe n'est stocké : la connexion PostgreSQL doit déjà être
enregistrée dans QGIS (Panneau Parcourir → PostgreSQL → Nouvelle
connexion), et QGIS gère l'authentification.

## Utilisation

1. Choisir le CSV des parcelles (colonnes attendues : `id`, `commune`,
   `prefixe`, `section`, `numero`, `contenance`, et optionnellement
   `created`, `updated`, `layer`).
2. Choisir la connexion PostgreSQL enregistrée dans QGIS.
3. Saisir le schéma de travail (ex. `q_26_01_4825`) et le nom court de la
   commande (ex. `wk`).
4. Vérifier/ajuster le millésime des fichiers fonciers.
5. Cliquer sur **Générer les données**. Si des tables `etat_p_wk`,
   `plans_parcellaire_wk` ou `comparaison_parcelles_wk` existent déjà pour
   cette commande, une confirmation est demandée avant remplacement.
6. Les trois tables sont créées dans une seule transaction PostgreSQL
   (tout ou rien), puis chargées automatiquement dans le projet sous les
   noms fixes `etat_parcellaire_courant`, `plan_parcellaire_courant`,
   `comparaison_courante` (l'état parcellaire sans géométrie, le plan
   comme couche polygonale).
7. Le compte rendu affiche le bilan : nombre de parcelles CSV, lignes
   d'état, parcelles au plan, anomalies et liste des identifiants
   manquants.
8. **Vérifier** recalcule uniquement la comparaison sans réimporter le
   CSV (utile après une modification manuelle des données sources).

## Sécurité et confidentialité

- Aucune donnée n'est envoyée sur Internet : tout le traitement se fait
  en local (QGIS) et sur votre base PostgreSQL professionnelle.
- Tous les noms de schéma/table/commande saisis par l'utilisateur sont
  validés par une expression régulière stricte
  (`parcellaire_ddt95/core/identifiers.py`) puis échappés avant toute
  utilisation dans une requête SQL — aucune concaténation SQL brute.
- Les données du CSV sont importées via le fournisseur PostgreSQL natif
  de QGIS (attributs de feature liés), jamais concaténées dans du texte
  SQL.
- Aucun identifiant de connexion, mot de passe ou chemin local n'est
  codé en dur dans le plugin.

## Prochaines étapes (Phase 3 à 5)

- Phase 3 : une fois un projet QGIS avec mises en page (`etat_p`,
  `plans_parcellaire`, atlas par commune) disponible, le brancher sur les
  couches à noms fixes ci-dessus et documenter son fonctionnement avant
  toute modification.
- Phase 4 : implémenter l'export PDF (atlas QGIS) dans
  `core/export_pdf.py` et activer le bouton correspondant.
- Phase 5 : notice d'installation Windows définitive une fois testé sur
  le poste professionnel.

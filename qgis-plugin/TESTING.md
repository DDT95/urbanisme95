# Tester le plugin sur votre Mac

Ce guide fait tourner le plugin de bout en bout avec des **données
entièrement fictives** (`tests/fixtures/`), pour valider le circuit avant
de le pointer sur vos vraies tables Fichiers Fonciers.

Prérequis : QGIS installé sur le Mac, un serveur PostgreSQL accessible
(local via Postgres.app/Homebrew, ou un serveur de test) avec l'extension
PostGIS disponible.

## 1. Préparer une base de test

```bash
createdb parcellaire_test
psql parcellaire_test -f qgis-plugin/tests/fixtures/create_test_referentiels.sql
psql parcellaire_test -c "CREATE SCHEMA IF NOT EXISTS q_test_wk;"
```

Cela crée les schémas fictifs `x_ff2024_dep`, `x_ff2024_non_ano_dep`,
`r_drieat` avec 2 parcelles complètes (propriétaire, géométrie, dont une
avec GPA), et un schéma vide `q_test_wk` qui servira de schéma de travail.
Le CSV de test (`tests/fixtures/sample_parcelles.csv`) contient 3
parcelles : les 2 ci-dessus, plus une 3ᵉ volontairement absente des
référentiels, pour vérifier la détection d'anomalie.

## 2. Enregistrer la connexion dans QGIS

Panneau **Parcourir** → PostgreSQL → clic droit → **Nouvelle connexion...**
→ pointez vers `parcellaire_test` (hôte, port, base, identifiants de test).
Testez la connexion.

## 3. Installer le plugin

```bash
mkdir -p "$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"
ln -s "$(pwd)/qgis-plugin/parcellaire_ddt95" \
  "$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/parcellaire_ddt95"
```

(Exécutez cette commande depuis la racine du dépôt. Un lien symbolique
permet de tester vos futures modifications sans réinstaller.)

Redémarrez QGIS (ou Extensions → Recharger les extensions si vous avez le
plugin *Plugin Reloader*), puis Extensions → Gérer/Installer les
extensions → Installées → cochez **Parcellaire DDT95**.

## 4. Faire tourner le prototype

1. Ouvrez le plugin (menu Base de données → « État et plan parcellaire... »).
2. CSV : `qgis-plugin/tests/fixtures/sample_parcelles.csv`.
3. Connexion : celle créée à l'étape 2.
4. Schéma de travail : `q_test_wk`.
5. Commande : `wk`.
6. Millésime : `2024` (déjà par défaut).
7. Cliquez **Diagnostiquer les tables sources** : le compte rendu doit
   indiquer *« Toutes les colonnes attendues sont présentes »* pour les
   3 tables — cela confirme que `column_mapping.py` correspond bien au
   jeu de test (et donc que la mécanique fonctionne ; ce sera à revérifier
   avec vos vraies tables ensuite).
8. Cliquez **Générer les données**.

## 5. Résultat attendu

- Compte rendu : `3` parcelles CSV, `2` lignes d'état, `2` parcelles au
  plan, `1` anomalie (`959990000A0003`, `manquant_etat` et
  `manquant_plan`).
- Trois couches ajoutées au projet : `etat_parcellaire_courant` (table,
  sans géométrie, avec la colonne `gpa` = `oui` pour la première
  parcelle et `non` pour la seconde), `plan_parcellaire_courant`
  (polygones), `comparaison_courante`.
- Relancez **Générer les données** une seconde fois : une boîte de
  dialogue doit demander confirmation avant de remplacer les tables
  existantes.
- Cliquez **Vérifier** : le bilan doit rester identique sans réimporter
  le CSV.

Si tout ceci fonctionne, le circuit CSV → PostgreSQL → QGIS est validé.
L'étape suivante sera de pointer `column_mapping.py` sur vos vraies
tables Fichiers Fonciers (via **Diagnostiquer les tables sources** pour
repérer les écarts) puis de rejouer ce test avec un schéma de travail
réel.

## Nettoyage

```bash
dropdb parcellaire_test
rm "$HOME/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/parcellaire_ddt95"
```

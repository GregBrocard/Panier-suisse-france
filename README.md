# Panier Suisse France

Payer moins là où ça ne coûte rien aux paysans suisses. Comparaison automatisée du prix des courses entre la Suisse et la France voisine, avec un calculateur personnel (départ depuis toute localité suisse, 12 zones françaises), à partir de données publiques : comparaison officielle des niveaux de prix (Eurostat–OFS), OFAG, INSEE, BCE, OFDF, TCS, Open Prices, UFC-Que Choisir, flux officiel des prix des carburants et relevé Migros.

- **Site** : https://gregbrocard.github.io/Panier-suisse-france/ (version 3.1) · archives : `/v3/` (branche `v3`), `/v2/` (branche `v2`) et `/v1/` (branche `v1`)
- **Méthodologie** : [METHODOLOGIE.md](METHODOLOGIE.md)
- **Réglages** : panier [config/panier.yaml](config/panier.yaml) · villes [config/destinations.yaml](config/destinations.yaml) · site [config/site.yaml](config/site.yaml)
- **Données** : tableurs `ecarts_par_rayon.csv`, `produits.csv`, `historique_fruits_legumes.csv` (générés dans le site, page Données ouvertes), `data/pli.json`, `data/latest.json`, `data/series.json`, `data/essence.json`, `data/barometre/`, `data/releves/`, `data/controles.json`

## Les robots (GitHub Actions)

| Robot | Quand | Ce qu'il fait |
|---|---|---|
| Relevé mensuel des prix (`collect.yml`) | le 20 de chaque mois, 06:17 UTC | tests, relevé complet, contrôles, site, publication ; ouvre un ticket en cas d'alerte |
| Essence du jour (`essence.yml`) | chaque jour, 05:41 UTC | prix des stations et change du jour, site, publication |
| Tests (`tests.yml`) | à chaque modification du code | vérifie les calculs et la construction du site |

Lancer à la main : onglet **Actions** → choisir le robot → *Run workflow*.

## Si le robot s'arrête

1. Onglet **Actions** : ouvrir la dernière exécution en rouge et lire l'étape en échec.
2. Un ticket « à vérifier » dans l'onglet **Issues** décrit les alertes du dernier relevé ; le site reste publié avec les valeurs du mois précédent, signalées.
3. GitHub désactive les tâches planifiées d'un dépôt public sans activité pendant 60 jours : si c'est le cas, **Actions** → robot → *Enable workflow*.
4. Relancer *Relevé mensuel des prix* avec `site_seulement = true` republie le site sans refaire le relevé.

## À activer (aucune action technique de plus)

Dans `config/site.yaml` : nom de domaine (`base_url`), statistiques sans cookies (`goatcounter`), lettre d'information (`newsletter_url`), liens rémunérés (`affiliation`), e-mail de contact (`contact_email`). Une valeur vide désactive la fonction.

## Ce que fait la version 3.1

- Principe : économiser en France sur ce que la Suisse importe (épicerie, huiles, boissons), garder en Suisse ce qu'elle produit (viande, laitages et œufs, fruits et légumes) ; réglage « Vous achetez suisse » dans le calculateur.
- Pages « Pourquoi c'est plus cher en Suisse » et « Acheter suisse moins cher » (fermes, distributeurs, boucheries d'OpenStreetMap, `data/fermes_osm.json`, relevé chaque mois par le robot de l'essence).

- L'écart par rayon part de la comparaison officielle Eurostat–OFS (`data/pli.json`, relue chaque mois), mise à jour par le change et nos relevés : voir METHODOLOGIE.md § 3.0.
- Le calculateur demande où l'on fait ses courses en Suisse (Aldi/Lidl par défaut, Migros, Coop ; test K-Tipp).
- Pages générées : accueil, essence, 12 zones, prix par produit (`/prix/`), supermarchés suisses (`/suisse/`), partenaires, baromètre mensuel, douane, données ouvertes, widget, méthode.
- Après chaque publication, le robot vérifie que le site répond et ouvre un ticket sinon.

## Ajouter un prix d'essence suisse

Le fichier [data/prix_ch.yaml](data/prix_ch.yaml) contient les prix relevés en Suisse, station par station (le mode « Où faire le plein » les utilise). Il se modifie directement sur GitHub, même depuis un téléphone : un bloc par station, avec la date. Les visiteurs signalent des prix via l'onglet **Issues** (étiquette « prix ») : vérifier, puis recopier dans le fichier.

## En local

```bash
pip install -r requirements.txt
python -m pytest -q tests          # tests
python -m scraper.build            # relevé mensuel (données)
python -m scraper.essence          # essence du jour
python -m scraper.site             # site complet dans dist/
```

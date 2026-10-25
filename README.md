# Panier Suisse France

Faire ses courses en France, ça vaut le coup ? Comparaison automatisée du prix des courses entre la Suisse et la France voisine, avec un calculateur personnel (départ depuis toute localité suisse, 12 zones françaises), à partir de données publiques : OFAG, INSEE, Eurostat, BCE, OFDF, TCS, Open Prices, UFC-Que Choisir, flux officiel des prix des carburants et relevé Migros.

- **Site** : https://gregbrocard.github.io/Panier-suisse-france/ (version 2) · version 1 archivée : `/v1/` et branche `v1`
- **Méthodologie** : [METHODOLOGIE.md](METHODOLOGIE.md)
- **Réglages** : panier [config/panier.yaml](config/panier.yaml) · villes [config/destinations.yaml](config/destinations.yaml) · site [config/site.yaml](config/site.yaml)
- **Données** : `data/latest.json`, `data/series.json`, `data/essence.json`, `data/barometre/`, `data/releves/`, `data/controles.json`

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

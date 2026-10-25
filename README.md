# Panier Suisse / France

Relevé mensuel automatisé du prix d'un même panier de courses en Suisse romande et dans la France voisine (Annemasse, Divonne / La Cure, Vallorbe / Pontarlier).

- **Méthodologie** : [METHODOLOGIE.md](METHODOLOGIE.md)
- **Panier** : [config/basket.yaml](config/basket.yaml) · **Enseignes** : [config/stores.yaml](config/stores.yaml)
- **Données** : `data/history.json` (série mensuelle), `data/latest.json` (dernier relevé détaillé), `data/releves/` (archives)

## Fonctionnement

Le workflow GitHub Actions `Relevé mensuel des prix` tourne le 2 de chaque mois. Il lit les sites publics des enseignes, retient pour chaque besoin le produit qui correspond aux règles du panier, convertit au taux BCE et enregistre le résultat dans `data/`.

Lancer à la main : onglet **Actions** → *Relevé mensuel des prix* → *Run workflow*.

En local :

```bash
pip install -r requirements.txt
python -m scraper.run                          # relevé complet
SCRAPER_ONLY=ch_coop python -m scraper.run     # une seule enseigne
SCRAPER_DEBUG=1 python -m scraper.probe        # sonde les sites (pages gardées dans debug/)
```

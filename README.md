# Panier Suisse × France

Comparaison mensuelle automatisée du prix des courses entre la Suisse romande et la France voisine (départ depuis toute localité suisse, 12 zones françaises de destination), à partir de données publiques : OFAG, INSEE, BCE, OFDF, Open Prices, flux officiel des prix des carburants et relevé Migros.

- **Méthodologie** : [METHODOLOGIE.md](METHODOLOGIE.md)
- **Panier** : [config/panier.yaml](config/panier.yaml) · **Villes françaises** : [config/destinations.yaml](config/destinations.yaml)
- **Données** : `data/series.json` (historique depuis 2006), `data/latest.json` (dernier relevé), `data/releves/` (archives)
- **Site** : `site/index.html` (page autonome, publiée sur GitHub Pages)

## Fonctionnement

Le workflow **Relevé mensuel des prix** tourne le 20 de chaque mois : il interroge les sources (`scraper/build.py`), assemble le site (`scraper/site.py`), enregistre les données dans le dépôt et publie la page.

Lancer à la main : onglet **Actions** → *Relevé mensuel des prix* → *Run workflow*.

```bash
pip install -r requirements.txt
python -m scraper.build   # données
python -m scraper.site    # site/index.html
```

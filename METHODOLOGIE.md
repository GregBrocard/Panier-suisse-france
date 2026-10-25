# Méthodologie — Panier Suisse × France

Version 1.1 · octobre 2026 (ajout du niveau de prix par magasin)

## 1. Question posée

Combien coûtent les mêmes courses du quotidien en Suisse romande et dans la France voisine, et à partir de quand le déplacement vaut-il la peine ? Quatre passages frontaliers sont couverts : Genève ↔ Annemasse, Nyon ↔ Divonne / Gex, La Cure ↔ Les Rousses, Vallorbe ↔ Jougne / Pontarlier.

## 2. Principe : des sources publiques, vérifiables et automatisées

Le comparateur n'utilise que des données publiées ouvertement. Il ne contourne aucune protection technique de site marchand. Les enseignes dont le site bloque les robots (Coop, Aldi Suisse, E.Leclerc, Carrefour, Intermarché, Super U) ne sont pas relevées.

Les données sont reconstruites automatiquement le 20 de chaque mois par un workflow GitHub Actions public. Chaque chiffre affiché peut être retrouvé dans `data/latest.json` (photo du mois), `data/series.json` (historique) et `data/releves/AAAA-MM.json` (archives des relevés automatiques).

## 3. Les couches du panier

Le panier est défini dans `config/panier.yaml`. Il décrit des produits courants comparables, et non une liste de produits d'un seul pays.

### 3.1 Fruits et légumes : séries statistiques officielles (historique depuis 2006)

| | Suisse | France |
|---|---|---|
| Source | Office fédéral de l'agriculture (OFAG), prix de consommation mensuels relevés dans le commerce de détail, région de vente « Suisse » (données ouvertes LINDAS) | INSEE, prix moyens mensuels de vente au détail en métropole (base BDM) |
| Unité | CHF par kg | EUR par kg |

14 produits : bananes, pommes, poires, clémentines, oranges, tomates, carottes, courgettes, champignons de Paris, oignons jaunes, poireaux, endives, poivrons, pommes de terre. Quand l'OFAG publie plusieurs variétés pour un même produit (ex. pommes Golden, Gala et Braeburn), on prend leur moyenne. Quand l'OFAG publie plusieurs séries pour un même produit et un même mois, on prend également leur moyenne.

Le pain est affiché à titre indicatif mais n'entre pas dans le total : le pain mi-blanc suisse et la baguette française ne sont pas le même produit.

### 3.2 Viande

France : INSEE (entrecôte de bœuf, escalope de veau, rôti de porc dans le filet, jambon supérieur). Suisse : relevé automatique du site Migros, **médiane** des produits correspondants au kilo, hors bio et hors promotion. La médiane est utilisée parce que la référence française est elle-même une moyenne de marché, et non un premier prix.

### 3.3 Produits de marque identiques

Nutella, Coca-Cola (bouteille PET), Red Bull 25 cl, Pringles Original, Kinder Bueno, Lindt Excellence noir. Comparaison au **prix unitaire** (par kg ou par litre), pour neutraliser les différences de format.
- Suisse : Migros, produit de la même marque et de la même gamme, prix régulier.
- France : Open Prices (Open Food Facts), base ouverte de tickets de caisse : médiane des prix hors promotion relevés en France sur 12 mois, pour le code-barres indiqué. Le nombre de relevés est affiché ; sous 5 relevés, le chiffre est signalé comme indicatif.

### 3.4 Carburant

- France : flux officiel des prix des stations (ministère de l'Économie, data.economie.gouv.fr), moyenne des stations de chaque zone : Annemasse (74100, 74240), Divonne / Gex (01220, 01170), Les Rousses (39220), Jougne / Pontarlier (25370, 25300). Le SP95 pur ayant presque disparu, on retient le SP95 ou, à défaut, l'E10.
- Suisse : tableau T 4.4 de l'Office fédéral de la douane et de la sécurité des frontières (OFDF), prix à la colonne en zone frontière genevoise, publié mensuellement.
- Historique France : INSEE, prix moyens mensuels des carburants.

### 3.5 Niveau de prix de chaque magasin français

Les prix français des sections 3.1 à 3.3 sont des moyennes nationales. Pour estimer les prix d'un magasin précis, on utilise le comparateur des supermarchés de l'UFC-Que Choisir, qui relève chaque jour, dans chaque magasin disposant d'un drive, le prix d'un même panier d'une centaine de produits (marques nationales et marques de distributeur ; épicerie, fruits et légumes, crèmerie, boucherie, boissons, hygiène).

- **Magasins d'une zone.** Un ou deux magasins « graines » par zone, plus tous les magasins situés à moins de 15 km d'eux selon la liste publiée par Que Choisir (limités au département de la zone).
- **Référence nationale.** Un panel de magasins tirés au hasard dans toute la France (tirage fixe, graine 2026), dont on prend la médiane du panier global.
- **Indice du magasin** = panier global du magasin ÷ médiane du panel. Un indice de 0,92 signifie un magasin 8 % moins cher que le magasin français typique.
- **Indice de la zone** = médiane des indices des magasins de la zone.
- **Écart Suisse / magasin** pour une catégorie : (1 + écart Suisse / France) ÷ indice − 1.

Cette méthode suppose que l'écart d'un magasin à la moyenne est le même dans toutes les catégories ; c'est une approximation. Les données de Que Choisir leur appartiennent ; elles sont publiées avec l'accord de l'UFC-Que Choisir (octobre 2026), avec citation de la source et lien vers leur comparateur. Le paramètre `quechoisir.publier` de `config/panier.yaml` permet de les retirer du site public à tout moment.

## 4. Calculs

**Change.** Les prix français sont convertis au taux de référence EUR/CHF de la Banque centrale européenne : moyenne mensuelle pour l'historique, dernier taux quotidien pour la photo du mois. Le taux réellement obtenu par carte est en général 1 à 2 % moins favorable.

**Écart.** Pour un produit : écart = prix suisse ÷ prix français en CHF − 1. Pour un panier : somme des prix suisses ÷ somme des prix français, chaque produit étant pondéré par sa quantité de référence `qty` (panier hebdomadaire d'un ménage de deux personnes). Un mois n'est calculé que si au moins 60 % des produits sont disponibles des deux côtés ; seuls les produits disponibles des deux côtés ce mois-là entrent dans le calcul.

**Moyenne sur 12 mois.** Les fruits et légumes étant saisonniers, l'indicateur principal est la moyenne des écarts mensuels sur les 12 derniers mois.

**Calculateur de trajet.**
- économie sur les courses = dépense × taux d'économie pondéré selon la composition du panier choisie (viande, fruits et légumes, marques), chaque écart étant ajusté par l'indice du magasin choisi (ou de la zone) ;
- coût du trajet = distance aller-retour × consommation ÷ 100 × prix suisse du carburant ;
- plein en France (option) = litres × (prix suisse − prix moyen de la zone) ;
- TVA suisse : si les achats dépassent 150 CHF par personne, 2,6 % (taux réduit alimentaire) sur la totalité ;
- seuil de rentabilité = coût du trajet ÷ taux d'économie.
Le temps passé et l'usure du véhicule ne sont pas comptés.

## 5. Règles douanières rappelées (OFDF, ch.ch, 2026)

- Franchise de valeur : 150 CHF par personne et par jour ; au-delà, TVA suisse sur la totalité.
- Viande : 1 kg par personne et par jour en franchise ; au-delà, droits de douane sur l'excédent.
- Alcool : 5 L sous 18 % vol., 1 L au-dessus ; tabac : 250 cigarettes.

## 6. Limites connues

- Les prix alimentaires français de base sont des moyennes nationales ; l'ajustement par magasin (§ 3.5) repose sur un indice global, pas sur des prix par produit.
- La viande suisse provient d'une seule enseigne (Migros), faute de série officielle ouverte.
- Open Prices dépend des tickets partagés par ses contributeurs : certains produits ont peu de relevés.
- L'origine et la qualité des fruits et légumes ne sont pas contrôlées.
- Les quantités de référence sont forfaitaires ; une pondération selon l'IPC de l'OFS est prévue dans une version ultérieure.

## 7. Citer

> Brocard, G. (2026). *Panier Suisse × France*, méthodologie v1.1. Données OFAG, INSEE, BCE, OFDF, Open Prices, UFC-Que Choisir. Code et données : https://github.com/GregBrocard/Panier-suisse-france

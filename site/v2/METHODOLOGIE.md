# Méthodologie — Panier Suisse France

Version 2.1 · octobre 2026. La version 1 (septembre–octobre 2026) reste consultable : [site archivé](https://gregbrocard.github.io/Panier-suisse-france/v1/) et branche `v1` du dépôt. Les changements de la version 2 sont listés à la section 9.

## 1. Question posée

Combien coûtent les mêmes courses du quotidien en Suisse et dans la France voisine, et à partir de quand le déplacement vaut-il la peine, une fois le trajet, l'usure de la voiture et la douane comptés ?

- **Départ** : n'importe quelle localité de Suisse (répertoire officiel des localités de swisstopo, environ 4 100 localités).
- **Arrivée** : l'une des 12 zones françaises où les Suisses font couramment leurs courses (`config/destinations.yaml`) : Annemasse, Saint-Julien-en-Genevois, Saint-Genis / Ferney (avec Thoiry), Divonne / Gex (avec Segny), Thonon-les-Bains, Évian-les-Bains, Les Rousses, Jougne, Pontarlier, Morteau, Delle, Saint-Louis. Les communes voisines du Pays de Gex sont regroupées parce que, prises une à une, elles comptent trop peu de magasins référencés.

## 2. Principe : des sources publiques, vérifiables et automatisées

Le comparateur n'utilise que des données publiées ouvertement. Il ne contourne aucune protection technique de site marchand. Les enseignes dont le site bloque les robots (Coop, Aldi Suisse, Lidl Suisse, Denner, E.Leclerc, Carrefour, Intermarché, Super U) ne sont pas relevées directement.

Deux robots publics (GitHub Actions) tiennent le site à jour :

- **relevé mensuel**, le 20 de chaque mois : tous les prix, les magasins, les trajets ;
- **relevé quotidien de l'essence**, chaque matin : prix des stations françaises et taux de change du jour.

Chaque chiffre affiché peut être retrouvé dans les fichiers ouverts : `data/latest.json` (photo du mois), `data/series.json` (historique), `data/essence.json` (essence du jour), `data/releves/AAAA-MM.json` (archives des relevés), `data/barometre/AAAA-MM.json` (chiffres publiés chaque mois), `data/controles.json` (contrôles automatiques).

## 3. Les couches du panier

Le panier est défini dans `config/panier.yaml` (version 2). Le calculateur regroupe les produits en quatre catégories : viande, fruits et légumes, produits laitiers, épicerie et marques.

### 3.1 Fruits et légumes : séries statistiques officielles (historique depuis 2006)

| | Suisse | France |
|---|---|---|
| Source | Office fédéral de l'agriculture (OFAG), prix de consommation mensuels relevés dans le commerce de détail, région de vente « Suisse » (données ouvertes LINDAS) | INSEE, prix moyens mensuels de vente au détail en métropole (base BDM) |
| Unité | CHF par kg | EUR par kg |

14 produits : bananes, pommes, poires, clémentines, oranges, tomates, carottes, courgettes, champignons de Paris, oignons jaunes, poireaux, endives, poivrons, pommes de terre. Quand l'OFAG publie plusieurs variétés pour un même produit (ex. pommes Golden, Gala et Braeburn), on prend leur moyenne. La série OFAG est une moyenne de tout le commerce de détail suisse, discounters compris.

Le pain est affiché à titre indicatif mais n'entre pas dans le total : le pain mi-blanc suisse et la baguette française ne sont pas le même produit.

### 3.2 Produits laitiers et huile (nouveau en v2)

Cinq produits : lait UHT, beurre, emmental, yaourt nature, huile de tournesol.

- **Suisse** : OFAG, prix de consommation mensuels (lait drink UHT, beurre de choix, Emmentaler doux, yogourt nature, huile de tournesol non bio importée). Série OFAG : moyenne de tout le commerce de détail.
- **France** : l'INSEE a cessé de publier le prix moyen de ces produits en décembre 2019. Le prix est donc **estimé** :

  prix estimé (mois m) = prix moyen INSEE de décembre 2019 × indice des prix (m) ÷ indice des prix (décembre 2019)

  avec l'indice des prix à la consommation harmonisé de l'INSEE (base 2025) du poste correspondant : lait écrémé (idbank 011812298), beurre et matières grasses animales (011812325), fromage (011812307), yaourt (011812310), huiles végétales (011812322). Les prix de 2019 utilisés sont ceux des séries arrêtées 000442480 (lait UHT demi-écrémé), 000442490 (beurre extra fin 250 g, ramené au kg), 000442487 (emmental français), 000849398 (yaourt nature 500 g, ramené au kg) et 000442493 (huile de tournesol).

Cette méthode suppose que les prix de ces produits ont évolué comme l'ensemble de leur poste depuis 2019. Elle est indiquée comme une estimation partout sur le site. Les produits ne sont pas strictement identiques (lait drink à 2,7 % en Suisse, demi-écrémé en France).

### 3.3 Viande

France : INSEE (entrecôte de bœuf, escalope de veau, rôti de porc dans le filet, jambon supérieur). Suisse : relevé automatique du site Migros, **médiane** des produits correspondants au kilo, hors bio et hors promotion, **réduite de 5 %**.

Pourquoi −5 % : le comparateur s'adresse à des ménages attentifs aux prix, qui font en Suisse plutôt leurs courses chez un discounter. Les sites d'Aldi, Lidl et Denner ne pouvant pas être relevés automatiquement, on part du prix Migros et on le ramène au niveau des discounters. Le test de prix K-Tipp d'août 2025 (100 produits courants) donne un panier de 243,54 CHF chez Migros, contre 232,83 CHF chez Lidl et 230,94 CHF chez Aldi, soit un écart d'environ 5 %. Le paramètre `viande_ajustement_discount` de `config/panier.yaml` porte ce taux ; le prix Migros brut reste publié (`ch_migros` dans `data/latest.json`).

**Taille d'échantillon (v2)** : un morceau doit reposer sur au moins 5 produits Migros. Sinon, le prix suisse du mois précédent est repris et signalé sur le site (section 7).

La viande suisse et la viande vendue en moyenne en France ne sont pas toujours de même origine ni de même label ; la comparaison porte sur les prix réellement payés pour un même morceau.

### 3.4 Produits de marque identiques

Dix produits (v2 : quatre de plus) : Nutella, Coca-Cola (bouteille PET), Red Bull 25 cl, Pringles Original, Kinder Bueno, Lindt Excellence noir, Oreo Original, Mini Babybel, Evian 6 × 1,5 L, Barilla Pesto alla Genovese. Comparaison au **prix unitaire** (par kg ou par litre), pour neutraliser les différences de format.

- Suisse : Migros, produit de la même marque et de la même gamme, prix régulier. Les produits de marque coûtent pratiquement le même prix chez Migros et chez les discounters (relevé bonus.ch, août 2025) : pas d'ajustement.
- France : Open Prices (Open Food Facts), base ouverte de tickets de caisse : médiane des prix hors promotion relevés en France pour le code-barres indiqué, **sur 6 mois s'il y a au moins 10 relevés, sinon sur 12 mois** (v2). Le nombre de relevés et la fenêtre sont affichés ; sous 10 relevés, le chiffre est signalé comme indicatif.

Dans le calculateur, l'écart des marques représente la catégorie « épicerie et marques » (pain et céréales, sucre et chocolat, boissons, autres produits d'épicerie).

### 3.5 Carburant

- **France** : flux officiel des prix des stations (ministère de l'Économie, data.economie.gouv.fr), moyenne des stations à moins de 8 km du centre de chaque zone (ou de l'une de ses communes). Le SP95 pur ayant presque disparu, on retient le SP95 ou, à défaut, l'E10. **Relevé chaque jour** (v2) ; les trois stations les moins chères de chaque zone sont publiées.
- **Suisse et autres frontières** : tableau T 4.4 de l'Office fédéral de la douane et de la sécurité des frontières (OFDF), prix à la colonne en zone frontière, publié mensuellement, pour cinq frontières : Genève / France, Bâle / Weil am Rhein, Kreuzlingen / Constance, Tessin / Italie, Liechtenstein / Autriche. Le calculateur utilise la zone genevoise.
- **Historique France** : INSEE, prix moyens mensuels des carburants.

**Correction (v2)** : dans le texte du tableau OFDF, le premier bloc de chiffres est l'essence 95 et le second le diesel ; la version 1 les lisait dans l'ordre inverse, ce qui surestimait d'environ 13 % le coût de l'essence pour le trajet et inversait le gain d'un plein en France. Vérification : le prix français indiqué par l'OFDF dans chaque bloc correspond respectivement au SP95 et au gazole du flux officiel français et de la série INSEE. Un contrôle automatique compare désormais chaque mois ces prix et corrige une éventuelle inversion en la signalant.

### 3.6 Niveau de prix de chaque magasin français

Les prix français des sections 3.1 à 3.4 sont des moyennes nationales. Pour estimer les prix d'un magasin précis, on utilise le comparateur des supermarchés de l'UFC-Que Choisir, qui relève dans chaque magasin disposant d'un drive le prix d'un même panier d'une centaine de produits (marques nationales et marques de distributeur ; épicerie, fruits et légumes, crèmerie, boucherie, boissons, hygiène).

- **Magasins d'une zone** : tous les magasins listés par Que Choisir dans les départements frontaliers (74, 01, 39, 25, 68, 90) ; chaque adresse est géolocalisée (Nominatim, OpenStreetMap) et le magasin est rattaché à la zone la plus proche s'il se trouve à moins de 7 km de son centre ou, pour une zone qui regroupe plusieurs communes, de l'un des centres de ces communes.
- **Référence nationale (le « supermarché français moyen »)** : un panel de magasins tirés au hasard dans toute la France (tirage fixe, graine 2026 ; 168 magasins valides en octobre 2026), dont on prend la médiane du panier global. Ce panel sert uniquement d'étalon.
- **Indice du magasin** = panier global du magasin ÷ médiane du panel. Un indice de 0,92 signifie un magasin 8 % moins cher que le supermarché français moyen ; le site l'affiche ainsi.
- **Indice de la zone** = médiane des indices de ses magasins. Une zone sans magasin référencé utilise la moyenne française (indice 1).
- **Écart Suisse / magasin** pour une catégorie : (1 + écart Suisse / France) ÷ indice − 1.

En clair : si le caddie Que Choisir coûte 10 % de plus dans un magasin que dans le supermarché français moyen, on considère que vos courses y coûtent aussi 10 % de plus que les prix moyens français, puis on compare aux prix suisses.

Cette méthode suppose que l'écart d'un magasin à la moyenne est le même dans toutes les catégories ; c'est une approximation. Les données de Que Choisir leur appartiennent ; leur source est citée avec un lien vers leur comparateur. L'accord de l'UFC-Que Choisir pour cette publication n'a pas encore été demandé. Le paramètre `quechoisir.publier` de `config/panier.yaml` permet de les retirer du site public à tout moment.

### 3.7 Où faire le plein (v2.1)

Le mode « Où faire le plein » (page Essence) indique, depuis une localité suisse, la station qui fait le plus économiser, trajet compris, et la meilleure à moins de 5, 10 ou 20 km.

**Stations et prix.**
- **France** : toutes les stations de la bande frontalière (latitude 45,75° à 47,95°, longitude 5,55° à 7,65°), avec leur prix du jour issu du flux officiel (relevé quotidien). Un prix non mis à jour par la station depuis plus de 15 jours n'est pas utilisé. Le nom de la station vient d'OpenStreetMap (station la plus proche à moins de 150 m), sinon de la commune.
- **Suisse** : la liste des stations (environ 3 800) vient d'OpenStreetMap, mise à jour chaque mois. **Aucune source ouverte ne publie les prix station par station en Suisse** : la loi n'oblige pas les stations à les publier, et les bases existantes (TCS, Benzio, TankBillig, Fuelo) reposent sur des saisies d'utilisateurs et ne sont pas libres de réutilisation (les conditions du TCS limitent l'appli à un usage privé et non commercial). Le site n'utilise donc que des prix relevés pour lui (`data/prix_ch.yaml`) : relevés personnels ou signalés par des visiteurs, vérifiés avant ajout, publiés avec leur date et leur source. Un prix de plus de 14 jours est marqué « à confirmer » ; au-delà de 45 jours, il n'est plus utilisé. D'autres sources pourront être branchées avec l'accord de leur producteur.
- **Prix habituel** (référence) : par défaut, le prix moyen de la zone frontière suisse la plus proche publié chaque mois par l'OFDF (Genève, Bâle, Kreuzlingen, Tessin, Liechtenstein) ; l'utilisateur peut le remplacer par le prix de sa station.

**Distance.** Même base que le calculateur : coordonnées des localités (swisstopo) et itinéraires OSRM vers les 12 villes frontalières.
- Station française : itinéraire réel jusqu'à la ville frontalière la plus proche de la station, plus la distance entre cette ville et la station × facteur route ; si la ligne droite ne traverse pas de lac et donne une distance plus courte, c'est elle qui est retenue (ligne droite × facteur route).
- Station suisse : ligne droite × facteur route, doublée si la ligne droite traverse un lac.
- **Facteur route** : rapport médian entre la distance routière OSRM et la distance à vol d'oiseau, mesuré sur environ 7 000 trajets réels du site (1,39 en octobre 2026). **Vitesse moyenne** : médiane des mêmes trajets (environ 76 km/h). Ces deux valeurs sont recalculées à chaque publication.

**Gain net** = (prix habituel − prix de la station) × litres − carburant brûlé pour l'aller-retour (distance × 2 × consommation × prix habituel) − usure de la voiture (distance × 2 × 0,19 CHF/km, TCS 2026, option). Le temps de trajet est affiché mais n'est pas déduit. Seules les stations à moins de 90 km sont considérées.

**Réponses affichées.** (1) « Près de chez vous » : la station suisse la plus rentable dans le rayon choisi si un prix relevé existe ; sinon, les quatre stations suisses les plus proches (OpenStreetMap, sans les stations pour bateaux), avec un lien vers le radar du TCS pour voir leur prix et un lien pour signaler un prix. (2) « En France » : le détour n'est conseillé que s'il rapporte au moins 5 CHF et demande moins de 45 minutes de route aller ; sinon le site l'écrit et indique le gain ou la perte de la meilleure station française.

**Limites.** Les distances vers les stations suisses et vers les stations françaises éloignées des villes frontalières sont des estimations. La couverture suisse dépend des relevés reçus. L'Allemagne, l'Italie et l'Autriche ne sont pas encore couvertes station par station (leurs prix moyens frontaliers figurent dans le tableau OFDF de la page).

## 4. Calculs

**Change.** Les prix français sont convertis au taux de référence EUR/CHF de la Banque centrale européenne : moyenne mensuelle pour l'historique, dernier taux quotidien pour la photo du mois et l'essence.

**Écart.** Pour un produit : écart = prix suisse ÷ prix français en CHF − 1. Pour un panier : somme des prix suisses ÷ somme des prix français, chaque produit étant pondéré par sa quantité de référence `qty` (panier hebdomadaire d'un ménage de deux personnes). Un mois n'est calculé que si au moins 60 % des produits sont disponibles des deux côtés.

**Moyenne sur 12 mois.** Les fruits et légumes étant saisonniers, l'indicateur principal est la moyenne des écarts mensuels sur les 12 derniers mois.

**Pondération du panier (v2).** Le choix « Un peu de tout » pondère les quatre catégories selon la structure des dépenses alimentaires des ménages suisses, telle que mesurée par les pondérations de l'indice des prix à la consommation harmonisé (Eurostat, `prc_hicp_inw`, Suisse, 2025, en pour mille) :

| Catégorie | Postes COICOP | Poids (‰) | Part |
|---|---|---|---|
| Viande | 01.1.2 | 17,93 | 18,0 % |
| Fruits et légumes | 01.1.6, 01.1.7 | 20,57 | 20,6 % |
| Produits laitiers | 01.1.4, 01.1.5 | 18,30 | 18,4 % |
| Épicerie et marques | 01.1.1, 01.1.3, 01.1.8, 01.1.9, 01.2 | 42,92 | 43,0 % |

Les autres choix (« Viande », « Fruits et légumes », « Produits laitiers », « Épicerie et marques ») donnent 55 à 60 % du poids à la catégorie choisie et répartissent le reste. Si une catégorie n'a pas de chiffre un mois donné, les poids des autres sont renormalisés.

**Calculateur de trajet.** Les formules sont dans `site/calc.js` (navigateur) et `scraper/synthese.py` (pages générées) ; les deux versions sont comparées par les tests automatiques.

- taux d'économie = Σ poids × (1 − 1 ÷ (1 + écart de la catégorie ajusté par l'indice du magasin)) ;
- économie sur les courses = dépense × taux d'économie ;
- distance : calculée automatiquement entre le centre de la localité de départ (coordonnées swisstopo) et le centre de la zone de destination, itinéraire le plus rapide (OSRM sur OpenStreetMap) ; l'utilisateur peut la corriger ;
- énergie du trajet (v2) : voiture à essence ou diesel = distance aller-retour × consommation ÷ 100 × prix suisse du carburant correspondant (OFDF) ; voiture électrique = distance aller-retour × consommation (18 kWh/100 km par défaut) ÷ 100 × 0,28 CHF/kWh (TCS 2026) ; transports publics = prix du billet indiqué ;
- **usure de la voiture (v2, comptée par défaut)** = distance aller-retour × 0,19 CHF/km. Source : frais kilométriques TCS 2026, véhicule de référence : frais variables 4 135 CHF par an pour 15 000 km, soit 0,276 CHF/km, moins l'essence (5 L/100 km à 1,71 CHF, soit 0,086 CHF/km). L'utilisateur peut la décocher ;
- plein en France (option) = litres × (prix suisse − prix moyen de la zone, du jour) ;
- **frais de carte (option, v2)** = 1,5 % des achats en France, ordre de grandeur des frais de change d'une carte suisse classique ;
- TVA suisse : si les achats dépassent 150 CHF par personne, 2,6 % (taux réduit alimentaire) sur la totalité ;
- **droits de douane sur la viande (v2)** : quantité de viande estimée = poids de la viande × dépense en France ÷ prix moyen français de la viande au kilo ; au-delà de 1 kg par personne, 17 CHF par kg jusqu'à 10 kg d'excédent, 23 CHF au-delà (OFDF) ;
- **seuil de rentabilité (v2)** : montant de courses à partir duquel l'économie nette devient positive (recherche numérique entre 0 et 5 000 CHF), affiché avec la courbe de l'économie selon le montant ;
- **détaxe (v2, information)** : si les achats en France dépassent 100 €, TVA française maximale récupérable = achats × 5,5 ÷ 105,5 ; elle n'est pas ajoutée à l'économie, car l'opérateur garde une partie en frais et la détaxe exige un achat de plus de 100 € dans un même magasin ;
- temps : durée de trajet aller-retour (OSRM) plus 15 minutes forfaitaires de douane et de parking (v2), affichée à part comme coût d'opportunité (durée × valeur d'une heure, 25 CHF/h par défaut à titre d'exemple) ; elle n'est pas déduite de l'économie.

**Pages des zones (v2).** Pour chaque zone, l'économie est calculée depuis les villes suisses proches pour deux cas types : 150 CHF de courses pour 1 adulte et 300 CHF pour 2 adultes, « un peu de tout », voiture à essence 7 L/100 km, usure comprise, au niveau de prix du magasin du milieu.

## 5. Règles douanières rappelées (OFDF, 2026)

- Franchise de valeur : 150 CHF par personne et par jour ; au-delà, TVA suisse sur la totalité (2,6 % pour l'alimentation, 8,1 % pour le reste).
- Viande et préparations de viande (sans le gibier) : 1 kg ; au-delà 17 CHF/kg jusqu'à 10 kg, 23 CHF/kg au-delà.
- Beurre et crème : 1 kg ou 1 L ; au-delà 16 CHF par kg ou litre.
- Huiles, graisses, margarine : 5 kg ou 5 L ; au-delà 2 CHF.
- Boissons alcoolisées : 5 L jusqu'à 18 % vol. (au-delà 2 CHF/L), 1 L au-dessus (au-delà 15 CHF/L).
- Tabac : 250 cigarettes ou cigares, ou 250 g d'autres tabacs ; au-delà 0,25 CHF par cigarette.

Source : OFDF, brochure « Info douane : franchises de valeur et quantitatives ». Détaxe française : douane française, procédure PABLO (plus de 100 € TTC le même jour dans le même magasin, visa à la sortie de l'Union européenne).

## 6. Contrôles automatiques et valeurs de secours (v2)

À chaque relevé mensuel, `scraper/controles.py` vérifie les chiffres avant publication :

- **valeur manquante** (source inaccessible, produit introuvable) ou **échantillon trop petit** (viande : moins de 5 produits) : la valeur du mois précédent est reprise ; elle est marquée sur le site par la date de la valeur reprise ;
- **saut anormal** : un écart de prix qui varie de plus de 15 points d'un mois à l'autre est publié mais signalé ;
- **cohérence de l'essence** : le prix français du tableau OFDF doit être à moins de 10 % du flux officiel français ; une inversion essence / diesel est corrigée et signalée ;
- **magasins** : une zone qui perd plus de la moitié de ses magasins, ou une médiane du panel national qui bouge de plus de 10 %, est signalée ;
- **fraîcheur** : une série officielle en retard de plus de 3 mois est signalée.

Le rapport est publié (`data/controles.json`, page « Données ouvertes ») ; en cas d'alerte, le robot ouvre un ticket sur GitHub, ce qui prévient le responsable par e-mail. Des tests automatiques (`tests/`) vérifient les calculs clés (lecture du tableau OFDF, contrôles, formule d'économie, identité des calculs JavaScript et Python) avant chaque relevé et à chaque modification du code.

## 7. Baromètre mensuel (v2)

Chaque mois, les chiffres clés (écart viande, fruits et légumes sur 12 mois, produits laitiers, marques, plein de 50 L, change) sont figés dans `data/barometre/AAAA-MM.json` et publiés sur une page datée, avec la variation par rapport au mois précédent, un texte prêt à reprendre et une image. Ces pages ne sont jamais modifiées après le mois concerné.

## 8. Limites connues

- Les prix alimentaires français de base sont des moyennes nationales ; l'ajustement par magasin (§ 3.6) repose sur un indice global, pas sur des prix par produit.
- Les prix français des produits laitiers sont estimés (§ 3.2).
- La viande suisse provient d'une seule enseigne (Migros) ; l'ajustement de 5 % vers les discounters repose sur un seul test de prix (K-Tipp, 2025) et sera revu à chaque nouveau test publié.
- Côté français, Que Choisir ne couvre pas les discounters sans drive (Lidl, Aldi) : on compare un prix suisse de discounter à un supermarché français classique, ce qui tend à sous-estimer l'économie.
- Open Prices dépend des tickets partagés par ses contributeurs : certains produits ont peu de relevés.
- L'origine et la qualité des fruits et légumes ne sont pas contrôlées. Les promotions ne sont comptées ni en Suisse ni en France.
- L'usure de la voiture est un forfait moyen (TCS) ; la quantité de viande achetée est estimée à partir du budget.
- Les règles douanières sont rappelées à titre indicatif ; la règle officielle fait foi.

## 9. Historique des versions

**v2.1 (octobre 2026)** : mode « Où faire le plein » (stations françaises au prix du jour, stations suisses OpenStreetMap, prix suisses relevés, facteur route calibré sur les trajets réels, prise en compte des lacs).

**v2.0 (octobre 2026)**
- Correction de la lecture du tableau OFDF (essence 95 et diesel étaient inversés), contrôle automatique ajouté.
- Nouvelle catégorie produits laitiers et huile (5 produits, prix français estimés par indexation).
- Quatre marques de plus ; fenêtre Open Prices de 6 mois quand les relevés sont assez nombreux.
- Pondération « Un peu de tout » fondée sur les pondérations de l'indice des prix harmonisé suisse (Eurostat 2025), au lieu d'un choix forfaitaire.
- Calculateur : usure de la voiture (TCS), voiture diesel, électrique ou transports publics, frais de carte, droits de douane sur la viande, seuil de rentabilité avec courbe, information sur la détaxe, temps de douane, réglages gardés sur l'appareil, lien de partage.
- Contrôles de cohérence, valeurs de secours, alertes par ticket, tests automatiques.
- Essence relevée chaque jour ; nouvelle page Essence avec les cinq frontières suisses.
- Nouvelles pages : une par zone, baromètre mensuel, guide de la douane, données ouvertes, widget, à propos, mentions légales, confidentialité.
- Polices et scripts hébergés sur le site (aucun service tiers), image de partage, icône, plan du site.
- Zones regroupées : Divonne / Gex, Saint-Genis / Ferney.

**v1.4 (octobre 2026)** : viande ramenée au niveau des discounters (−5 %). **v1.3** : 12 zones. **v1.2** : magasins par zone (Que Choisir), toutes les localités suisses. **v1.0–1.1** : panier officiel, viande, marques, carburant.

## 10. Citer

> Brocard, G. (2026). *Panier Suisse France*, méthodologie v2.1. Données OFAG, INSEE, Eurostat, BCE, OFDF, TCS, Open Prices, UFC-Que Choisir. Code et données : https://github.com/GregBrocard/Panier-suisse-france

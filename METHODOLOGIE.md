# Méthodologie — Panier Suisse France

Version 3.1 · octobre 2026. Les versions précédentes restent consultables : [version 3.0](https://gregbrocard.github.io/Panier-suisse-france/v3/), [version 2](https://gregbrocard.github.io/Panier-suisse-france/v2/) et [version 1](https://gregbrocard.github.io/Panier-suisse-france/v1/) (branches `v3`, `v2` et `v1` du dépôt). Les changements sont listés à la section 9.

**En bref.**
0. **Le principe (v3.1)** : payer moins là où ça ne coûte rien aux paysans suisses. Le site distingue ce que la Suisse produit elle-même (viande, laitages et œufs, fruits et légumes) de ce qu'elle importe surtout (épicerie, huiles, boissons). Par défaut, le calculateur laisse les premiers en Suisse et ne compte en France que le reste ; l'utilisateur peut changer ce réglage. Les écarts de prix sont publiés sans les atténuer, avec ce que paie la différence (§ 3.9).
1. L'écart de prix entre la Suisse et la France, rayon par rayon, part de la **comparaison officielle des niveaux de prix** publiée par Eurostat avec l'Office fédéral de la statistique (dernière année disponible).
2. Il est mis à jour chaque mois avec le **taux de change du jour** et l'**évolution des prix mesurée par nos relevés** (fruits et légumes, produits laitiers).
3. Le calculateur l'ajuste au **supermarché suisse** que vous fréquentez (discounter, Migros ou Coop, test K-Tipp) et au **magasin français** choisi (indice UFC-Que Choisir).
4. Il retire le trajet (carburant, usure de la voiture), la TVA suisse au-delà de 150 CHF par personne et, en option, les frais de carte ; il ajoute le plein fait en France si vous le cochez.
5. Le temps passé est affiché à part, jamais déduit. Les droits de douane sur la viande sont signalés, pas déduits : en restant dans la franchise, on ne les paie pas.
6. Toutes les données et tout le code sont publics ; chaque chiffre peut être recalculé.

**Sommaire.** 1. Question posée · 2. Principe · 3. Sources et couches du panier (3.0 écart de référence, 3.1 fruits et légumes, 3.2 produits laitiers, 3.3 viande, 3.4 marques, 3.5 carburant, 3.6 magasins français, 3.7 supermarchés suisses, 3.8 où faire le plein, 3.9 origine des produits et choix suisse, 3.10 vente directe) · 4. Calculs · 5. Douane · 6. Contrôles · 7. Baromètre · 8. Limites · 9. Versions · 10. Citer

## 1. Question posée

Combien coûtent les mêmes courses du quotidien en Suisse et dans la France voisine, et à partir de quand le déplacement vaut-il la peine, une fois le trajet, l'usure de la voiture et la douane comptés ? Et depuis la v3.1 : sur quels produits l'économie ne coûte-t-elle rien aux producteurs suisses ?

- **Départ** : n'importe quelle localité de Suisse (répertoire officiel des localités de swisstopo, environ 4 100 localités).
- **Arrivée** : l'une des 12 zones françaises où les Suisses font couramment leurs courses (`config/destinations.yaml`) : Annemasse, Saint-Julien-en-Genevois, Saint-Genis / Ferney (avec Thoiry), Divonne / Gex (avec Segny), Thonon-les-Bains, Évian-les-Bains, Les Rousses, Jougne, Pontarlier, Morteau, Delle, Saint-Louis. Les communes voisines du Pays de Gex sont regroupées parce que, prises une à une, elles comptent trop peu de magasins référencés.

## 2. Principe : des sources publiques, vérifiables et automatisées

Le comparateur n'utilise que des données publiées ouvertement. Il ne contourne aucune protection technique de site marchand. Les enseignes dont le site bloque les robots (Coop, Aldi Suisse, Lidl Suisse, Denner, E.Leclerc, Carrefour, Intermarché, Super U) ne sont pas relevées directement.

Deux robots publics (GitHub Actions) tiennent le site à jour :

- **relevé mensuel**, le 20 de chaque mois : tous les prix, les magasins, les trajets ;
- **relevé quotidien de l'essence**, chaque matin : prix des stations françaises et taux de change du jour.

Chaque chiffre affiché peut être retrouvé dans les fichiers ouverts : `data/pli.json` (comparaison officielle de référence), `data/latest.json` (photo du mois), `data/series.json` (historique), `data/essence.json` (essence du jour), `data/releves/AAAA-MM.json` (archives des relevés), `data/barometre/AAAA-MM.json` (chiffres publiés chaque mois), `data/controles.json` (contrôles automatiques).

## 3. Sources et couches du panier

Le panier est défini dans `config/panier.yaml` (version 2). Le calculateur regroupe les produits en quatre catégories : viande, fruits et légumes, produits laitiers, épicerie et boissons.

### 3.0 Écart de référence : la comparaison officielle des niveaux de prix (nouveau en v3)

**Pourquoi.** Jusqu'à la version 2, l'écart de chaque rayon venait directement de nos relevés : une poignée de produits par rayon (quatre morceaux de viande, dix marques). Comparés à la statistique officielle, ces petits paniers s'en écartaient nettement (viande : +103 % chez nous contre +58 % pour Eurostat ; fruits et légumes : −2 % contre +15 %). Un petit échantillon n'est pas représentatif d'un rayon entier ; la statistique officielle, elle, compare des centaines de produits équivalents relevés dans tout le pays.

**Source.** Eurostat, indices de niveau des prix (`prc_ppp_ind`), programme Eurostat-OCDE des parités de pouvoir d'achat, auquel la Suisse participe par l'Office fédéral de la statistique. Indice UE27 = 100, à prix et taux de change de l'année. Dernière année publiée : 2024 (`data/pli.json`, relu à chaque relevé mensuel).

| Rayon du site (v3.1) | Postes Eurostat (poids dans l'indice suisse, ‰) | Écart officiel 2024 |
|---|---|---|
| Viande | Viande (17,93) | +57,7 % |
| Lait, fromage, œufs | Lait, fromage, œufs (15,80) | +53,3 % |
| Fruits, légumes, pommes de terre | Fruits, légumes, pommes de terre (20,57) | +14,9 % |
| Pain et céréales | Pain et céréales (16,71) | +44,9 % |
| Épicerie, huiles, boissons | Huiles et graisses (2,50) ; poisson (2,81) ; autres produits alimentaires (14,05) ; boissons sans alcool (9,35) | +54,5 % |

En v3.0, les huiles étaient comptées avec les produits laitiers et le pain avec l'épicerie ; la v3.1 les sépare pour distinguer ce que la Suisse produit de ce qu'elle importe.

Écart d'un rayon = Σ poids × indice Suisse ÷ Σ poids × indice France − 1.

**Mise à jour chaque mois.**

écart du mois = (1 + écart officiel) × effet de change × évolution relative − 1

- **effet de change** = taux EUR/CHF moyen de l'année de référence (BCE) ÷ taux du jour. Si le franc s'est apprécié depuis, les prix suisses exprimés en euros ont monté d'autant.
- **évolution relative** : comment le rapport entre prix suisses (CHF) et prix français (EUR) a évolué dans nos relevés depuis l'année de référence. Fruits et légumes : moyenne des 12 derniers mois (saisons) rapportée à la moyenne de l'année de référence. Produits laitiers : moyenne des 3 derniers mois. Viande et épicerie : nos relevés sont trop récents pour mesurer une évolution ; ces rayons ne suivent que le change.

Le détail (écart officiel, effet de change, évolution) est publié chaque mois (`data/ecarts_par_rayon.csv`, baromètre). Nos relevés par produit restent affichés tels quels, produit par produit : ils montrent des exemples concrets, l'écart de référence mesure le rayon.

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

France : INSEE (entrecôte de bœuf, escalope de veau, rôti de porc dans le filet, jambon supérieur). Suisse : relevé automatique du site Migros, **médiane** des produits correspondants au kilo, hors bio et hors promotion. Ces exemples sont publiés au prix Migros brut (v3) ; l'ajustement au supermarché suisse se fait désormais dans le calculateur pour tous les rayons (§ 3.7), et non plus par une réduction de 5 % propre à la viande.

Ces quatre morceaux sont parmi les plus chers en Suisse : leur écart (+100 % environ) dépasse nettement celui du rayon entier, qui comprend aussi la volaille, la charcuterie et la viande hachée. C'est pourquoi le calculateur utilise l'écart officiel du rayon (§ 3.0).

**Taille d'échantillon (v2)** : un morceau doit reposer sur au moins 5 produits Migros. Sinon, le prix suisse du mois précédent est repris et signalé sur le site (section 6).

La viande suisse et la viande vendue en moyenne en France ne sont pas toujours de même origine ni de même label ; la comparaison porte sur les prix réellement payés pour un même morceau.

### 3.4 Produits de marque identiques

Dix produits (v2 : quatre de plus) : Nutella, Coca-Cola (bouteille PET), Red Bull 25 cl, Pringles Original, Kinder Bueno, Lindt Excellence noir, Oreo Original, Mini Babybel, Evian 6 × 1,5 L, Barilla Pesto alla Genovese. Comparaison au **prix unitaire** (par kg ou par litre), pour neutraliser les différences de format.

- Suisse : Migros, produit de la même marque et de la même gamme, prix régulier. Les produits de marque coûtent pratiquement le même prix chez Migros et chez les discounters (relevé bonus.ch, août 2025) : pas d'ajustement.
- France : Open Prices (Open Food Facts), base ouverte de tickets de caisse : médiane des prix hors promotion relevés en France pour le code-barres indiqué, **sur 6 mois s'il y a au moins 10 relevés, sinon sur 12 mois** (v2). Le nombre de relevés et la fenêtre sont affichés ; sous 10 relevés, le chiffre est signalé comme indicatif.

Ces marques sont des exemples ; dans le calculateur, la catégorie « épicerie et boissons » utilise l'écart officiel (§ 3.0).

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
- **Écart Suisse / magasin** pour une catégorie : (1 + écart Suisse / France) × facteur du supermarché suisse ÷ indice − 1.
- Le calculateur affiche l'économie pour le magasin du milieu de la zone et, en dessous, la fourchette entre le magasin le moins cher et le plus cher de la zone.

En clair : si le caddie Que Choisir coûte 10 % de plus dans un magasin que dans le supermarché français moyen, on considère que vos courses y coûtent aussi 10 % de plus que les prix moyens français, puis on compare aux prix suisses.

Cette méthode suppose que l'écart d'un magasin à la moyenne est le même dans toutes les catégories ; c'est une approximation. Les données de Que Choisir leur appartiennent ; leur source est citée avec un lien vers leur comparateur. L'accord de l'UFC-Que Choisir pour cette publication n'a pas encore été demandé. Le paramètre `quechoisir.publier` de `config/panier.yaml` permet de les retirer du site public à tout moment.

### 3.7 Supermarché suisse de référence (nouveau en v3)

Les statistiques officielles sont des moyennes de tout le commerce suisse. Or l'écart avec la France dépend du magasin où l'on fait ses courses en Suisse. Le calculateur demande donc « Où faites-vous vos courses en Suisse ? » et applique un facteur tiré du dernier test de prix K-Tipp (août 2025, même panier de 100 produits courants dans chaque enseigne) :

| Choix | Panier K-Tipp | Facteur |
|---|---|---|
| Aldi ou Lidl (par défaut) | 230,94 et 232,83 CHF (moyenne 231,89) | 0,952 |
| Migros ou Denner (référence) | 243,54 CHF (Migros ; Denner n'est pas mesuré à part, il est rangé au niveau Migros par prudence) | 1,000 |
| Coop | 250,70 CHF | 1,029 |

Le facteur multiplie le prix suisse pour la viande, les fruits et légumes et les produits laitiers ; il ne s'applique pas à l'épicerie et aux boissons, où les produits de marque coûtent pratiquement le même prix dans toutes les enseignes (relevé bonus.ch, août 2025). On suppose que la moyenne officielle suisse est proche du niveau Migros, premier détaillant du pays ; c'est une approximation. Par défaut, le calculateur se place chez un discounter : c'est l'hypothèse la plus prudente (l'économie la plus faible) pour un ménage attentif aux prix. Les tests K-Tipp sont repris à chaque nouvelle publication.

### 3.8 Où faire le plein (v2.1)

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

### 3.9 Origine des produits et choix suisse (nouveau en v3.1)

**Classement des rayons.** Origine dominante pour le consommateur suisse, d'après les taux d'autosuffisance d'Agristat (2023) : lait et produits laitiers 113 %, viande 86 %, pommes de terre 69 %, œufs 57 %, céréales 47 %, légumes 44 %, huiles végétales 25 %, fruits 21 % (pommes et poires bien plus), café, cacao, riz, épices 0 %. D'où : viande, laitages et œufs, fruits et légumes = « produit surtout en Suisse » ; pain et céréales = « en partie suisse » ; épicerie, huiles, poisson, boissons sans alcool = « surtout importé ». Chaque produit relevé porte aussi une origine (« produit en Suisse », « suisse en saison », « importé ») ; un produit acheté dans un magasin suisse peut être importé : le site rappelle de lire l'étiquette.

**Ce que paie l'écart.** Page « Pourquoi c'est plus cher en Suisse » : règles d'élevage inscrites dans la loi (poules en cage interdites depuis 1991 ; effectifs maximaux : 18 000 poules pondeuses, 27 000 poulets, 1 500 porcs, 300 veaux d'engraissement ; transport des animaux limité à 6 heures de trajet et 8 heures en tout, LPA art. 15 et OPAn art. 152a ; part des animaux en programme SRPA), part du producteur dans le prix de vente (environ 30 centimes par franc, 34 à 42 selon le moniteur des prix FHNW pour Marchés équitables Suisse, 2024), concentration du commerce de détail (Coop et Migros, environ 80 % des ventes alimentaires des grandes enseignes, Nielsen 2025).

**Règle de neutralité.** Les écarts de prix sont publiés tels quels, sans les atténuer. Le site n'emploie pas l'impératif (« il faut ») ; il distingue ce que dit la loi de ce que disent les moyennes ; il ne porte aucun jugement sur une enseigne nommée ; il signale les sources de la filière (Proviande, Union suisse des paysans) comme telles ; le calcul « tout en France » reste toujours disponible. Aucun partenaire ne peut modifier un chiffre, une source ou un classement.

### 3.10 Vente directe (nouveau en v3.1)

La page « Acheter suisse moins cher » liste, autour d'une localité, les magasins à la ferme, distributeurs de produits de la ferme (lait, œufs, fromage, viande…), boucheries, fromageries, marchés et caves référencés dans OpenStreetMap (© contributeurs OpenStreetMap, licence ODbL), relevés chaque mois (`data/fermes_osm.json`). Distance : vol d'oiseau × facteur route (§ 3.8). Aucune source ne publie les prix de la vente directe : le site n'affirme donc pas qu'elle est moins chère ; des relevés datés pourront être ajoutés.

## 4. Calculs

**Change.** Les prix français sont convertis au taux de référence EUR/CHF de la Banque centrale européenne : moyenne mensuelle pour l'historique, dernier taux quotidien pour la photo du mois et l'essence.

**Écart.** Pour un produit : écart = prix suisse ÷ prix français en CHF − 1. Pour un panier : somme des prix suisses ÷ somme des prix français, chaque produit étant pondéré par sa quantité de référence `qty` (panier hebdomadaire d'un ménage de deux personnes). Un mois n'est calculé que si au moins 60 % des produits sont disponibles des deux côtés.

**Moyenne sur 12 mois.** Les fruits et légumes étant saisonniers, l'indicateur principal est la moyenne des écarts mensuels sur les 12 derniers mois.

**Pondération du panier (v3.1).** Le panier « un peu de tout » pondère les cinq rayons selon la structure des dépenses alimentaires des ménages suisses, telle que mesurée par les pondérations de l'indice des prix à la consommation harmonisé (Eurostat, `prc_hicp_inw`, Suisse, 2025, en pour mille) :

| Rayon | Postes COICOP | Poids (‰) | Part |
|---|---|---|---|
| Viande | 01.1.2 | 17,93 | 18,0 % |
| Lait, fromage, œufs | 01.1.4 | 15,80 | 15,8 % |
| Fruits, légumes, pommes de terre | 01.1.6, 01.1.7 | 20,57 | 20,6 % |
| Pain et céréales | 01.1.1 | 16,71 | 16,8 % |
| Épicerie, huiles, boissons | 01.1.3, 01.1.5, 01.1.8, 01.1.9, 01.2 | 28,71 | 28,8 % |

Les choix « Viande », « Fruits et légumes », etc. de la v3.0 sont remplacés par le réglage « Vous achetez suisse » (§ 3.9). Si un rayon n'a pas de chiffre un mois donné, les poids des autres sont renormalisés.

**Calculateur de trajet.** Les formules sont dans `site/calc.js` (navigateur) et `scraper/synthese.py` (pages générées) ; les deux versions sont comparées par les tests automatiques.

- **rayons achetés en Suisse (v3.1)** : la dépense indiquée est celle de toutes les courses ; la part des rayons cochés « Vous achetez suisse » (par défaut viande, laitages et œufs, fruits et légumes) reste en Suisse et n'entre pas dans le calcul ; seule la part restante est achetée en France ;
- taux d'économie sur la part achetée en France = Σ poids × (1 − 1 ÷ (1 + écart du rayon ajusté par le supermarché suisse et par l'indice du magasin français)), sur les seuls rayons achetés en France ;
- le résultat indique aussi ce que donnerait le cas « tout en France », et la différence entre les deux : c'est ce que coûte le choix suisse ;
- économie sur les courses = dépense × taux d'économie ;
- distance : calculée automatiquement entre le centre de la localité de départ (coordonnées swisstopo) et le centre de la zone de destination, itinéraire le plus rapide (OSRM sur OpenStreetMap) ; l'utilisateur peut la corriger ;
- énergie du trajet (v2) : voiture à essence ou diesel = distance aller-retour × consommation ÷ 100 × prix suisse du carburant correspondant (OFDF) ; voiture électrique = distance aller-retour × consommation (18 kWh/100 km par défaut) ÷ 100 × 0,28 CHF/kWh (TCS 2026) ; transports publics = prix du billet indiqué ;
- **usure de la voiture (v2, comptée par défaut)** = distance aller-retour × 0,19 CHF/km. Source : frais kilométriques TCS 2026, véhicule de référence : frais variables 4 135 CHF par an pour 15 000 km, soit 0,276 CHF/km, moins l'essence (5 L/100 km à 1,71 CHF, soit 0,086 CHF/km). L'utilisateur peut la décocher ;
- plein en France (option) = litres × (prix suisse − prix moyen de la zone, du jour) ;
- **frais de carte (option, v2)** = 1,5 % des achats en France, ordre de grandeur des frais de change d'une carte suisse classique ;
- TVA suisse : si les achats dépassent 150 CHF par personne, 2,6 % (taux réduit alimentaire) sur la totalité ;
- **droits de douane sur la viande (avertissement, v3)** : quantité de viande estimée = poids de la viande × dépense en France ÷ prix moyen français de la viande au kilo ; au-delà de 1 kg par personne, le site affiche un avertissement avec le montant qui serait dû (17 CHF par kg jusqu'à 10 kg d'excédent, 23 CHF au-delà, OFDF). Ce montant n'est plus déduit (il l'était en v2) : un acheteur informé reste dans la franchise ;
- **seuil de rentabilité (v2)** : montant de courses à partir duquel l'économie nette devient positive (recherche numérique entre 0 et 5 000 CHF), affiché avec la courbe de l'économie selon le montant ;
- **détaxe (v2, information)** : si les achats en France dépassent 100 €, TVA française maximale récupérable = achats × 5,5 ÷ 105,5 ; elle n'est pas ajoutée à l'économie, car l'opérateur garde une partie en frais et la détaxe exige un achat de plus de 100 € dans un même magasin ;
- temps : durée de trajet aller-retour (OSRM) plus 15 minutes forfaitaires de douane et de parking (v2), affichée à part comme coût d'opportunité (durée × valeur d'une heure, 25 CHF/h par défaut à titre d'exemple) ; elle n'est pas déduite de l'économie.

**Pages des zones (v3.1).** Pour chaque zone, l'économie est calculée depuis les villes suisses proches pour 300 CHF de courses, 2 adultes, dans deux cas : viande, laitages et fruits et légumes achetés en Suisse, ou tout acheté en France ; « un peu de tout », voiture à essence 7 L/100 km, usure comprise, au niveau de prix du magasin du milieu, courses suisses chez un discounter.

**Chiffres d'accueil (v3.1).** « Ce que la Suisse importe coûte X % de moins en France ; ce qu'elle produit y est Y % plus cher » : X et Y sont calculés comme ci-dessous sur les rayons d'origine « import » (épicerie, huiles, boissons) et « suisse » (viande, laitages et œufs, fruits et légumes). Le pain, d'origine mixte, n'entre dans aucun des deux.

**Chiffre d'accueil (v3).** « En moyenne, les mêmes courses coûtent X % de moins en France, avant trajet » : X = Σ poids × (1 − 1 ÷ (1 + écart de référence du rayon)), avec les poids « Un peu de tout », au niveau de la moyenne suisse (Migros) et du supermarché français moyen. Le calculateur, lui, part par défaut d'un discounter suisse et donne donc une économie un peu plus faible.

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

Chaque mois, les chiffres clés (économie totale, écarts de référence par rayon avec leur décomposition, écarts de nos relevés, plein de 50 L, change ; version 3 du format depuis octobre 2026) sont figés dans `data/barometre/AAAA-MM.json` et publiés sur une page datée, avec la variation par rapport au mois précédent, un texte prêt à reprendre et une image. Ces pages ne sont jamais modifiées après le mois concerné.

## 8. Limites connues

- Les prix alimentaires français de base sont des moyennes nationales ; l'ajustement par magasin (§ 3.6) repose sur un indice global, pas sur des prix par produit.
- Les prix français des produits laitiers sont estimés (§ 3.2).
- L'écart de référence date de la dernière année publiée par Eurostat (2024 en octobre 2026) ; sa mise à jour mensuelle ne suit que le change pour la viande et l'épicerie.
- Les facteurs de supermarché suisse reposent sur un seul test de prix (K-Tipp, 2025) et sont appliqués de la même façon à quatre rayons (pas à l'épicerie).
- Les exemples de viande suisse proviennent d'une seule enseigne (Migros).
- Côté français, Que Choisir ne couvre pas les discounters sans drive (Lidl, Aldi) : on compare un prix suisse de discounter à un supermarché français classique, ce qui tend à sous-estimer l'économie.
- Open Prices dépend des tickets partagés par ses contributeurs : certains produits ont peu de relevés.
- L'origine et la qualité des fruits et légumes ne sont pas contrôlées. Les promotions ne sont comptées ni en Suisse ni en France.
- L'usure de la voiture est un forfait moyen (TCS) ; la quantité de viande achetée est estimée à partir du budget.
- Les règles douanières sont rappelées à titre indicatif ; la règle officielle fait foi.
- Le classement par origine porte sur des rayons entiers : un produit précis peut être importé dans un rayon « suisse », et inversement. Les fruits et légumes suisses ne le sont qu'en saison.
- Les comparaisons de règles d'élevage portent sur la loi et les moyennes ; elles ne disent rien d'une exploitation ou d'un label précis. À qualité égale (labels français), l'écart de prix est plus faible.
- La liste des points de vente directe dépend des contributeurs d'OpenStreetMap ; ses prix ne sont pas connus.

## 9. Historique des versions

**v3.1 (octobre 2026)** : nouveau principe « payer moins là où ça ne coûte rien aux paysans suisses ». Cinq rayons au lieu de quatre (pain et huiles séparés) ; origine de chaque rayon et produit ; réglage « Vous achetez suisse » dans le calculateur (viande, laitages et œufs, fruits et légumes cochés par défaut) avec comparaison au cas « tout en France » ; pages « Pourquoi c'est plus cher en Suisse » et « Acheter suisse moins cher » (points de vente directe OpenStreetMap) ; chiffres d'accueil, baromètre, images de partage et pages des zones selon l'origine ; questions fréquentes sur les paysans et la viande.

**v3.0 (octobre 2026)**
- Écart par rayon ancré sur la comparaison officielle des niveaux de prix (Eurostat–OFS), mis à jour chaque mois par le change et l'évolution de nos relevés (§ 3.0). Chiffre d'accueil unique : l'économie moyenne sur les mêmes courses.
- Choix du supermarché suisse dans le calculateur (K-Tipp), discounter par défaut ; fin de la réduction de 5 % propre à la viande.
- Droits de douane sur la viande : avertissement au lieu d'une déduction. Fourchette d'économie selon le magasin français.
- Nouvelles pages : prix par produit (une page par produit, historique), supermarchés suisses, partenaires ; questions fréquentes sur l'accueil.
- Exports tableur (CSV), aperçu du widget, baromètre au nouveau format, images de partage avec l'économie totale.
- Tableaux lisibles sur téléphone, graphiques chargés seulement quand on les affiche (page d’accueil allégée de 40 %).

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

> Brocard, G. (2026). *Panier Suisse France*, méthodologie v3.1. Données Eurostat–OFS, Agristat, OFAG, OSAV, INSEE, BCE, OFDF, TCS, K-Tipp, Open Prices, OpenStreetMap, UFC-Que Choisir. Code et données : https://github.com/GregBrocard/Panier-suisse-france

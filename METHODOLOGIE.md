# Méthodologie — Comparateur de panier Suisse / France

Version 1 · octobre 2026

## 1. Question posée

Combien coûte le même panier de courses du quotidien en Suisse et dans la France voisine, et à partir de quand le déplacement vaut-il la peine ?

Le comparateur répond pour trois passages frontaliers de Suisse romande :

| Zone | Côté suisse | Côté français |
|---|---|---|
| Genève ↔ Annemasse | prix nationaux des chaînes suisses | E.Leclerc Drive Ville-la-Grand (Annemasse) |
| Nyon ↔ Divonne / La Cure | prix nationaux des chaînes suisses | E.Leclerc Drive du Pays de Gex |
| Vallorbe ↔ Jougne / Pontarlier | prix nationaux des chaînes suisses | E.Leclerc Drive Pontarlier |

## 2. Le panier : des besoins, pas des produits

Le panier n'est ni « suisse » ni « français ». Chaque ligne décrit un **besoin** défini de façon neutre, par exemple « 1 L de lait UHT demi-écrémé » ou « 500 g de viande hachée de bœuf ». Dans chaque enseigne, on retient le produit qui remplit ce besoin selon des règles écrites à l'avance (fichier `config/basket.yaml`), puis on ramène son prix à l'unité (par kg, par litre ou par pièce).

Cela évite deux biais fréquents :
- partir d'une liste de produits suisses (on pénalise la France, où ces produits n'existent pas) ;
- comparer des formats différents (un pot de 600 g contre un de 750 g).

Le panier compte 25 lignes, regroupées en deux sous-paniers :

**Panier « premier prix » (20 besoins).** Laitier, épicerie, viande, fruits et légumes, ménage. Pour chaque besoin, on retient dans chaque enseigne **le produit valide au prix unitaire le plus bas**, marques de distributeur comprises. C'est le panier de quelqu'un qui cherche à dépenser le moins possible, des deux côtés de la frontière.

**Panier « marques » (5 produits).** Nutella 750 g, Coca-Cola 1,5 L, Barilla Spaghetti n°5 500 g, Evian 1,5 L, Kellogg's Corn Flakes. Ce sont des produits identiques vendus des deux côtés : la comparaison y est pure, sans débat sur la qualité.

Chaque besoin a une **quantité de référence** (`ref_qty`) correspondant à un achat courant (2 L de lait, 250 g de beurre, 10 œufs…). Le total du panier est la somme des quantités de référence multipliées par les prix unitaires. Il représente environ un panier hebdomadaire pour un ménage d'une ou deux personnes.

## 3. Règles de sélection d'un produit

Pour qu'un produit soit retenu pour un besoin, il doit :
1. contenir les mots obligatoires du besoin (ex. « poulet » et « filet » ou « émincé ») ;
2. ne contenir aucun mot exclu (ex. « bio », « pané », « mariné ») ;
3. avoir un conditionnement compris dans les bornes du besoin (ex. 0,2 à 2 kg).

Les produits **bio** sont exclus partout, pour comparer des gammes équivalentes. Les **multipacks** hors bornes sont écartés : on compare un conditionnement unitaire courant.

Parmi les produits valides, on retient le moins cher au prix unitaire, **hors promotion** quand un prix régulier existe. Les promotions faussent une comparaison mensuelle : un relevé tombé un jour de promo ne dit rien du prix habituel.

## 4. Panier moyen et panier le moins cher

Pour chaque zone et chaque besoin :
- **moyenne** : moyenne des prix des enseignes du pays qui proposent ce besoin ;
- **minimum** : prix de l'enseigne la moins chère du pays.

Le chiffre principal affiché est la **moyenne** (le panier « typique »). Le minimum est affiché en détail.

Un besoin n'entre dans le total d'une zone que s'il a été trouvé **des deux côtés**. Le nombre de besoins effectivement comparés est toujours indiqué à côté du total.

## 5. Change

Les prix français sont convertis en francs au **taux de référence de la Banque centrale européenne** (EUR/CHF) du jour du relevé. C'est un taux interbancaire : le taux réellement obtenu dépend de la carte ou du compte utilisé (souvent 0,5 à 2 % moins favorable).

## 6. Sources et fréquence

Les prix sont relevés automatiquement **une fois par mois** (le 2), sur les sites publics des enseignes :
- Suisse : Coop, Migros, Lidl Suisse, Aldi Suisse (prix nationaux, valables dans les trois zones) ;
- France : E.Leclerc Drive, un magasin par zone (les prix varient d'un magasin à l'autre).

Chaque relevé est archivé avec, pour chaque ligne, le nom exact du produit retenu, son prix, son conditionnement et l'URL de la page source (`data/releves/AAAA-MM.json`). L'historique résumé est dans `data/history.json`.

Le code de relevé est public et versionné. Toute modification du panier incrémente `basket_version` ; une rupture de série est alors signalée sur le graphique.

## 7. Le déplacement

Le calculateur estime le coût du trajet aller-retour :

coût = distance aller-retour (km) × consommation (L/100 km) ÷ 100 × prix du carburant (CHF/L)

L'économie nette est la différence de prix du panier moins ce coût. Le **seuil de rentabilité** est le montant de courses à partir duquel l'économie couvre le trajet. Le temps passé et l'usure du véhicule ne sont pas comptés ; ils sont mentionnés à titre indicatif.

## 8. Règles douanières rappelées

Pour les achats rapportés en Suisse pour un usage privé (source : OFDF, ch.ch) :
- franchise de valeur : 150 CHF par personne et par jour ; au-delà, la TVA suisse est due sur la **totalité** du montant ;
- viande : 1 kg par personne et par jour en franchise ; au-delà, droits de douane sur l'excédent ;
- alcool : 5 L sous 18 % vol., 1 L au-dessus ; tabac : 250 cigarettes.

## 9. Limites connues

- Un seul drive par zone côté français : un hypermarché n'est pas représentatif de tous les commerces de la zone. Lidl France ne publie pas ses prix alimentaires en ligne et n'est donc pas relevé.
- Les prix en ligne des drives peuvent différer légèrement des prix en rayon.
- Les fruits, légumes et la viande varient selon la saison et l'origine ; l'origine n'est pas contrôlée.
- La sélection automatique peut retenir un produit imparfait. Chaque ligne étant tracée avec son URL, les erreurs sont vérifiables et corrigeables.
- Le panier pondère chaque besoin par une quantité forfaitaire, pas par la structure de consommation réelle d'un ménage (pondération de l'IPC de l'OFS envisagée dans une version ultérieure).

## 10. Citer

> Comparateur de panier Suisse / France, méthodologie v1 (octobre 2026). Relevés mensuels automatisés, code et données : github.com/<compte>/panier-suisse-france.

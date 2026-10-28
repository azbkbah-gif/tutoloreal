view: +order_items {
  measure: total_ca {
    description: "Chiffre d'affaires brut HT, toutes lignes de commande y compris annulés et retournées. Synonymes : CA brut, ventes, revenue."
  }
  measure: ca_net {
    description: "Chiffres d'affaires net HT, hors commandes annulés et retournées, Mesure à privilégier pour toute question sur le CA ou les ventes. Synonymes : CA, chiffre d'affaires, ventes nettes."
  }
  measure: panier_moyen {
    description: "Montant moyen d'une commande HT (CA net / nombre de commandes Synonymes : panier, AOV, valeur moyenne de commande.)"
  }
  dimension: status {
    description: "Statut de la ligne : Complete, Shipped, Processing, Cancelled, Returned."
  }
  measure: taux_marge {
    description: "Marge brute / CA net, en pourcentage. Synonymes : marge, taux de marge, rentabilité."
  }
  measure: marge_brute {
    label: "Marge brute"
    description: "CA net moins coût de revient des produits vendus"
    type: sum
    sql: ${marge_ligne} ;;
    filters: [status: "-Cancelled,-Returned"]
    value_format_name: eur
  }
}

view: +products {
  dimension: department {
    hidden: yes
  }
  dimension: category {
    description: "Catégorie de produit : Soins du visage, Maquillage, Parfums, Capillaire, Corps, Homme. Synonymes : famille, univers, rayon, type de produit."
  }
}

view: +users {
  dimension: country {
    description: "Pays de résidence du client. Synonymes : pays, marché, zone, géographie."
  }
    dimension: age_tier {
    description: "Tranche d'âge du client. Valeurs possibles : Below 18, 18 to 24, 25 to 34, 35 to 44, 45 to 54, 55 to 64, 65 or Above. Synonymes : âge, génération, 25-34 ans."
  }
}

explore: ventes_ia {
  from: order_items
  view_name: order_items
  label: "Ventes  (Agent IA)"
  description: "Explore réservé au compagnon IA : CA, commandes et panier par catégorie, marque, pays et date."

  join: products {
    sql_on: ${order_items.product_id} = {products.id} ;;
    relationship: many_to_one
  }
  join: users {
    sql_on: ${order_items.user_id} = ${users.id} ;;
    relationship: many_to_one
  }

  # Champs visibles par l'agent + leurs dépendances techniques (masquées par hidden: yes)
  fields: [
    order_items.sale_price,
    order_items.order_id,
    users.age,
    order_items.created_date,
    order_items.created_month,
    order_items.created_year,
    order_items.status,
    order_items.ca_net,
    order_items.total_ca,
    order_items.nb_commandes,
    order_items.panier_moyen,
    order_items.taux_marge,
    order_items.marge_brute,
    order_items.marge_ligne,
    products.cost,
    products.category,
    products.brand,
    users.country,
    users.age_tier
  ]

}
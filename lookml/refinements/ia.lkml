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
}

view: +products {
  dimension: department {
    hidden: yes
  }
}

explore: ventes_ia {
  from: order_items
  view_name: order_items
  label: "Ventes  (Agent IA)"
  description: "Explore réservé au compagnon IA : CA, commandes et panier par catégorie, marque, pays et date."

  join: products {
    sql_on: ${order_items.product_id} = $ {products.id} ;;
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
    products.category,
    products.brand,
    users.country,
    users.age_tier
  ]

}
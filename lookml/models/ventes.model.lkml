connection: "formation_bbigquery"

include: "/views/*.view.lkml"
include: "/refinemnts/*.lkml"


datagroup: quotidien {
  sql_trigger: SELECT CURRENT_DATE() ;;
  max_cache_age: "24 hours"
}

persist_with: quotidien 

explore: order_items {
  label: "Ventes"
  description: "Analyse des ventes par produits, client, pays et date"

  join: orders {
    type: left_outer
    sql_on: $ {order_items.order_id} = ${orders.order_id} ;;
    relationship: many_to_one
  }
  join: products {
    type: left_outer
    sql_on: $ {order_items.product_id} = ${products.id} ;;
    relationship: many_to_one
  }
  join: users {
    type: left_outer
    sql_on: ${order_items.user_id} = ${users.id}  ;;
    relationship: many_to_one
  }
}
test: ca_net_positif {
  explore_source: order_items {
    column: ca_net {field: order_items.ca_net}

  }
  assert: ca_net_superieur_a_zero {
    expression: ${order_items.ca_net} >= 0 ;;
  }
}
test: commandes_2025_superieures_a_10000 {
  explore_source: order_items {
    column: nb_commandes { field: order_items.nb_commandes }
    filters: [order_items.created_year: "2025"]
  }
  assert: plus_de_10000_commandes {
    expression: ${order_items.nb_commandes} > 10000 ;;
  }
}
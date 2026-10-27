view: orders {
  sql_table_name: `@{projet_gcp}.@{dataset}.orders` ;;

  dimension: order_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.order_id ;;
    hidden: yes
  }

  dimension: status {
    label: "Statut de la commande"
    type: string
    sql: ${TABLE}.status ;;
  }
  dimension: num_of_item {
    label: "Nombre d'articles"
    type: number
    sql: ${TABLE}.num_of_item ;;
  }
  dimension_group: created {
    label: "Commande"
    type: time
    timeframes: [raw, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
  }
    dimension_group: livraison {
    label: "Délai de livraison"
    type: duration
    intervals: [hour, day]
    sql_start: ${TABLE}.created_at ;;
    sql_end: ${TABLE}.delivered_at ;;
  }
  measure: nb_commandes {
    label: "Nombre de commandes"
    type: count
  }
  measure: delai_livraison_moyen {
    label: "Delai moyen de livraison (jours)"
    type: average
    sql: ${days_livraison} ;;
    value_format_name: decimal_1
  }
    dimension: est_livree {
    label: "Commande livrée"
    type: yesno
    sql: ${TABLE}.delivered_at IS NOT NULL ;;
  }
}
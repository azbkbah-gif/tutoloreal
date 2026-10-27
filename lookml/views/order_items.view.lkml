view: order_items {
  sql_table_name: `@{projet_gcp}.@{dataset}.order_items` ;;

  dimension: order_item_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
    hidden: yes
  }
  dimension: order_id {
    type: number
    sql: ${TABLE}.order_id ;;
    hidden: yes   
  }
  dimension: user_id {
    type: number
    sql: ${TABLE}.user_id ;;
    hidden: yes   
  }
  dimension: product_id {
    type: number
    sql: ${TABLE}.product_id ;;
    hidden: yes
  }
  dimension: status {
    label: "Statut de la ligne"
    type: string
    sql: ${TABLE}.status ;;
  }
  dimension_group: created {
    label: "Vente"
    type: time
    timeframes: [raw, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
  }
  dimension: sale_price {
    label: "Prix de vente"
    type: number
    sql: ${TABLE}.sale_price ;;
    value_format_name: euro_2
    hidden: yes
  }
  dimension: marge_ligne {
    type: number
    sql: ${sale_price} - {products.cost} ;;
    hidden: yes
  }
  measure: total_ca {
    label: "Chiffre d'affaires"
    description: "Somme des prix de ventes HT, tous status confondus"
    type: sum
    sql: ${sale_price} ;;
    value_format_name: euro_2
  }
  measure: ca_net {
    label: "CA net"
    description: "CA HT hors commandes annulés et retournées"
    type: sum
    sql: ${sale_price} ;;
    filters: [status: "-cancelled", status: "-returned"]
    value_format_name: euro_2
  }
  measure: nb_commandes {
    label: "Nombre de commandes"
    type: count_distinct
    sql: ${order_id} ;;
  }
  measure: nb_artcles {
    label: "Nombres d'articles vendus"
    type: count
    sql: ${order_item_id} ;;
  }
  measure: panier_moyen {
    label: "Panier moyen"
    description: " CA net divisé par le nombre de commandes"
    type: number
    sql: ${ca_net} / NULLIF(${nb_commandes}, 0) ;;
    value_format_name: euro_2
  }
  measure: taux_retour {
    label: "Taux retour"
    type: number
    sql: 1.0 * COUNT(CASE WHEN ${status} = 'Retourned' THEN 1 END) / NULLIF(COUNT(*), 0) ;;
    value_format_name: percent_1
  }
}

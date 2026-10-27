view: products {
  sql_table_name: `@{projet_gcp}.@{dataset}.products` ;;

  dimension: id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
    hidden: yes
  }
  dimension: name {
    label: "Nom du produit"
    type: string
    sql: ${TABLE}.name ;;
  }
  dimension: brand {
    label: "Marque"
    type: string
    sql: ${TABLE}.brand ;;
  }
  dimension: category {
    label: "Catégorie"
    type: string
    sql: ${TABLE}.category ;;
  }
  dimension: department {
    label: "Département"
    type: string
    sql: ${TABLE}.department ;;
  }
  dimension: retail_price {
    label: "Prix catalogue"
    type: number
    sql: ${TABLE}.retail_price ;;
    value_format_name: euro_2
  }
  dimension: cost {
    label: "Cout de revient"
    type: number
    sql: ${TABLE}.cost ;;
    value_format_name: euro_2
    hidden: yes
  }
  dimension: price_tier {
    label: "Game de prix"
    type: tier
    tiers: [20,50, 100]
    style: integer
    sql: ${retail_price} ;;
  }

  measure: nb_produits {
    label: "Nombre de produits"
    type: count
  }
  
}
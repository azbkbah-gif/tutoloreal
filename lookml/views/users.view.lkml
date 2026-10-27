view: users {
  sql_table_name: `@{projet_gcp}.@{dataset}.users` ;;

  dimension: id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
    hidden: yes
  }
  dimension: full_name {
    label: "Nom du client"
    type: string
    sql: ${TABLE}.first_name + " " + ${TABLE}.last_name ;;
  }
  dimension: email{
    type: string
    sql: ${TABLE}.email ;;
    hidden: yes
  }
  dimension: age {
    label: "Âge"
    type: number
    sql: ${TABLE}.age ;;
  }
  dimension: age_tier {
    label: "Tranche d'âge"
    type: tier
    tiers: [0, 18, 25, 35, 45, 55, 65]
    style: integer
    sql: ${age} ;;
  }
  dimension: gender {
    label: "Genre"
    type: string
    sql: ${TABLE}.gender ;;
  }
  dimension: country {
    label: "Pays"
    type: string
    sql: ${TABLE}.country ;;
  }
  dimension: city {
    label: "Ville"
    type: string
    sql: ${TABLE}.city ;;
 }

 dimension: traffic_source {
    label: "Source d'aquisition"
    type: string
    sql: ${TABLE}.traffic_source ;;
  }

  dimension_group: created {
    label: "Inscription"
    type: time
    timeframes: [raw, date, month, year]
    sql: ${TABLE}.created_at ;;
  }
  measure: nb_clients {
    label: "Nombre de clients"
    type: count_distinct
    sql: ${id} ;;
  }
}
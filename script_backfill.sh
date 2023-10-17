DAG_ID="electricity_parent_id_agg"
START_DATE=2022-05-25T00:00:00Z
END_DATE=2022-05-25T01:00:00Z
airflow dags backfill $DAG_ID --start-date=$START_DATE --end-date=$END_DATE
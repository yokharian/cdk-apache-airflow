kill "$(ps -ef | grep "airflow webserver"| awk '{print $2}')"
kill "$(ps -ef | grep "airflow scheduler"| awk '{print $2}')"
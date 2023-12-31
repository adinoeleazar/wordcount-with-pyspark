# [START composer_pyspark_tutorial]
"""Example Airflow DAG that creates a Cloud Dataproc cluster, runs the PySpark
wordcount example, and deletes the cluster.
This DAG relies on three Airflow variables
https://airflow.apache.org/concepts.html#variables
* gcp_project - Google Cloud Project to use for the Cloud Dataproc cluster.
* gce_zone - Google Compute Engine zone where Cloud Dataproc cluster should be
  created.
* gcs_bucket - Google Cloud Storage bucket to use for result of PySpark job.
  See https://cloud.google.com/storage/docs/creating-buckets for creating a
  bucket.
"""
import datetime
import os
from airflow import models
from airflow.contrib.operators import dataproc_operator
from airflow.utils import trigger_rule

# Output file for Cloud Dataproc job.
output_file = os.path.join(
    models.Variable.get('gcs_bucket'), 'wordcount',
    datetime.datetime.now().strftime('%Y%m%d-%H%M%S')) + os.sep

# Path to spark wordcount example jar file in created gcs_bucket.
WORDCOUNT_JAR = (
    'gs://gcs_bucket/spark-examples_2.9.2-0.7.0-sources.jar'
)

# Arguments to pass to Cloud Dataproc job.
input_file = 'gs://pub/shakespeare/rose.txt'
wordcount_args = ['wordcount', input_file, output_file]
yesterday = datetime.datetime.combine(
    datetime.datetime.today() - datetime.timedelta(1),
    datetime.datetime.min.time())
default_dag_args = {
    # Setting start date as yesterday starts the DAG immediately when it is
    # detected in the Cloud Storage bucket.
    'start_date': yesterday,
    # To email on failure or retry set 'email' arg to your email and enable
    # emailing here.
    'email_on_failure': False,
    'email_on_retry': False,
    # If a task fails, retry it once after waiting at least 5 minutes
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=5),
    'project_id': models.Variable.get('gcp_project')
}

# [START composer_pyspark_schedule]
with models.DAG(
        'composer_pyspark_tutorial',
        # Continue to run DAG once per day
        schedule_interval=datetime.timedelta(days=1),
        default_args=default_dag_args) as dag:
    # [END composer_pyspark_schedule]

    # Create a Cloud Dataproc cluster.
    create_dataproc_cluster = dataproc_operator.DataprocClusterCreateOperator(
        task_id='create_dataproc_cluster',
        # Give the cluster a unique name by appending the date scheduled.
        # See https://airflow.apache.org/code.html#default-variables
        cluster_name='composer-pyspark-tutorial-cluster-{{ ds_nodash }}',
        num_workers=2,
        region='place_holder_text',
        zone=models.Variable.get('gce_zone'),
        image_version='2.0',
        master_machine_type='e2-standard-2',
        worker_machine_type='e2-standard-2')
    
    # Run the PySpark wordcount example installed on the Cloud Dataproc cluster
    # master node.
    run_dataproc_pyspark = dataproc_operator.DataProcPySparkOperator(
        task_id='run_dataproc_pyspark',
        region='place_holder_text',
        main=WORDCOUNT_JAR,
        cluster_name='composer-pyspark-tutorial-cluster-{{ ds_nodash }}',
        arguments=wordcount_args)
    
    # Delete Cloud Dataproc cluster.
    delete_dataproc_cluster = dataproc_operator.DataprocClusterDeleteOperator(
        task_id='delete_dataproc_cluster',
        region='place_holder_text',
        cluster_name='composer-pyspark-tutorial-cluster-{{ ds_nodash }}',
        # Setting trigger_rule to ALL_DONE causes the cluster to be deleted
        # even if the Dataproc job fails.
        trigger_rule=trigger_rule.TriggerRule.ALL_DONE)
    
    # [START composer_pyspark_steps]
    # Define DAG dependencies.
    create_dataproc_cluster >> run_dataproc_pyspark >> delete_dataproc_cluster

    # [END composer_pyspark_steps]
# [END composer_pyspark_tutorial]
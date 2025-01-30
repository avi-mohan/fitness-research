from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os

# Define default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'fitness_research_pipeline',
    default_args=default_args,
    description='Pipeline to process fitness research papers',
    schedule_interval=timedelta(days=1),
)

def check_papers_folder(**context):
    """Check if our papers folder exists and has PDFs"""
    papers_dir = '/opt/airflow/documents/papers'
    if not os.path.exists(papers_dir):
        print(f"Creating papers directory at {papers_dir}")
        os.makedirs(papers_dir)
    
    pdfs = [f for f in os.listdir(papers_dir) if f.endswith('.pdf')]
    print(f"Found {len(pdfs)} PDF files")
    return len(pdfs)

# Define tasks
check_folder = PythonOperator(
    task_id='check_papers_folder',
    python_callable=check_papers_folder,
    dag=dag,
)
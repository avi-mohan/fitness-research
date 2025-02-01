from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import PyPDF2

from airflow.models.dagrun import DagRun
from airflow.utils.dates import days_ago


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

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
    print(f"Found {len(pdfs)} PDF files: {pdfs}")
    return len(pdfs)

def extract_text_from_pdf(**context):
    """Extract and process text from squat biomechanics PDF"""
    papers_dir = '/opt/airflow/documents/papers'
    pdf_path = os.path.join(papers_dir, 'squat_biomechanics.pdf')
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
                
            # Log some interesting findings
            if "collegiate" in text.lower():
                print("Found information about collegiate lifters")
            if "biomechanical" in text.lower():
                print("Found biomechanical analysis")
                
            print(f"Successfully processed {len(reader.pages)} pages")
            return text
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        raise

# Define tasks
check_folder = PythonOperator(
    task_id='check_papers_folder',
    python_callable=check_papers_folder,
    dag=dag,
)

extract_text = PythonOperator(
    task_id='extract_text',
    python_callable=extract_text_from_pdf,
    dag=dag,
)

# Set task dependencies
check_folder >> extract_text

dag = dag

if __name__ == "__main__":
    dag.test()
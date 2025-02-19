# Standard library imports
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import uuid
from typing import List, Dict

# We import PyPDF2 at the module level since it's a lightweight library
# and is essential for the DAG to function
import PyPDF2

def get_weaviate_client():
    """
    Create and return a Weaviate client.
    We import weaviate inside the function to avoid DAG loading issues.
    """
    import weaviate
    return weaviate.Client(
        url="http://weaviate:8080",  # URL where Weaviate is running in Docker
    )

def init_weaviate_schema():
    """
    Initialize the Weaviate schema for storing research paper chunks.
    Creates a ResearchPaper class if it doesn't exist.
    """
    # Import inside function to avoid DAG loading issues
    import weaviate
    client = get_weaviate_client()
    
    # Define the schema for research papers
    schema = {
        "classes": [{
            "class": "ResearchPaper",
            "description": "A research paper about fitness and exercise science",
            "vectorizer": "none",  # We'll provide our own vectors
            "properties": [
                {
                    "name": "title",
                    "dataType": ["string"],
                    "description": "Title of the paper",
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Content chunk from the paper",
                },
                {
                    "name": "page_number",
                    "dataType": ["int"],
                    "description": "Page number of the chunk",
                },
                {
                    "name": "filename",
                    "dataType": ["string"],
                    "description": "Source PDF filename",
                }
            ],
        }]
    }
    
    # Create schema if it doesn't exist
    if not client.schema.exists("ResearchPaper"):
        client.schema.create(schema)

def check_papers_folder(**context):
    """
    First task: Check if papers folder exists and contains PDFs.
    Creates the folder if it doesn't exist.
    Returns the number of PDFs found.
    """
    papers_dir = '/opt/airflow/documents/papers'
    if not os.path.exists(papers_dir):
        print(f"Creating papers directory at {papers_dir}")
        os.makedirs(papers_dir)
    
    # Get list of PDF files
    pdfs = [f for f in os.listdir(papers_dir) if f.endswith('.pdf')]
    print(f"Found {len(pdfs)} PDF files: {pdfs}")
    
    # Pass list of PDFs to next task using XCom
    context['task_instance'].xcom_push(key='pdf_files', value=pdfs)
    return len(pdfs)

def extract_text_from_pdf(**context):
    """
    Second task: Extract text from each PDF file.
    Processes each PDF and splits into page-level chunks.
    """
    papers_dir = '/opt/airflow/documents/papers'
    # Get PDF list from previous task
    pdf_files = context['task_instance'].xcom_pull(key='pdf_files', task_ids='check_papers_folder')
    
    processed_papers = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(papers_dir, pdf_file)
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                chunks = []
                
                # Process each page
                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():  # Only add non-empty pages
                        chunks.append({
                            'content': text.strip(),
                            'page_number': page_num,
                        })
                
                paper_info = {
                    'filename': pdf_file,
                    'chunks': chunks,
                    'total_pages': len(reader.pages)
                }
                processed_papers.append(paper_info)
                print(f"Processed {pdf_file}: {len(chunks)} chunks")
                
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
            continue
    
    # Pass processed papers to next task
    context['task_instance'].xcom_push(key='processed_papers', value=processed_papers)
    return len(processed_papers)

def generate_embeddings_and_store(**context):
    """
    Generate embeddings using a lightweight approach with TF-IDF
    """
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    # Get processed papers from previous task
    processed_papers = context['task_instance'].xcom_pull(key='processed_papers', task_ids='extract_text')
    
    # Initialize vectorizer
    vectorizer = TfidfVectorizer(max_features=100)  # Limit features for speed
    
    total_chunks = 0
    all_chunks = []
    
    # Collect all text chunks
    for paper in processed_papers:
        filename = paper['filename']
        print(f"Processing {filename}")
        
        for chunk in paper['chunks']:
            all_chunks.append(chunk['content'])
            
    # Generate embeddings for all chunks at once
    try:
        embeddings = vectorizer.fit_transform(all_chunks).toarray()
        
        # Store in Weaviate
        client = get_weaviate_client()
        init_weaviate_schema()
        
        # Store each chunk with its embedding
        for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
            # Calculate which paper this chunk belongs to
            chunks_per_paper = len(processed_papers[0]['chunks'])
            paper_index = i // chunks_per_paper
            paper = processed_papers[paper_index]
            
            client.data_object.create(
                class_name="ResearchPaper",
                data_object={
                    "title": paper['filename'].replace('.pdf', ''),
                    "content": chunk[:1000],  # Limit content length
                    "page_number": paper['chunks'][i % chunks_per_paper]['page_number'],
                    "filename": paper['filename']
                },
                vector=embedding.tolist(),
                uuid=str(uuid.uuid4())
            )
            total_chunks += 1
            
        print(f"Successfully stored {total_chunks} chunks with embeddings")
        return total_chunks
        
    except Exception as e:
        print(f"Error in embedding generation: {str(e)}")
        raise

# DAG definition
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 2, 1),
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

# Define the tasks
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

store_embeddings = PythonOperator(
    task_id='store_embeddings',
    python_callable=generate_embeddings_and_store,
    dag=dag,
)

# Set task dependencies
check_folder >> extract_text >> store_embeddings
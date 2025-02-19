# Fitness Research Assistant

A data engineering project that processes exercise science research papers and provides evidence-based answers to fitness questions using RAG (Retrieval Augmented Generation).

## Project Overview

This system:
1. Processes research papers about exercise science
2. Extracts and indexes content using vector embeddings
3. Provides research-based answers to fitness questions

### Components

1. **Data Pipeline (Airflow)**
   - PDF processing and text extraction
   - Document chunking and embedding generation
   - Vector database integration
   - Tech Stack: Apache Airflow, PyPDF2

2. **Vector Database**
   - Stores document chunks and embeddings
   - Enables semantic search
   - Tech Stack: Weaviate

3. **Search API**
   - Processes user questions
   - Retrieves relevant research
   - Tech Stack: FastAPI

### Tech Stack
- Apache Airflow for orchestration
- FastAPI for API
- Weaviate for vector storage
- Docker & Docker Compose
- PostgreSQL for Airflow metadata
- Python libraries (PyPDF2, scikit-learn)

## Setup

1. Clone the repository:
```bash
git clone [repository-url]
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access:
   - Airflow UI: http://localhost:8080 (user: admin, pass: admin)
   - API Documentation: http://localhost:8000/docs

4. Add PDFs to `documents/papers/` directory

5. Run the processing pipeline through Airflow UI

## Usage

1. Process papers:
   - Add PDFs to documents/papers/
   - Run the DAG in Airflow

2. Query the system:
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"question": "What is proper squat form?"}'
```

## Project Structure
```
fitness-research/
├── dags/                  # Airflow DAGs
│   └── research_pipeline.py
├── api/                   # FastAPI code
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── documents/papers/      # Research papers
├── docker-compose.yaml    # Docker configuration
├── Dockerfile            # Airflow container config
└── requirements.txt      # Python dependencies
```

## Future Improvements
- Enhanced text extraction and preprocessing
- Better answer generation and summarization
- User interface for easier interaction
- Support for more document formats
- Improved search relevance

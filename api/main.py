from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

app = FastAPI(title="Fitness Research Assistant")

# Initialize vectorizer (same settings as in DAG)
vectorizer = TfidfVectorizer(max_features=100)

def get_weaviate_client():
    """Get Weaviate client with correct Docker service name"""
    import weaviate
    return weaviate.Client("http://weaviate:8080")

def init_weaviate_schema():
    """Initialize the Weaviate schema if it doesn't exist"""
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

# Initialize schema on startup
init_weaviate_schema()

class Query(BaseModel):
    question: str

def extract_relevant_info(content: str, question: str) -> str:
    """Clean and format the content to be more readable and relevant"""
    # Clean up text
    content = content.replace("\\n", " ").replace("\\", "")
    content = " ".join(content.split())  # Remove extra whitespace
    return content

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies Weaviate connection"""
    try:
        client = get_weaviate_client()
        init_weaviate_schema()  # Ensure schema exists
        return {
            "status": "healthy",
            "weaviate": "connected",
            "schema": "initialized"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_papers(query: Query):
    """Search endpoint that finds relevant paper excerpts about fitness"""
    try:
        client = get_weaviate_client()
        
        # Get all documents to fit vectorizer
        response = client.query.get(
            "ResearchPaper",
            ["content"]
        ).do()
        
        if not response or "data" not in response or "Get" not in response["data"]:
            return {
                "question": query.question,
                "findings": [],
                "message": "No documents found. Please run the DAG first to process documents."
            }
            
        # Get all document contents
        documents = [doc["content"] for doc in response["data"]["Get"]["ResearchPaper"]]
        
        # Expand the query to be more specific about proper form
        search_query = f"""
        Find information about {query.question}. 
        Focus on technique, proper form, and safety considerations.
        """
        
        # Fit and transform the vectorizer
        vectorizer.fit(documents)
        query_embedding = vectorizer.transform([search_query]).toarray()[0]
        
        # Search Weaviate
        search_response = client.query.get(
            "ResearchPaper",
            ["content", "filename", "page_number"]
        ).with_near_vector({
            "vector": query_embedding.tolist()
        }).with_limit(3).do()
        
        # Format results to be more user-friendly
        formatted_results = []
        seen_content = set()
        
        if "data" in search_response and "Get" in search_response["data"]:
            papers = search_response["data"]["Get"]["ResearchPaper"]
            for paper in papers:
                content = extract_relevant_info(paper["content"], query.question)
                
                if content in seen_content:
                    continue
                    
                seen_content.add(content)
                formatted_results.append({
                    "excerpt": content,
                    "source": f"Source: {paper['filename']}, Page {paper['page_number']}"
                })
        
        return {
            "question": query.question,
            "findings": formatted_results,
            "note": "These findings are based on scientific research papers. Please consult with a qualified professional for personalized advice."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/papers")
async def list_papers():
    """List all papers in the database"""
    try:
        client = get_weaviate_client()
        
        response = client.query.get(
            "ResearchPaper",
            ["filename"]
        ).with_limit(100).do()
        
        papers = set()
        if "data" in response and "Get" in response["data"]:
            for item in response["data"]["Get"]["ResearchPaper"]:
                papers.add(item["filename"])
        
        return {
            "papers": list(papers)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
from kafka.errors import KafkaError
from prometheus_client import Counter, make_asgi_app
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ingestion Service", version="1.0.0")

# Métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

messages_ingested = Counter('messages_ingested_total', 'Total messages ingested')
messages_failed = Counter('messages_failed_total', 'Total failed messages')

# Configuración de Kafka con reintentos
def create_producer():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers='kafka:9092',
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                acks='all',
                max_in_flight_requests_per_connection=1
            )
            logger.info("Kafka producer connected successfully")
            return producer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

producer = create_producer()

class IngestRequest(BaseModel):
    text: str
    user_id: int | None = None
    metadata: dict | None = None

@app.get("/")
async def root():
    return {"service": "Ingestion Service", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "kafka": "connected"}

@app.post("/ingest")
async def ingest(data: IngestRequest):
    try:
        message = {
            "text": data.text,
            "user_id": data.user_id,
            "metadata": data.metadata or {},
            "timestamp": time.time()
        }
        
        # Enviar a Kafka
        future = producer.send("incoming_messages", message)
        
        # Esperar confirmación
        record_metadata = future.get(timeout=10)
        
        messages_ingested.inc()
        
        logger.info(f"Message ingested: topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
        
        return {
            "status": "success",
            "message": "Message sent to Kafka",
            "topic": record_metadata.topic,
            "partition": record_metadata.partition,
            "offset": record_metadata.offset
        }
        
    except KafkaError as e:
        messages_failed.inc()
        logger.error(f"Kafka error: {str(e)}")
        raise HTTPException(status_code=503, detail="Failed to send message to Kafka")
    except Exception as e:
        messages_failed.inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


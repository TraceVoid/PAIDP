from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
from kafka.errors import KafkaError
from prometheus_client import Counter, make_asgi_app
import json
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuración desde variables de entorno ──────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

app = FastAPI(title="Ingestion Service", version="1.0.0")

# Métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

messages_ingested = Counter('messages_ingested_total', 'Total messages ingested')
messages_failed = Counter('messages_failed_total', 'Total failed messages')

# ── Kafka Producer (con reintentos) ───────────────────────────────────────────
def create_producer() -> KafkaProducer:
    for attempt in range(5):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                acks='all',
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"Kafka producer conectado a {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except KafkaError as e:
            logger.warning(f"Intento {attempt + 1}/5 fallido: {e}")
            if attempt < 4:
                time.sleep(2)
    raise RuntimeError("No se pudo conectar al producer Kafka")


producer = create_producer()


# ── Modelos ───────────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    text: str
    user_id: int | None = None
    metadata: dict | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"service": "Ingestion Service", "status": "running"}


@app.get("/health")
async def health():
    """
    CORRECCIÓN: antes retornaba kafka: "connected" sin verificarlo.
    Ahora hace un list_topics() real para comprobar la conexión.
    """
    try:
        topics = producer.partitions_for("incoming_messages")  # fuerza conexión real
        return {"status": "healthy", "kafka": "connected"}
    except Exception as e:
        logger.error(f"Health check Kafka fallido: {e}")
        raise HTTPException(status_code=503, detail="Kafka no disponible")


@app.post("/ingest")
async def ingest(data: IngestRequest):
    try:
        message = {
            "text": data.text,
            "user_id": data.user_id,
            "metadata": data.metadata or {},
            "timestamp": time.time()
        }

        future = producer.send("incoming_messages", message)
        record_metadata = future.get(timeout=10)

        messages_ingested.inc()
        logger.info(
            f"Mensaje enviado → topic={record_metadata.topic}, "
            f"partition={record_metadata.partition}, offset={record_metadata.offset}"
        )

        return {
            "status": "success",
            "message": "Mensaje enviado a Kafka",
            "topic": record_metadata.topic,
            "partition": record_metadata.partition,
            "offset": record_metadata.offset
        }

    except KafkaError as e:
        messages_failed.inc()
        logger.error(f"Error Kafka: {str(e)}")
        raise HTTPException(status_code=503, detail="Error al enviar mensaje a Kafka")
    except Exception as e:
        messages_failed.inc()
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

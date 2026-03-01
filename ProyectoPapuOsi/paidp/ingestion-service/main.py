from fastapi import FastAPI
from kafka import KafkaProducer
import json

app = FastAPI(title="Ingestion Service")

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

@app.post("/ingest")
async def ingest(data: dict):
    
    producer.send("incoming_messages", data)
    producer.flush()
    
    return {"status": "Message sent to Kafka"}

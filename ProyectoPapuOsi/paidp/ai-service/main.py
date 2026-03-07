from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from prometheus_client import Counter, Histogram, start_http_server
import torch
import json
import logging
import mlflow
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métricas Prometheus
predictions_total = Counter('predictions_total', 'Total predictions made')
predictions_duration = Histogram('prediction_duration_seconds', 'Prediction duration')

# Configuración MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("paidp-threat-detection")

class ThreatDetectionModel:
    def __init__(self):
        logger.info("Initializing threat detection model...")
        
        # Usar modelo pre-entrenado de HuggingFace para detección de toxicidad
        model_name = "unitary/toxic-bert"
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()
            
            logger.info(f"Model loaded successfully: {model_name}")
            
            # Registrar modelo en MLflow
            with mlflow.start_run(run_name="model_initialization"):
                mlflow.log_param("model_name", model_name)
                mlflow.log_param("framework", "pytorch")
                mlflow.set_tag("stage", "production")
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def predict(self, text: str) -> float:
        with predictions_duration.time():
            try:
                # Tokenizar texto
                inputs = self.tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True
                )
                
                # Inferencia
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probs = torch.softmax(logits, dim=1)
                    
                # Score de amenaza (probabilidad de toxicidad)
                threat_score = probs[0][1].item()
                
                predictions_total.inc()
                
                logger.debug(f"Prediction made: score={threat_score:.4f}")
                
                return threat_score
                
            except Exception as e:
                logger.error(f"Prediction error: {str(e)}")
                return 0.0

def create_consumer():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                "incoming_messages",
                bootstrap_servers='kafka:9092',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='ai-service-group'
            )
            logger.info("Kafka consumer connected successfully")
            return consumer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

def create_producer():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers='kafka:9092',
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
            logger.info("Kafka producer connected successfully")
            return producer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

def main():
    # Iniciar servidor de métricas
    start_http_server(8002)
    logger.info("Metrics server started on port 8002")
    
    # Inicializar modelo
    model = ThreatDetectionModel()
    
    # Crear conexiones Kafka
    consumer = create_consumer()
    producer = create_producer()
    
    logger.info("AI Service is ready to process messages")
    
    # Procesar mensajes
    message_count = 0
    
    for message in consumer:
        try:
            data = message.value
            text = data.get("text", "")
            
            if not text:
                logger.warning("Received empty text")
                continue
            
            # Realizar predicción
            with mlflow.start_run(run_name=f"prediction_{message_count}"):
                start_time = time.time()
                score = model.predict(text)
                duration = time.time() - start_time
                
                # Log en MLflow
                mlflow.log_metric("score", score)
                mlflow.log_metric("duration_ms", duration * 1000)
                mlflow.log_param("text_length", len(text))
            
            # Enviar resultado
            result = {
                "text": text,
                "score": score,
                "user_id": data.get("user_id"),
                "timestamp": data.get("timestamp"),
                "metadata": data.get("metadata", {})
            }
            
            producer.send("ai_scores", result)
            producer.flush()
            
            message_count += 1
            
            if message_count % 100 == 0:
                logger.info(f"Processed {message_count} messages")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            continue

if __name__ == "__main__":
    main()


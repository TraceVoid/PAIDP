from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from prometheus_client import Counter, Gauge, start_http_server
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métricas Prometheus
decisions_total = Counter('decisions_total', 'Total decisions made', ['action'])
current_threat_level = Gauge('current_threat_level', 'Current threat level')
avg_score = Gauge('average_threat_score', 'Average threat score')

# Configuración de umbrales
THRESHOLDS = {
    'block': 0.7,
    'alert': 0.4,
    'allow': 0.0
}

class DecisionEngine:
    def __init__(self):
        self.scores_buffer = []
        self.buffer_size = 100
        
    def decide(self, score: float, metadata: dict = None) -> dict:
        """
        Toma decisiones basadas en el score y contexto adicional
        """
        # Agregar score al buffer
        self.scores_buffer.append(score)
        if len(self.scores_buffer) > self.buffer_size:
            self.scores_buffer.pop(0)
        
        # Calcular promedio
        avg = sum(self.scores_buffer) / len(self.scores_buffer) if self.scores_buffer else 0
        avg_score.set(avg)
        
        # Determinar acción
        if score >= THRESHOLDS['block']:
            action = "block"
            priority = "high"
            reason = "High threat score detected"
        elif score >= THRESHOLDS['alert']:
            action = "alert"
            priority = "medium"
            reason = "Moderate threat score detected"
        else:
            action = "allow"
            priority = "low"
            reason = "Low threat score"
        
        # Ajustar decisión basado en tendencia
        if avg > THRESHOLDS['alert'] and action == "allow":
            action = "alert"
            reason += " (elevated due to trend)"
        
        # Actualizar métricas
        decisions_total.labels(action=action).inc()
        current_threat_level.set(score)
        
        decision = {
            "action": action,
            "priority": priority,
            "reason": reason,
            "score": score,
            "avg_score": avg
        }
        
        logger.info(f"Decision made: {action} (score={score:.4f}, avg={avg:.4f})")
        
        return decision

def create_consumer():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                "ai_scores",
                bootstrap_servers='kafka:9092',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='decision-agent-group'
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
    start_http_server(8003)
    logger.info("Metrics server started on port 8003")
    
    # Inicializar motor de decisiones
    engine = DecisionEngine()
    
    # Crear conexiones Kafka
    consumer = create_consumer()
    producer = create_producer()
    
    logger.info("Decision Agent is ready to process scores")
    
    message_count = 0
    
    for message in consumer:
        try:
            data = message.value
            score = data.get("score", 0.0)
            
            # Tomar decisión
            decision = engine.decide(score, data.get("metadata", {}))
            
            # Preparar mensaje de salida
            result = {
                "text": data.get("text", ""),
                "score": score,
                "action": decision["action"],
                "priority": decision["priority"],
                "reason": decision["reason"],
                "user_id": data.get("user_id"),
                "timestamp": data.get("timestamp"),
                "metadata": data.get("metadata", {})
            }
            
            # Enviar a SOAR
            producer.send("security_actions", result)
            producer.flush()
            
            message_count += 1
            
            if message_count % 100 == 0:
                logger.info(f"Processed {message_count} decisions")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            continue

if __name__ == "__main__":
    main()


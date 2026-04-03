from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from prometheus_client import Counter, Gauge, start_http_server
from collections import deque
import json
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuración desde variables de entorno ──────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
THRESHOLD_BLOCK = float(os.getenv("THRESHOLD_BLOCK", "0.7"))
THRESHOLD_ALERT = float(os.getenv("THRESHOLD_ALERT", "0.4"))

# ── Métricas Prometheus ───────────────────────────────────────────────────────
decisions_total = Counter('decisions_total', 'Total decisions made', ['action'])
current_threat_level = Gauge('current_threat_level', 'Current threat level')
avg_score_gauge = Gauge('average_threat_score', 'Average threat score')


# ── Motor de decisión ─────────────────────────────────────────────────────────
class DecisionEngine:
    def __init__(self, buffer_size: int = 100):
        # CORRECCIÓN: deque con maxlen es O(1) vs list.pop(0) que es O(n)
        self.scores_buffer: deque = deque(maxlen=buffer_size)

    def decide(self, score: float, metadata: dict = None) -> dict:
        self.scores_buffer.append(score)

        avg = sum(self.scores_buffer) / len(self.scores_buffer)
        avg_score_gauge.set(avg)
        current_threat_level.set(score)

        if score >= THRESHOLD_BLOCK:
            action, priority, reason = "block", "high", "Score de amenaza alto"
        elif score >= THRESHOLD_ALERT:
            action, priority, reason = "alert", "medium", "Score de amenaza moderado"
        else:
            action, priority, reason = "allow", "low", "Score de amenaza bajo"

        # Elevar decisión si la tendencia reciente es alta
        if avg > THRESHOLD_ALERT and action == "allow":
            action = "alert"
            reason += " (elevado por tendencia)"

        decisions_total.labels(action=action).inc()

        decision = {
            "action": action,
            "priority": priority,
            "reason": reason,
            "score": score,
            "avg_score": avg
        }
        logger.info(f"Decisión: {action} (score={score:.4f}, avg={avg:.4f})")
        return decision


# ── Kafka ─────────────────────────────────────────────────────────────────────
def create_consumer():
    for attempt in range(5):
        try:
            consumer = KafkaConsumer(
                "ai_scores",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='decision-agent-group'
            )
            logger.info("Kafka consumer conectado")
            return consumer
        except KafkaError as e:
            logger.warning(f"Intento {attempt + 1}/5 fallido: {e}")
            if attempt < 4:
                time.sleep(2)
    raise Exception("No se pudo conectar al consumidor Kafka")


def create_producer():
    for attempt in range(5):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
            logger.info("Kafka producer conectado")
            return producer
        except KafkaError as e:
            logger.warning(f"Intento {attempt + 1}/5 fallido: {e}")
            if attempt < 4:
                time.sleep(2)
    raise Exception("No se pudo conectar al producer Kafka")


def main():
    start_http_server(8003)
    logger.info("Servidor de métricas en puerto 8003")

    engine = DecisionEngine()
    consumer = create_consumer()
    producer = create_producer()

    logger.info("Decision Agent listo")

    message_count = 0
    for message in consumer:
        try:
            data = message.value
            score = data.get("score", 0.0)

            decision = engine.decide(score, data.get("metadata", {}))

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

            producer.send("security_actions", result)
            producer.flush()

            message_count += 1
            if message_count % 100 == 0:
                logger.info(f"Procesadas {message_count} decisiones")

        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            continue


if __name__ == "__main__":
    main()

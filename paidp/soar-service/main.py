from kafka import KafkaConsumer
from kafka.errors import KafkaError
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from prometheus_client import Counter, start_http_server
from datetime import datetime, timezone
from contextlib import contextmanager
import json
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Métricas Prometheus ───────────────────────────────────────────────────────
actions_total = Counter('soar_actions_total', 'Total SOAR actions executed', ['action'])

# ── Configuración ─────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/paidp")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

# ── Base de datos ─────────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    score = Column(Float)
    action = Column(String)
    priority = Column(String)
    reason = Column(String)
    status = Column(String)   # open | investigating | resolved
    user_id = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)


# ── Sesión por operación (CORRECCIÓN: no usar sesión global) ──────────────────
@contextmanager
def get_db_session():
    """
    Proporciona una sesión DB con ciclo de vida por operación.
    CORRECCIÓN: la versión anterior usaba una única sesión para toda la vida
    del servicio; si ocurría un error la sesión quedaba en estado inválido
    y todas las operaciones siguientes fallaban silenciosamente.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Motor SOAR ────────────────────────────────────────────────────────────────
class SOAREngine:

    def execute_action(self, data: dict):
        action = data.get("action", "unknown")
        text = data.get("text", "")
        score = data.get("score", 0.0)
        priority = data.get("priority", "low")
        reason = data.get("reason", "")
        user_id = data.get("user_id")

        with get_db_session() as db:
            incident = SecurityIncident(
                text=text,
                score=score,
                action=action,
                priority=priority,
                reason=reason,
                status="open" if action in ["block", "alert"] else "resolved",
                user_id=user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(incident)
            db.flush()   # obtener ID sin cerrar sesión aún

            if action == "block":
                self._block_threat(incident)
            elif action == "alert":
                self._alert_admin(incident)
            elif action == "allow":
                self._log_allowed(incident, db)
            else:
                logger.warning(f"Acción desconocida: {action}")

        actions_total.labels(action=action).inc()
        logger.info(f"Acción ejecutada: {action} (incidente #{incident.id})")

    def _block_threat(self, incident: SecurityIncident):
        logger.warning(f"🚫 BLOQUEO DE AMENAZA [ID: {incident.id}]")
        logger.warning(f"   Score:    {incident.score:.4f}")
        logger.warning(f"   Prioridad:{incident.priority}")
        logger.warning(f"   Razón:    {incident.reason}")
        logger.warning(f"   Texto:    {incident.text[:100]}...")
        # TODO: integrar con firewall, SIEM, etc.

    def _alert_admin(self, incident: SecurityIncident):
        logger.info(f"⚠️  ALERTA [ID: {incident.id}]")
        logger.info(f"   Score:    {incident.score:.4f}")
        logger.info(f"   Prioridad:{incident.priority}")
        logger.info(f"   Razón:    {incident.reason}")
        logger.info(f"   Texto:    {incident.text[:100]}...")
        # TODO: enviar email, Slack, crear ticket, etc.

    def _log_allowed(self, incident: SecurityIncident, db):
        logger.debug(f"✅ PERMITIDO [ID: {incident.id}] score={incident.score:.4f}")
        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)


# ── Kafka ─────────────────────────────────────────────────────────────────────
def create_consumer():
    for attempt in range(5):
        try:
            consumer = KafkaConsumer(
                "security_actions",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='soar-service-group'
            )
            logger.info("Kafka consumer conectado")
            return consumer
        except KafkaError as e:
            logger.warning(f"Intento {attempt + 1}/5 fallido: {e}")
            if attempt < 4:
                time.sleep(2)
    raise Exception("No se pudo conectar al consumidor Kafka")


def main():
    start_http_server(8004)
    logger.info("Servidor de métricas en puerto 8004")

    soar = SOAREngine()
    consumer = create_consumer()

    logger.info("SOAR Service listo para ejecutar acciones")

    message_count = 0
    for message in consumer:
        try:
            soar.execute_action(message.value)
            message_count += 1
            if message_count % 100 == 0:
                logger.info(f"Ejecutadas {message_count} acciones")
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            continue


if __name__ == "__main__":
    main()

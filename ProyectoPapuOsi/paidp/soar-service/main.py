from kafka import KafkaConsumer
from kafka.errors import KafkaError
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from prometheus_client import Counter, start_http_server
from datetime import datetime
import json
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métricas Prometheus
actions_total = Counter('soar_actions_total', 'Total SOAR actions executed', ['action'])

# Base de datos PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/paidp")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SecurityIncident(Base):
    __tablename__ = "security_incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    score = Column(Float)
    action = Column(String)
    priority = Column(String)
    reason = Column(String)
    status = Column(String)  # open, investigating, resolved
    user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

class SOAREngine:
    def __init__(self):
        self.db = SessionLocal()
        
    def execute_action(self, data: dict):
        """
        Ejecuta acciones de seguridad basadas en la decisión
        """
        action = data.get("action", "unknown")
        text = data.get("text", "")
        score = data.get("score", 0.0)
        priority = data.get("priority", "low")
        reason = data.get("reason", "")
        user_id = data.get("user_id")
        
        # Registrar incidente en base de datos
        incident = SecurityIncident(
            text=text,
            score=score,
            action=action,
            priority=priority,
            reason=reason,
            status="open" if action in ["block", "alert"] else "resolved",
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        try:
            self.db.add(incident)
            self.db.commit()
            self.db.refresh(incident)
            
            # Ejecutar acción específica
            if action == "block":
                self._block_threat(incident)
            elif action == "alert":
                self._alert_admin(incident)
            elif action == "allow":
                self._log_allowed(incident)
            else:
                logger.warning(f"Unknown action: {action}")
            
            actions_total.labels(action=action).inc()
            
            logger.info(f"Action executed: {action} for incident {incident.id}")
            
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            self.db.rollback()
    
    def _block_threat(self, incident: SecurityIncident):
        """
        Bloquear amenaza detectada
        """
        logger.warning(f"🚫 BLOCKING THREAT [ID: {incident.id}]")
        logger.warning(f"   Score: {incident.score:.4f}")
        logger.warning(f"   Priority: {incident.priority}")
        logger.warning(f"   Reason: {incident.reason}")
        logger.warning(f"   Text: {incident.text[:100]}...")
        
        # Aquí se podría:
        # - Bloquear IP
        # - Cerrar conexión
        # - Actualizar firewall
        # - Notificar a SIEM
        
    def _alert_admin(self, incident: SecurityIncident):
        """
        Alertar a administradores
        """
        logger.info(f"⚠️  ALERT [ID: {incident.id}]")
        logger.info(f"   Score: {incident.score:.4f}")
        logger.info(f"   Priority: {incident.priority}")
        logger.info(f"   Reason: {incident.reason}")
        logger.info(f"   Text: {incident.text[:100]}...")
        
        # Aquí se podría:
        # - Enviar email
        # - Enviar notificación Slack/Teams
        # - Crear ticket en sistema de tickets
        # - Escalar a equipo de seguridad
        
    def _log_allowed(self, incident: SecurityIncident):
        """
        Registrar contenido permitido
        """
        logger.debug(f"✅ ALLOWED [ID: {incident.id}]")
        logger.debug(f"   Score: {incident.score:.4f}")
        
        # Marcar como resuelto inmediatamente
        incident.status = "resolved"
        incident.resolved_at = datetime.utcnow()
        self.db.commit()

def create_consumer():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                "security_actions",
                bootstrap_servers='kafka:9092',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='soar-service-group'
            )
            logger.info("Kafka consumer connected successfully")
            return consumer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

def main():
    # Iniciar servidor de métricas
    start_http_server(8004)
    logger.info("Metrics server started on port 8004")
    
    # Inicializar motor SOAR
    soar = SOAREngine()
    
    # Crear consumidor Kafka
    consumer = create_consumer()
    
    logger.info("SOAR Service is ready to execute actions")
    
    message_count = 0
    
    for message in consumer:
        try:
            data = message.value
            soar.execute_action(data)
            
            message_count += 1
            
            if message_count % 100 == 0:
                logger.info(f"Executed {message_count} actions")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            continue

if __name__ == "__main__":
    main()


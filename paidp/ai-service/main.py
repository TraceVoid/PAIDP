from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from prometheus_client import Counter, Histogram, make_asgi_app
import torch
import re
import json
import logging
import time
import threading
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
# Modelo entrenado específicamente para phishing (mucho más preciso que toxic-bert)
MODEL_NAME = os.getenv("MODEL_NAME", "ealvaradob/bert-finetuned-phishing")

app = FastAPI(title="AI Service", version="1.0.0")

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

predictions_total = Counter('predictions_total', 'Total predictions made')
predictions_duration = Histogram('prediction_duration_seconds', 'Prediction duration')

model_instance = None
model_loading = False
model_error = None

# ── Heurísticas de phishing (capa de reglas, funciona sin modelo) ─────────────
# Patrones que indican phishing con alta confianza
PHISHING_URL_PATTERNS = [
    r'secure[\-\.][\w\-]+\.(com|net|org)/verify',
    r'[\w\-]+-paypal[\-\.]',
    r'[\w\-]+-amazon[\-\.]',
    r'[\w\-]+-netflix[\-\.]',
    r'[\w\-]+-google[\-\.]',
    r'[\w\-]+-apple[\-\.]',
    r'[\w\-]+-microsoft[\-\.]',
    r'[\w\-]+-facebook[\-\.]',
    r'login[\-\.][\w\-]+\.(xyz|tk|ml|ga|cf|gq)',
    r'verify[\-\.][\w\-]+\.(xyz|tk|ml|ga|cf|gq)',
    r'account[\-\.][\w\-]+\.(xyz|tk|ml|ga|cf|gq)',
    r'http[s]?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP directa
    r'bit\.ly|tinyurl\.com|goo\.gl|t\.co/[a-zA-Z0-9]+.*login',
]

# Palabras clave de urgencia + acción típicas en phishing
URGENCY_KEYWORDS = [
    'verify your account', 'confirm your account', 'update your information',
    'your account has been', 'account compromised', 'account suspended',
    'account will be closed', 'unusual activity', 'suspicious activity',
    'click here immediately', 'act now', 'expires in 24', 'expires in 48',
    'limited time', 'your password has', 'reset your password immediately',
    'confirm your identity', 'validate your account', 'reactivate your account',
    'your account is at risk', 'click the link below to verify',
    'verify now', 'confirm now', 'update now',
]

# Combinaciones de URL + palabras de acción (muy alta señal de phishing)
ACTION_WORDS_WITH_URL = [
    'login', 'verify', 'validate', 'confirm', 'update', 'secure',
    'account', 'password', 'credential', 'sign in', 'log in',
]


def heuristic_phishing_score(text: str) -> float:
    """
    Calcula un score de phishing basado en reglas heurísticas.
    Retorna un valor entre 0.0 y 1.0.
    No depende del modelo ML — funciona siempre.
    """
    text_lower = text.lower()
    score = 0.0
    has_url = bool(re.search(r'https?://', text_lower))

    # 1. URL con patrones de phishing conocidos
    for pattern in PHISHING_URL_PATTERNS:
        if re.search(pattern, text_lower):
            score = max(score, 0.92)
            logger.info(f"Heurística: patrón URL phishing detectado → {pattern}")
            return score  # certeza alta, no seguir calculando

    # 2. Palabras de urgencia/acción + URL presente
    if has_url:
        for keyword in ACTION_WORDS_WITH_URL:
            if keyword in text_lower:
                score = max(score, 0.75)
                break

    # 3. Frases de urgencia típicas de phishing
    for phrase in URGENCY_KEYWORDS:
        if phrase in text_lower:
            score = max(score, 0.80)
            logger.info(f"Heurística: frase urgencia detectada → '{phrase}'")
            break

    # 4. URGENT en mayúsculas + cualquier URL
    if 'URGENT' in text and has_url:
        score = max(score, 0.85)

    # 5. Múltiples palabras de acción sin URL → score moderado
    action_count = sum(1 for kw in ACTION_WORDS_WITH_URL if kw in text_lower)
    if action_count >= 3 and not has_url:
        score = max(score, 0.55)

    return round(score, 4)


# ── Modelo ML ─────────────────────────────────────────────────────────────────
class PhishingDetectionModel:
    def __init__(self):
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        logger.info(f"Cargando modelo: {MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        self.model.eval()
        logger.info("Modelo cargado correctamente")

    def predict(self, text: str) -> float:
        try:
            inputs = self.tokenizer(
                text, return_tensors="pt",
                truncation=True, max_length=512, padding=True
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
            # label 1 = phishing en este modelo
            return probs[0][1].item()
        except Exception as e:
            logger.error(f"Error en predicción del modelo: {e}")
            return 0.0


def combined_predict(text: str) -> float:
    """
    Score final = máximo entre heurísticas y modelo ML.
    Si las heurísticas ya detectan phishing claro, el modelo es secundario.
    Si el modelo está cargando, solo se usan heurísticas.
    """
    heuristic_score = heuristic_phishing_score(text)

    if model_instance is not None:
        with predictions_duration.time():
            ml_score = model_instance.predict(text)
        predictions_total.inc()
        # Tomar el máximo: si cualquiera de los dos detecta phishing, es phishing
        final_score = max(heuristic_score, ml_score)
        logger.info(
            f"Score → heurística={heuristic_score:.3f}, "
            f"modelo={ml_score:.3f}, final={final_score:.3f}"
        )
    else:
        final_score = heuristic_score
        logger.info(
            f"Score (solo heurísticas, modelo cargando) → {final_score:.3f}"
        )

    return round(final_score, 4)


# ── Carga de modelo en background ─────────────────────────────────────────────
def load_model_background():
    global model_instance, model_loading, model_error
    model_loading = True
    try:
        model_instance = PhishingDetectionModel()
        t = threading.Thread(target=kafka_consumer_loop, daemon=True)
        t.start()
    except Exception as e:
        model_error = str(e)
        logger.error(f"Error cargando modelo: {e}")
        logger.warning("El servicio continuará usando solo heurísticas")
    finally:
        model_loading = False


@app.on_event("startup")
def startup():
    t = threading.Thread(target=load_model_background, daemon=True)
    t.start()


# ── Endpoints ─────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    score: float
    prediction: str


@app.get("/")
def root():
    return {"service": "AI Service", "status": "running"}


@app.get("/health")
def health():
    if model_error:
        # El modelo falló pero las heurísticas siguen funcionando
        return {"status": "degraded", "model": MODEL_NAME, "note": "usando solo heurísticas"}
    if model_loading or model_instance is None:
        return {"status": "loading", "model": MODEL_NAME, "note": "heurísticas activas"}
    return {"status": "healthy", "model": MODEL_NAME}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="El campo 'text' no puede estar vacío")

    score = combined_predict(request.text)
    prediction = "phishing" if score > 0.7 else "suspicious" if score > 0.4 else "legitimate"
    return PredictResponse(score=score, prediction=prediction)


# ── Loop Kafka ────────────────────────────────────────────────────────────────
def create_consumer():
    for _ in range(5):
        try:
            return KafkaConsumer(
                "incoming_messages",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='ai-service-group'
            )
        except KafkaError:
            time.sleep(2)
    raise Exception("No se pudo conectar al consumidor Kafka")


def create_producer():
    for _ in range(5):
        try:
            return KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all'
            )
        except KafkaError:
            time.sleep(2)
    raise Exception("No se pudo conectar al producer Kafka")


def kafka_consumer_loop():
    try:
        consumer = create_consumer()
        producer = create_producer()
    except Exception as e:
        logger.error(f"Loop Kafka no pudo iniciarse: {e}")
        return

    logger.info("Loop Kafka activo")
    for message in consumer:
        try:
            data = message.value
            text = data.get("text", "")
            if not text:
                continue
            score = combined_predict(text)
            prediction = "phishing" if score > 0.7 else "suspicious" if score > 0.4 else "legitimate"
            producer.send("ai_scores", {
                "text": text, "score": score, "prediction": prediction,
                "user_id": data.get("user_id"),
                "timestamp": data.get("timestamp"),
                "metadata": data.get("metadata", {})
            })
            producer.flush()
        except Exception as e:
            logger.error(f"Error en loop Kafka: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

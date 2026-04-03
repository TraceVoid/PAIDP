from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from prometheus_client import Counter, Histogram, make_asgi_app
import requests
import redis
import json
import logging
import os

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuración desde variables de entorno ──────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/paidp")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8002")

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="PAIDP API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

request_counter = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
request_duration = Histogram('api_request_duration_seconds', 'API request duration')

# ── Seguridad ─────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ── Base de datos ─────────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class ThreatLog(Base):
    __tablename__ = "threat_logs"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    score = Column(Float)
    action = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer)


Base.metadata.create_all(bind=engine)

# ── Redis (con reintentos) ────────────────────────────────────────────────────
def create_redis_client() -> redis.Redis:
    """Crea el cliente Redis con reintentos en caso de fallo inicial."""
    import time
    for attempt in range(5):
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            client.ping()
            logger.info(f"Redis conectado en {REDIS_HOST}:{REDIS_PORT}")
            return client
        except redis.ConnectionError as e:
            logger.warning(f"Intento {attempt + 1}/5 de conexión a Redis fallido: {e}")
            if attempt < 4:
                time.sleep(2)
    raise RuntimeError("No se pudo conectar a Redis después de 5 intentos")


redis_client = create_redis_client()

# ── Umbrales de decisión (deben coincidir con decision-agent) ─────────────────
THRESHOLD_BLOCK = float(os.getenv("THRESHOLD_BLOCK", "0.7"))
THRESHOLD_ALERT = float(os.getenv("THRESHOLD_ALERT", "0.4"))


def score_to_action(score: float) -> str:
    if score >= THRESHOLD_BLOCK:
        return "block"
    elif score >= THRESHOLD_ALERT:
        return "alert"
    return "allow"


# ── Modelos Pydantic ──────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    text: str
    score: float
    action: str
    timestamp: datetime


# ── Utilidades ────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "PAIDP API Gateway", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    issues = []
    try:
        redis_client.ping()
    except Exception:
        issues.append("redis")

    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        issues.append("database")

    if issues:
        raise HTTPException(status_code=503, detail=f"Servicios no disponibles: {issues}")

    return {"status": "healthy", "database": "connected", "redis": "connected"}


@app.post("/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    request_counter.labels(method='POST', endpoint='/register').inc()

    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username ya registrado")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    logger.info(f"Nuevo usuario registrado: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    request_counter.labels(method='POST', endpoint='/token').inc()

    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    logger.info(f"Usuario autenticado: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_counter.labels(method='POST', endpoint='/analyze').inc()

    try:
        # ── 1. Revisar caché Redis ─────────────────────────────────────────
        cache_key = f"analysis:{hash(request.text)}"
        cached = redis_client.get(cache_key)

        if cached:
            logger.info(f"Cache hit para usuario {current_user.username}")
            result = json.loads(cached)
        else:
            # ── 2. Llamar al AI Service directamente (resultado síncrono) ──
            # CORRECCIÓN: antes se llamaba a ingestion-service que solo retorna
            # confirmación de Kafka, nunca el score real. Ahora se llama
            # directamente al endpoint /predict del ai-service.
            ai_response = requests.post(
                f"{AI_SERVICE_URL}/predict",
                json={"text": request.text},
                timeout=30
            )
            if ai_response.status_code != 200:
                raise HTTPException(status_code=503, detail="AI Service no disponible")

            ai_data = ai_response.json()
            score = ai_data.get("score", 0.0)
            action = score_to_action(score)

            result = {"score": score, "action": action}

            # Guardar en caché 5 minutos
            redis_client.setex(cache_key, 300, json.dumps(result))

            # ── 3. Enviar a ingestion-service para pipeline SOAR async ─────
            try:
                requests.post(
                    "http://ingestion-service:8001/ingest",
                    json={"text": request.text, "user_id": current_user.id},
                    timeout=5
                )
            except Exception as e:
                # El pipeline SOAR es best-effort; no bloquea la respuesta
                logger.warning(f"No se pudo enviar a ingestion-service: {e}")

        # ── 4. Persistir en base de datos ─────────────────────────────────
        now = datetime.now(timezone.utc)
        threat_log = ThreatLog(
            text=request.text,
            score=result.get("score", 0.0),
            action=result.get("action", "unknown"),
            user_id=current_user.id,
            timestamp=now
        )
        db.add(threat_log)
        db.commit()

        logger.info(
            f"Análisis para {current_user.username}: "
            f"score={result.get('score'):.2f}, action={result.get('action')}"
        )

        return AnalyzeResponse(
            text=request.text,
            score=result.get("score", 0.0),
            action=result.get("action", "unknown"),
            timestamp=now
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red: {str(e)}")
        raise HTTPException(status_code=503, detail="Servicio temporalmente no disponible")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en análisis: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    request_counter.labels(method='GET', endpoint='/history').inc()

    logs = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id
    ).order_by(ThreatLog.timestamp.desc()).limit(limit).all()

    return {"logs": logs}


@app.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_counter.labels(method='GET', endpoint='/stats').inc()

    total = db.query(ThreatLog).filter(ThreatLog.user_id == current_user.id).count()
    blocked = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id, ThreatLog.action == "block"
    ).count()
    alerted = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id, ThreatLog.action == "alert"
    ).count()
    allowed = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id, ThreatLog.action == "allow"
    ).count()

    return {
        "total_analyses": total,
        "blocked": blocked,
        "alerted": alerted,
        "allowed": allowed
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

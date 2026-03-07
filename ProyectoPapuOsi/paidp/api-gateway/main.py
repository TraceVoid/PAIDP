from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from prometheus_client import Counter, Histogram, make_asgi_app
import requests
import redis
import json
import logging
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la aplicación
app = FastAPI(title="PAIDP API Gateway", version="1.0.0")

# CORS
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

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Base de datos PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@postgres:5432/paidp")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# Modelos de base de datos
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
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer)

Base.metadata.create_all(bind=engine)

# Modelos Pydantic
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

# Funciones de utilidad
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
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

# Endpoints
@app.get("/")
async def root():
    return {"message": "PAIDP API Gateway", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health():
    try:
        redis_client.ping()
        return {"status": "healthy", "database": "connected", "redis": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    request_counter.labels(method='POST', endpoint='/register').inc()
    
    # Verificar si el usuario ya existe
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Crear token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"New user registered: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    request_counter.labels(method='POST', endpoint='/token').inc()
    
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_counter.labels(method='POST', endpoint='/analyze').inc()
    
    try:
        # Verificar cache en Redis
        cache_key = f"analysis:{hash(request.text)}"
        cached = redis_client.get(cache_key)
        
        if cached:
            logger.info(f"Cache hit for user {current_user.username}")
            result = json.loads(cached)
        else:
            # Enviar a ingestion service
            INGESTION_URL = "http://ingestion-service:8001/ingest"
            response = requests.post(
                INGESTION_URL,
                json={"text": request.text, "user_id": current_user.id},
                timeout=10
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ingestion service error")
            
            result = response.json()
            
            # Guardar en cache (5 minutos)
            redis_client.setex(cache_key, 300, json.dumps(result))
        
        # Guardar en base de datos
        threat_log = ThreatLog(
            text=request.text,
            score=result.get("score", 0.0),
            action=result.get("action", "unknown"),
            user_id=current_user.id,
            timestamp=datetime.utcnow()
        )
        db.add(threat_log)
        db.commit()
        
        logger.info(f"Analysis completed for user {current_user.username}: action={result.get('action')}")
        
        return AnalyzeResponse(
            text=request.text,
            score=result.get("score", 0.0),
            action=result.get("action", "unknown"),
            timestamp=datetime.utcnow()
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    request_counter.labels(method='GET', endpoint='/history').inc()
    
    logs = db.query(ThreatLog).filter(ThreatLog.user_id == current_user.id).order_by(
        ThreatLog.timestamp.desc()
    ).limit(limit).all()
    
    return {"logs": logs}

@app.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    request_counter.labels(method='GET', endpoint='/stats').inc()
    
    total = db.query(ThreatLog).filter(ThreatLog.user_id == current_user.id).count()
    blocked = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id,
        ThreatLog.action == "block"
    ).count()
    alerted = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id,
        ThreatLog.action == "alert"
    ).count()
    allowed = db.query(ThreatLog).filter(
        ThreatLog.user_id == current_user.id,
        ThreatLog.action == "allow"
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


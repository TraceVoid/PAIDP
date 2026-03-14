# 🛡️ TEZCAT – Plataforma Autónoma Inteligente de Defensa contra Ciberamenazas

<p align="center">
Sistema de detección de amenazas en tiempo real utilizando Inteligencia Artificial,
mensajería distribuida y automatización de respuestas de seguridad.
</p>

---

# ⚙️ Stack Tecnológico

## Frontend

<p align="center">
<img src="https://skillicons.dev/icons?i=react,materialui,vscode&perline=6" />
</p>

- **React**
- **Material UI**
- Visualización de métricas y eventos en tiempo real

---

## Backend

<p align="center">
<img src="https://skillicons.dev/icons?i=py,fastapi,git,github&perline=6" />
</p>

- **FastAPI**
- API RESTful
- Autenticación JWT
- Rate limiting

---

## Inteligencia Artificial

<p align="center">
<img src="https://skillicons.dev/icons?i=python,pytorch&perline=6" />
</p>

- **PyTorch**
- **Transformers / HuggingFace**
- Modelo BERT para detección de toxicidad y amenazas

---

## Infraestructura y Mensajería

<p align="center">
<img src="https://skillicons.dev/icons?i=kafka,postgres,redis,docker,kubernetes&perline=6" />
</p>

- **Kafka** → mensajería distribuida
- **PostgreSQL** → almacenamiento de incidentes
- **Redis** → rate limiting y cache
- **Docker** → contenedores
- **Kubernetes** → orquestación

---

## Observabilidad y MLOps

<p align="center">
<img src="https://skillicons.dev/icons?i=prometheus,grafana&perline=6" />
</p>

- **Prometheus** → métricas del sistema
- **Grafana** → dashboards de monitoreo
- **MLflow** → tracking de experimentos de IA

---

# 🧩 Arquitectura del Sistema

TEZCAT está compuesto por varios microservicios que trabajan en conjunto:

### 1️⃣ API Gateway

Puerto: `8000`

Responsabilidades:

- Autenticación JWT
- Rate limiting con Redis
- Endpoints RESTful
- Exportación de métricas para Prometheus

---

### 2️⃣ Ingestion Service

Puerto: `8001`

Responsabilidades:

- Recibir datos desde el API Gateway
- Validar payloads
- Publicar eventos en Kafka

---

### 3️⃣ AI Service

Responsabilidades:

- Consumir mensajes desde Kafka
- Analizar datos con modelo BERT
- Generar scores de amenaza
- Registrar métricas con MLflow

---

### 4️⃣ Decision Agent

Responsabilidades:

- Aplicar lógica de decisión basada en umbrales
- Analizar tendencias
- Determinar acciones de seguridad

---

### 5️⃣ SOAR Service

Responsabilidades:

- Ejecutar respuestas automáticas
- Registrar incidentes en PostgreSQL
- Gestionar logs estructurados

---

### 6️⃣ Dashboard

Responsabilidades:

- Visualización de métricas
- Historial de análisis
- Gráficos en tiempo real
- Panel de monitoreo

---

# 🚀 Inicio Rápido

## Prerrequisitos

- Docker
- Docker Compose
- Node.js 18+
- Python 3.10+
- Kubernetes (opcional)

---

# 🐳 Instalación con Docker Compose

```bash
git clone https://github.com/TraceVoid/PAIDP
cd ProyectoPapuOsi/paidp

docker-compose up --build
```

### Servicios disponibles

Dashboard  
```
http://localhost:3000
```

API Gateway  
```
http://localhost:8000
```

Swagger UI  
```
http://localhost:8000/docs
```

Prometheus  
```
http://localhost:9090
```

Grafana  
```
http://localhost:3001
```

MLflow  
```
http://localhost:5000
```

---

# 💻 Desarrollo Local

## Backend

```bash
cd api-gateway
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Frontend

```bash
cd dashboard
npm install
npm start
```

---

# 🧪 Uso de la API

### Registro

```bash
curl -X POST http://localhost:8000/register \
-H "Content-Type: application/json" \
-d '{"username":"user1","email":"user@example.com","password":"password123"}'
```

---

### Obtener token

```bash
TOKEN=$(curl -X POST http://localhost:8000/token \
-d "username=user1&password=password123" | jq -r .access_token)
```

---

### Analizar texto

```bash
curl -X POST http://localhost:8000/analyze \
-H "Authorization: Bearer $TOKEN" \
-H "Content-Type: application/json" \
-d '{"text":"Texto a analizar"}'
```

---

# ⚙️ Variables de Entorno

Archivo `.env`

```env
SECRET_KEY=your-secret-key

DATABASE_URL=postgresql://admin:admin@postgres:5432/paidp

MLFLOW_TRACKING_URI=http://mlflow:5000

KAFKA_BOOTSTRAP_SERVERS=kafka:9092

REDIS_HOST=redis
REDIS_PORT=6379
```

⚠️ Cambiar `SECRET_KEY` antes de producción.

---

# 📁 Estructura del Proyecto

```
paidp/
├── api-gateway/
├── ingestion-service/
├── ai-service/
├── decision-agent/
├── soar-service/
├── dashboard/
├── k8s/
├── monitoring/
├── docker-compose.yml
└── README.md
```

---

# 🔐 Seguridad

- Autenticación JWT
- Passwords hasheados con bcrypt
- Rate limiting con Redis
- Secrets en Kubernetes
- HTTPS en producción

---

# 📊 Monitoreo

### Prometheus

Métricas disponibles:

- `api_requests_total`
- `predictions_total`
- `decisions_total`
- `messages_ingested_total`

---

### Grafana

Dashboards incluidos:

- Sistema general
- Métricas de IA
- Análisis de amenazas
- Rendimiento de servicios

---

# 📚 Documentación de la API

Swagger UI:

```
http://localhost:8000/docs
```

---

# 👥 Contribuciones

Las contribuciones son bienvenidas.

1. Fork del repositorio
2. Crear una rama
3. Pull request

---

# 📄 Licencia

MIT License

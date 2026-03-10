# TEZCAT – Plataforma Autónoma Inteligente de Defensa contra Ciberamenazas
Sistema de detección de amenazas en tiempo real utilizando Inteligencia Artificial, mensajería distribuida y orquestación de respuestas de seguridad.

## Nota
Cambiar la parte de SECRET_KEY=Prueba123 en el docuemento ".env.example" y ".env" al momento de su lanzamiento. 

### Tecnologías

- **Frontend**: React + Material-UI
- **Backend**: FastAPI
- **IA**: PyTorch + HuggingFace (BERT para detección de toxicidad)
- **Mensajería**: Kafka
- **Base de datos**: PostgreSQL
- **Cache**: Redis
- **Contenedores**: Docker
- **Orquestación**: Kubernetes
- **Monitoreo**: Prometheus + Grafana
- **MLOps**: MLflow

### Componentes

1. **API Gateway** (Puerto 8000)
   - Autenticación JWT
   - Rate limiting con Redis
   - Endpoints RESTful
   - Métricas Prometheus

2. **Ingestion Service** (Puerto 8001)
   - Recibe datos del API Gateway
   - Publica mensajes en Kafka
   - Validación de datos

3. **AI Service**
   - Consume mensajes de Kafka
   - Análisis con modelo BERT pre-entrenado
   - Tracking con MLflow
   - Publica scores de amenaza

4. **Decision Agent**
   - Lógica de decisión basada en umbrales
   - Análisis de tendencias
   - Publicación de acciones

5. **SOAR Service**
   - Ejecución de respuestas automáticas
   - Registro de incidentes en PostgreSQL
   - Logs estructurados

6. **Dashboard**
   - Interfaz web React
   - Visualización de métricas
   - Historial de análisis
   - Gráficos en tiempo real

## Inicio Rápido

### Prerrequisitos

- Docker & Docker Compose
- Node.js 18+ (para desarrollo frontend)
- Python 3.10+ (para desarrollo backend)
- Kubernetes (opcional, para producción)

### Instalación con Docker Compose

```bash
# Clonar repositorio
git clone https://github.com/TraceVoid/PAIDP
cd ProyectoPapuOsi/paidp

# Construir e iniciar servicios
docker-compose up --build

# Acceder a:
# - Dashboard: http://localhost:3000
# - API Gateway: http://localhost:8000
# - MLflow: http://localhost:5000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001
```

### Desarrollo Local

#### Backend

```bash
# API Gateway
cd api-gateway
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Repetir para cada servicio
```

#### Frontend

```bash
cd dashboard
npm install
npm start
# Acceder a http://localhost:3000
```

## Uso

### 1. Registro/Login

```bash
# Registrar nuevo usuario
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","email":"user@example.com","password":"password123"}'
```

### 2. Análisis de Texto

```bash
# Obtener token
TOKEN=$(curl -X POST http://localhost:8000/token \
  -d "username=user1&password=password123" | jq -r .access_token)

# Analizar texto
curl -X POST http://localhost:8000/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Texto a analizar"}'
```

### 3. Consultar Historial

```bash
curl -X GET http://localhost:8000/history \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Estadísticas

```bash
curl -X GET http://localhost:8000/stats \
  -H "Authorization: Bearer $TOKEN"
```

## Configuración

### Variables de Entorno

Crear archivo `.env`:
```env
# API Gateway
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://admin:admin@postgres:5432/paidp

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

### Umbrales de Detección

En `decision-agent/main.py`:

```python
THRESHOLDS = {
    'block': 0.7,   # Score >= 70% → Bloquear
    'alert': 0.4,   # Score >= 40% → Alertar
    'allow': 0.0    # Score < 40% → Permitir
}
```

## Despliegue en Kubernetes

```bash
# Aplicar manifiestos
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/kafka.yaml
kubectl apply -f k8s/services.yaml

# Verificar despliegue
kubectl get pods -n paidp
kubectl get services -n paidp

# Obtener IP del API Gateway
kubectl get service api-gateway -n paidp
```

### Construir Imágenes para Kubernetes

```bash
# Construir todas las imágenes
docker build -t paidp/api-gateway:latest ./api-gateway
docker build -t paidp/ingestion-service:latest ./ingestion-service
docker build -t paidp/ai-service:latest ./ai-service
docker build -t paidp/decision-agent:latest ./decision-agent
docker build -t paidp/soar-service:latest ./soar-service
docker build -t paidp/dashboard:latest ./dashboard

# Push a registry (opcional)
docker push paidp/api-gateway:latest
# ... repetir para cada servicio
```

## Monitoreo

### Prometheus

Acceder a http://localhost:9090

Métricas disponibles:
- `api_requests_total` - Total de requests por endpoint
- `predictions_total` - Total de predicciones
- `decisions_total` - Total de decisiones por acción
- `messages_ingested_total` - Mensajes procesados

### Grafana

Acceder a http://localhost:3001 (admin/admin)

Dashboards incluidos:
- Sistema Overview
- Métricas de IA
- Análisis de Amenazas
- Performance de Servicios

### MLflow

Acceder a http://localhost:5000

Tracking de:
- Experimentos de modelo
- Métricas de predicción
- Artefactos de modelo
- Hiperparámetros

## Testing

```bash
# Tests unitarios
cd api-gateway
pytest tests/

# Tests de integración
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Load testing
k6 run tests/load-test.js
```

## Estructura del Proyecto

```
paidp/
├── api-gateway/          # API Gateway con FastAPI
├── ingestion-service/    # Servicio de ingesta
├── ai-service/          # Servicio de IA
├── decision-agent/      # Motor de decisiones
├── soar-service/        # Orquestación de respuestas
├── dashboard/           # Frontend React
├── k8s/                # Manifiestos Kubernetes
├── monitoring/         # Configuración Prometheus/Grafana
├── docker-compose.yml  # Orquestación Docker
```

## Seguridad

- JWT para autenticación
- Passwords hasheados con bcrypt
- Rate limiting con Redis
- HTTPS en producción (configurar ingress)
- Secrets en Kubernetes
- Network policies

Acceder a http://localhost:8000/docs para Swagger UI interactivo

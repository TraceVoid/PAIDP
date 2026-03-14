.PHONY: help build up down logs clean test k8s-deploy k8s-delete

help: ## Mostrar ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Construir imágenes Docker
	docker-compose build

up: ## Iniciar servicios
	docker-compose up -d
	@echo "Servicios iniciados:"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  API Gateway: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  MLflow: http://localhost:5000"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3001 (admin/admin)"

up-stepwise: ## Iniciar servicios paso a paso (recomendado si hay problemas)
	./start-stepwise.sh

up-simple: ## Iniciar con docker-compose simplificado
	docker-compose -f docker-compose.simple.yml up -d

down: ## Detener servicios
	docker-compose down

logs: ## Ver logs
	docker-compose logs -f

logs-api: ## Ver logs del API Gateway
	docker-compose logs -f api-gateway

logs-ai: ## Ver logs del AI Service
	docker-compose logs -f ai-service

# Kafka
diagnose-kafka: ## Diagnosticar problemas de Kafka
	./diagnose-kafka.sh

fix-kafka: ## Solución rápida para problemas de Kafka
	./fix-kafka.sh

kafka-topics: ## Listar topics de Kafka
	docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

kafka-logs: ## Ver logs de Kafka
	docker-compose logs -f kafka

kafka-test: ## Enviar mensaje de prueba a Kafka
	@echo "Enviando mensaje de prueba..."
	@echo '{"text":"Test message","user_id":1}' | docker-compose exec -T kafka kafka-console-producer --bootstrap-server localhost:9092 --topic incoming_messages
	@echo "Mensaje enviado. Verifica los logs de ai-service para ver el procesamiento"

kafka-consume: ## Consumir mensajes de incoming_messages
	docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic incoming_messages --from-beginning --max-messages 10

clean: ## Limpiar contenedores y volúmenes
	docker-compose down -v
	docker system prune -f

restart: down up ## Reiniciar servicios

ps: ## Ver estado de servicios
	docker-compose ps

test: ## Ejecutar tests
	@echo "Ejecutando tests..."
	# Agregar comandos de testing aquí

# Kubernetes
k8s-build: ## Construir imágenes para K8s
	docker build -t paidp/api-gateway:latest ./api-gateway
	docker build -t paidp/ingestion-service:latest ./ingestion-service
	docker build -t paidp/ai-service:latest ./ai-service
	docker build -t paidp/decision-agent:latest ./decision-agent
	docker build -t paidp/soar-service:latest ./soar-service
	docker build -t paidp/dashboard:latest ./dashboard

k8s-deploy: ## Desplegar en Kubernetes
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/postgres.yaml
	kubectl apply -f k8s/redis.yaml
	kubectl apply -f k8s/kafka.yaml
	kubectl apply -f k8s/services.yaml
	@echo "Esperando a que los pods estén listos..."
	kubectl wait --for=condition=ready pod -l app=postgres -n paidp --timeout=300s
	kubectl wait --for=condition=ready pod -l app=redis -n paidp --timeout=300s
	kubectl wait --for=condition=ready pod -l app=kafka -n paidp --timeout=300s

k8s-delete: ## Eliminar deployment de Kubernetes
	kubectl delete -f k8s/services.yaml
	kubectl delete -f k8s/kafka.yaml
	kubectl delete -f k8s/redis.yaml
	kubectl delete -f k8s/postgres.yaml
	kubectl delete -f k8s/namespace.yaml

k8s-status: ## Ver estado de K8s
	kubectl get all -n paidp

k8s-logs: ## Ver logs en K8s
	kubectl logs -f -l app=api-gateway -n paidp

# Desarrollo
dev-api: ## Iniciar API Gateway en modo desarrollo
	cd api-gateway && uvicorn main:app --reload --port 8000

dev-frontend: ## Iniciar frontend en modo desarrollo
	cd dashboard && npm start

# Base de datos
db-init: ## Inicializar base de datos
	docker-compose exec postgres psql -U admin -d paidp

db-reset: ## Resetear base de datos
	docker-compose down postgres
	docker volume rm paidp_postgres-data
	docker-compose up -d postgres

# Monitoring
grafana: ## Abrir Grafana
	open http://localhost:3001

prometheus: ## Abrir Prometheus
	open http://localhost:9090

mlflow: ## Abrir MLflow
	open http://localhost:5000

dashboard: ## Abrir Dashboard
	open http://localhost:3000

docs: ## Abrir API docs
	open http://localhost:8000/docs

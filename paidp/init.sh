#!/bin/bash

set -e

echo "========================================="
echo "  PAIDP - Inicialización del Proyecto"
echo "========================================="
echo ""

if ! command -v docker &> /dev/null; then
    echo "Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose no está instalado. Por favor instala Docker Compose primero."
    exit 1
fi

echo "Docker y Docker Compose detectados"
echo ""

if [ ! -f .env ]; then
    echo "Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo "Por favor edita el archivo .env con tus configuraciones"
else
    echo "Archivo .env ya existe"
fi

echo ""
echo "Construyendo imágenes Docker..."
docker-compose build

echo ""
echo "Iniciando servicios..."
docker-compose up -d

echo ""
echo "Esperando a que los servicios estén listos..."
sleep 20

echo ""
echo "Estado de los servicios:"
docker-compose ps

echo ""
echo "========================================="
echo "  Inicialización Completada"
echo "========================================="
echo ""
echo "Accede a los servicios en:"
echo ""
echo "  Dashboard:        http://localhost:3000"
echo "  API Gateway:      http://localhost:8000"
echo "  API Docs:         http://localhost:8000/docs"
echo "  MLflow:           http://localhost:5000"
echo "  Prometheus:       http://localhost:9090"
echo "  Grafana:          http://localhost:3001 (admin/admin)"
echo ""
echo "Para ver los logs: docker-compose logs -f"
echo "Para detener:      docker-compose down"
echo ""

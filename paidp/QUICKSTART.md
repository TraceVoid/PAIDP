# 🚀 Guía de Inicio Rápido - PAIDP

## Inicio en 5 minutos

### 1. Clonar y preparar

```bash
git clone <repo-url>
cd paidp
./init.sh
```

### 2. Acceder al Dashboard

Abre tu navegador en: http://localhost:3000

### 3. Crear cuenta

- Click en "Register"
- Ingresa username, email y password
- Click en "Register"

### 4. Analizar texto

- Ingresa texto en el área de análisis
- Click en "Analyze"
- Ver resultados y gráficos

## Comandos Útiles

```bash
# Ver logs
docker-compose logs -f

# Reiniciar servicios
docker-compose restart

# Detener todo
docker-compose down

# Limpiar todo (incluyendo datos)
docker-compose down -v
```

## Problemas Comunes

### Puerto 8000 ya en uso
```bash
# Cambiar puerto en docker-compose.yml
ports:
  - "8080:8000"  # Usar 8080 en lugar de 8000
```

### Servicios no inician
```bash
# Ver logs detallados
docker-compose logs [nombre-servicio]

# Reconstruir
docker-compose build --no-cache
docker-compose up -d
```

### Base de datos no responde
```bash
# Resetear base de datos
docker-compose down
docker volume rm paidp_postgres-data
docker-compose up -d
```

## Testing Rápido

### Con curl

```bash
# Registrar usuario
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"test123"}'

# Login
TOKEN=$(curl -X POST http://localhost:8000/token \
  -d "username=test&password=test123" | jq -r .access_token)

# Analizar texto
curl -X POST http://localhost:8000/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Este es un texto de prueba"}'

# Ver historial
curl -X GET http://localhost:8000/history \
  -H "Authorization: Bearer $TOKEN"

# Ver estadísticas
curl -X GET http://localhost:8000/stats \
  -H "Authorization: Bearer $TOKEN"
```

## Próximos Pasos

1. ✅ Explorar el dashboard en http://localhost:3000
2. ✅ Ver métricas en Grafana: http://localhost:3001
3. ✅ Revisar experimentos en MLflow: http://localhost:5000
4. ✅ Leer la documentación completa en README.md
5. ✅ Configurar alertas personalizadas
6. ✅ Desplegar en Kubernetes para producción

## Soporte

Si encuentras problemas:
1. Revisa los logs: `docker-compose logs -f`
2. Verifica el estado: `docker-compose ps`
3. Consulta README.md para más detalles
4. Abre un issue en el repositorio

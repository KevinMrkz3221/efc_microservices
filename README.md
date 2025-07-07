# EFC Microservice

Un microservicio de ejemplo desarrollado con FastAPI que permite gestionar items con operaciones CRUD completas.

## Características

- API RESTful con FastAPI
- Validación de datos con Pydantic
- Documentación automática con Swagger UI
- Operaciones CRUD (Create, Read, Update, Delete)
- Filtrado por categoría
- Endpoint de health check

## Instalación

1. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate     # En Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Ejecutar el microservicio

```bash
python main.py
```

O usando uvicorn directamente:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor estará disponible en: http://localhost:8000

## Documentación API

Una vez que el servidor esté ejecutándose, puedes acceder a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints disponibles

### Endpoints básicos
- `GET /` - Mensaje de bienvenida
- `GET /health` - Health check del servicio

### Gestión de items
- `GET /items` - Obtener todos los items
- `GET /items/{item_id}` - Obtener un item específico
- `POST /items` - Crear un nuevo item
- `PUT /items/{item_id}` - Actualizar un item existente
- `DELETE /items/{item_id}` - Eliminar un item
- `GET /items/category/{category}` - Obtener items por categoría

## Ejemplo de uso

### Crear un item
```bash
curl -X POST "http://localhost:8000/items" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Laptop",
       "description": "Laptop para desarrollo",
       "price": 1200.00,
       "category": "electronics"
     }'
```

### Obtener todos los items
```bash
curl -X GET "http://localhost:8000/items"
```

### Obtener items por categoría
```bash
curl -X GET "http://localhost:8000/items/category/electronics"
```

## Estructura del proyecto

```
EFC_microservice/
├── main.py           # Aplicación principal
├── requirements.txt  # Dependencias
└── README.md        # Documentación
```

## Modelo de datos

### Item
```json
{
  "id": 1,
  "name": "string",
  "description": "string",
  "price": 0.0,
  "category": "string"
}
```

### ItemCreate
```json
{
  "name": "string",
  "description": "string",
  "price": 0.0,
  "category": "string"
}
```
# efc_microservices

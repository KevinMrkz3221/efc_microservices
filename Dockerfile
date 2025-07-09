# Multi-stage build para optimizar el tamaño de la imagen
FROM python:3.11-slim as builder

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio para las dependencias
WORKDIR /app

# Instalar dependencias en un directorio temporal
COPY requirements.txt .
RUN pip install --user --no-cache-dir --verbose -r requirements.txt

# Imagen final
FROM python:3.11-slim

# Establecer variables de entorno para FastAPI
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH=/home/fastapi/.local/bin:$PATH

# Crear usuario no-root para seguridad
RUN groupadd -r fastapi && useradd -r -g fastapi fastapi

# Instalar curl para healthcheck
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder /root/.local /home/fastapi/.local

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios y establecer permisos
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R fastapi:fastapi /app && \
    chmod -R 755 /app

# Cambiar al usuario no-root
USER fastapi

# Exponer puerto
EXPOSE 8001

# Healthcheck para verificar que el servicio está funcionando
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Comando por defecto con configuración optimizada
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8001 --workers 32 --reload"]
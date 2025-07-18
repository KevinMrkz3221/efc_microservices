# Flujo Automático de Servicios de Pedimentos

## Descripción General

Después de completar exitosamente el procesamiento de un **pedimento completo**, el sistema ahora ejecuta automáticamente los siguientes servicios en segundo plano:

1. **Partidas** (si el pedimento tiene partidas)
2. **Remesas** (si el pedimento tiene remesas)
3. **Acuses** (si existen documentos digitalizados)

## Flujo de Ejecución

### 1. Ejecución del Pedimento Completo
```
POST /services/pedimento_completo
```

El endpoint procesa el pedimento completo y al finalizar exitosamente:
- ✅ Crea servicios adicionales automáticamente
- ✅ Programa la ejecución automática de servicios de seguimiento
- ✅ Retorna respuesta inmediata al cliente

### 2. Ejecución Automática en Segundo Plano

El sistema ejecuta automáticamente los siguientes servicios:

#### Partidas
- **Condición**: `numero_partidas > 0`
- **Servicio**: `POST /services/partidas`
- **Tipo**: 4

#### Remesas  
- **Condición**: `remesas = 1` en el XML del pedimento
- **Servicio**: `POST /services/remesas`
- **Tipo**: 5

#### Acuses
- **Condición**: Siempre se ejecuta (procesará solo si hay documentos digitalizados)
- **Servicio**: `POST /services/acuse`
- **Tipo**: 6

## Características del Sistema Automático

### ⏱️ Timing y Secuencia
- **Espera inicial**: 5 segundos después de completar el pedimento completo
- **Verificación de servicios**: Espera hasta 30 segundos a que se creen los servicios
- **Intervalo entre servicios**: 3 segundos entre cada ejecución
- **Ejecución secuencial**: Los servicios se ejecutan uno tras otro, no en paralelo

### 🔄 Sistema de Reintentos
- **Reintentos automáticos**: Hasta 2 reintentos por servicio
- **Backoff exponencial**: Tiempo de espera incrementa exponencialmente (2, 4, 8... segundos, máximo 30)
- **Tolerancia a fallos**: Si un servicio falla, continúa con los siguientes

### 📊 Logging y Monitoreo
- **Logging detallado**: Cada paso del proceso se registra con emojis para fácil identificación
- **Resumen de ejecución**: Al final se muestra un resumen con éxitos/fallos
- **Callback de finalización**: Notificación cuando termine todo el proceso

## Respuesta del Endpoint

El endpoint `/services/pedimento_completo` ahora retorna información adicional:

```json
{
  "success": true,
  "message": "Pedimento completo procesado exitosamente. Servicios automáticos programados.",
  "data": {
    "organizacion": "uuid-organizacion",
    "servicio": 123,
    "estado": 3,
    "pedimento_id": "uuid-pedimento",
    "documento": { ... },
    "xml_content": { ... },
    "edocuments": [ ... ],
    "servicios_adicionales": {
      "servicio_partidas": 124,
      "servicio_acuse": 125,
      "servicio_estado_pedimento": 126,
      "servicio_edocument": 127,
      "servicio_remesas": 128  // Solo si aplica
    },
    "servicios_automaticos": {
      "programados": true,
      "remesas_programadas": true,
      "partidas_programadas": true,
      "acuses_programados": true,
      "mensaje": "Los servicios de partidas, remesas y acuses se ejecutarán automáticamente en segundo plano"
    }
  }
}
```

## Consulta de Estado

Para verificar el progreso de los servicios automáticos:

```
GET /services/status/{pedimento_id}?organizacion={organizacion_id}
```

### Respuesta de Estado
```json
{
  "success": true,
  "pedimento_id": "uuid-pedimento",
  "organizacion": "uuid-organizacion",
  "summary": {
    "total_services": 6,
    "completed_services": 4,
    "in_progress_services": 1,
    "error_services": 1,
    "completion_percentage": 66.7
  },
  "services": {
    "pedimento_completo": {
      "exists": true,
      "service_id": 123,
      "estado": 3,
      "estado_nombre": "FINALIZADO"
    },
    "partidas": {
      "exists": true,
      "service_id": 124,
      "estado": 3,
      "estado_nombre": "FINALIZADO"
    },
    "remesas": {
      "exists": true,
      "service_id": 128,
      "estado": 2,
      "estado_nombre": "EN_PROCESO"
    },
    "acuse": {
      "exists": true,
      "service_id": 125,
      "estado": 4,
      "estado_nombre": "ERROR"
    }
  }
}
```

## Estados de Servicio

| Estado | Código | Descripción |
|--------|--------|-------------|
| CREADO | 1 | Servicio creado, esperando ejecución |
| EN_PROCESO | 2 | Servicio ejecutándose actualmente |
| FINALIZADO | 3 | Servicio completado exitosamente |
| ERROR | 4 | Servicio falló después de reintentos |

## Logs de Ejemplo

```
2024-07-10 12:00:15 INFO - Pedimento completo procesado exitosamente - Servicio: 123
2024-07-10 12:00:16 INFO - Programando servicios automáticos - Remesas: True, Partidas: True
2024-07-10 12:00:16 INFO - Servicios automáticos programados exitosamente para pedimento uuid-pedimento
2024-07-10 12:00:21 INFO - Esperando a que se completen las creaciones de servicios...
2024-07-10 12:00:26 INFO - 🔄 Iniciando procesamiento de partidas...
2024-07-10 12:00:26 INFO - Servicio tipo 4 encontrado para pedimento uuid-pedimento
2024-07-10 12:00:45 INFO - ✅ Servicio partidas completado exitosamente
2024-07-10 12:00:48 INFO - 🔄 Iniciando procesamiento de remesas...
2024-07-10 12:01:05 INFO - ✅ Servicio remesas completado exitosamente
2024-07-10 12:01:08 INFO - 🔄 Iniciando procesamiento de acuse...
2024-07-10 12:01:25 INFO - ✅ Servicio acuse completado exitosamente
2024-07-10 12:01:25 INFO - 🎉 Ejecución automática completada exitosamente - 3/3 (100%)
2024-07-10 12:01:25 INFO - Servicios automáticos completados para pedimento uuid-pedimento: 3/3 exitosos
```

## Beneficios

### ✨ Para el Usuario
- **Respuesta inmediata**: No espera a que se completen todos los servicios
- **Procesamiento automático**: No necesita ejecutar manualmente cada servicio
- **Tolerancia a fallos**: Los errores en servicios individuales no afectan el flujo completo

### 🔧 Para el Sistema
- **Desacoplamiento**: El pedimento completo no depende de los servicios secundarios
- **Escalabilidad**: Procesamiento en segundo plano no bloquea recursos
- **Monitoreo**: Logging detallado para debugging y análisis

### 📈 Para el Negocio
- **Eficiencia**: Automatización reduce tiempo de procesamiento manual
- **Confiabilidad**: Sistema de reintentos asegura máxima tasa de éxito
- **Visibilidad**: Estado en tiempo real de todos los servicios

## Consideraciones Técnicas

### Memoria y Recursos
- Las tareas en segundo plano se ejecutan en el mismo proceso
- Uso mínimo de memoria adicional
- Timeout automático para evitar tareas colgadas

### Manejo de Errores
- Errores en servicios automáticos no afectan la respuesta del pedimento completo
- Logs detallados para debugging
- Reintentos automáticos con backoff exponencial

### Concurrencia
- Ejecución secuencial evita sobrecarga del sistema VUCEM
- Intervalos de espera configurables
- Control de recursos mediante timeouts

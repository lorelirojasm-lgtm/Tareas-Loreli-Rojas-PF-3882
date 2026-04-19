# Sistema de Reserva de Citas Médicas - MediCitas

## Una plataforma de reserva de citas médicas

```mermaid
flowchart TD
    A["Médicos (REST sobre FastAPI)"]
    A-->B["Citas (GraphQL sobre Flask)"]
    B-->D["Notificaciones (REST sobre Flask)"]

```

- URL del servicio de Médicos: http://localhost:9090/docs
- URL del servicio de Citas: http://localhost:5001/graphql
- URL del servicio de Notificaciones: http://localhost:5002/apidocs

## Descripción de servicios

### Médicos (FastAPI)

- Gestiona el registro de médicos, especialidades y horarios disponibles
- Proporciona endpoints REST para consultar médicos y disponibilidad
- Base de datos: Información de médicos y sus horarios

### Citas (GraphQL - Flask)

- Gestiona la reserva y cancelación de citas médicas
- Proporciona interfaz GraphQL para consultas complejas de citas
- Se comunica con Médicos para validar disponibilidad
- Publica eventos de citas creadas/canceladas

### Notificaciones (Flask)

- Envía confirmaciones y recordatorios a pacientes
- Proporciona endpoints REST para gestionar notificaciones
- Se suscribe a eventos de Citas
- Base de datos: Historial de notificaciones enviadas

## Flujo de comunicación

1. **Cliente** → **Médicos**: Consulta disponibilidad
2. **Cliente** → **Citas**: Reserva una cita (valida con Médicos)
3. **Citas** → **Notificaciones**: Publica evento de cita creada
4. **Notificaciones**: Envía confirmación y recordatorios

## Contextos delimitados

Consulta la documentación en Tarea 1 para más detalles:

- [Contexto de Médicos](../tarea1/01-contexto-medicos.md)
- [Contexto de Citas](../tarea1/02-contexto-citas.md)
- [Contexto de Notificaciones](../tarea1/03-contexto-notificaciones.md)

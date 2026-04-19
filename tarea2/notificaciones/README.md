# Servicio de Notificaciones - MediCitas

API REST para gestionar notificaciones, confirmaciones y recordatorios de citas médicas.

## Endpoints

- `GET /notificaciones` - Lista todas las notificaciones
- `GET /notificaciones/<id>` - Obtiene una notificación específica
- `GET /notificaciones/cita/<cita_id>` - Obtiene notificaciones de una cita
- `GET /notificaciones/paciente/<paciente>` - Obtiene notificaciones de un paciente
- `POST /notificaciones` - Crea una nueva notificación

## Tecnología

- Framework: Flask
- Puerto: 5002
- Documentación interactiva: http://localhost:5002 (con Flask-RESTX u otra)

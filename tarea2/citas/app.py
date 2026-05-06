from flask import Flask
import strawberry
from strawberry.flask.views import GraphQLView
from typing import Optional
import logging
import os
import requests
from datetime import datetime, timezone


class CitaError(Exception):
    """Errores de negocio del servicio de Citas."""

# URLs de los servicios dependientes (resolución por DNS interno de Docker Compose)
MEDICOS_URL = os.getenv("MEDICOS_URL", "http://medicos:9090")
NOTIFICACIONES_URL = os.getenv("NOTIFICACIONES_URL", "http://notificaciones:5002")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Datos de ejemplo
citas_data = [
    {
        "id": 1,
        "medico_id": 1,
        "paciente": "Carlos Mendez",
        "fecha": "2026-04-20",
        "hora": "10:00",
        "estado": "confirmada"
    },
    {
        "id": 2,
        "medico_id": 2,
        "paciente": "Ana García",
        "fecha": "2026-04-21",
        "hora": "14:00",
        "estado": "confirmada"
    }
]

@strawberry.type
class Cita:
    id: int
    medico_id: int
    paciente: str
    fecha: str
    hora: str
    estado: str

@strawberry.type
class Query:
    @strawberry.field
    def todas_citas(self) -> list[Cita]:
        """Retorna todas las citas"""
        app.logger.info("Retornando lista de citas con tamaño: %d", len(citas_data))
        return [Cita(
            id=c["id"],
            medico_id=c["medico_id"],
            paciente=c["paciente"],
            fecha=c["fecha"],
            hora=c["hora"],
            estado=c["estado"]
        ) for c in citas_data]

    @strawberry.field
    def cita_por_id(self, cita_id: int) -> Optional[Cita]:
        """Retorna una cita específica por ID"""
        for c in citas_data:
            if c["id"] == cita_id:
                app.logger.info("Cita con id %d encontrada", cita_id)
                return Cita(
                    id=c["id"],
                    medico_id=c["medico_id"],
                    paciente=c["paciente"],
                    fecha=c["fecha"],
                    hora=c["hora"],
                    estado=c["estado"]
                )
        app.logger.info("Cita con id %d NO encontrada", cita_id)
        return None

    @strawberry.field
    def citas_por_medico(self, medico_id: int) -> list[Cita]:
        """Retorna citas de un médico específico"""
        resultado = [c for c in citas_data if c["medico_id"] == medico_id]
        app.logger.info("Retornando %d citas para médico %d", len(resultado), medico_id)
        return [Cita(
            id=c["id"],
            medico_id=c["medico_id"],
            paciente=c["paciente"],
            fecha=c["fecha"],
            hora=c["hora"],
            estado=c["estado"]
        ) for c in resultado]

    @strawberry.field
    def citas_por_paciente(self, paciente: str) -> list[Cita]:
        """Retorna citas de un paciente específico"""
        resultado = [c for c in citas_data if c["paciente"].lower() == paciente.lower()]
        app.logger.info("Retornando %d citas para paciente %s", len(resultado), paciente)
        return [Cita(
            id=c["id"],
            medico_id=c["medico_id"],
            paciente=c["paciente"],
            fecha=c["fecha"],
            hora=c["hora"],
            estado=c["estado"]
        ) for c in resultado]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def crear_cita(
        self,
        medico_id: int,
        paciente: str,
        fecha: str,
        hora: str,
    ) -> Cita:
        """Crea una nueva cita validando contra el servicio de Médicos
        y notificando al servicio de Notificaciones (comunicación entre servicios)."""

        # 1) Validar médico contra el servicio de Médicos (REST/FastAPI)
        try:
            resp = requests.get(f"{MEDICOS_URL}/medicos/{medico_id}", timeout=5)
        except requests.RequestException as exc:
            app.logger.error("Error contactando servicio Médicos: %s", exc)
            raise CitaError("Servicio de Médicos no disponible") from exc

        if resp.status_code != 200:
            app.logger.warning("Médico %d no encontrado (status=%s)", medico_id, resp.status_code)
            raise CitaError(f"Médico {medico_id} no existe")

        medico = resp.json()
        if not medico.get("disponible", False):
            raise CitaError(f"Médico {medico_id} no está disponible")

        # 2) Persistir la cita en memoria
        nueva_id = max((c["id"] for c in citas_data), default=0) + 1
        nueva_cita = {
            "id": nueva_id,
            "medico_id": medico_id,
            "paciente": paciente,
            "fecha": fecha,
            "hora": hora,
            "estado": "confirmada",
        }
        citas_data.append(nueva_cita)
        app.logger.info("Cita %d creada para paciente %s con médico %d", nueva_id, paciente, medico_id)

        # 3) Notificar al servicio de Notificaciones (REST/Flask)
        try:
            requests.post(
                f"{NOTIFICACIONES_URL}/notificaciones",
                json={
                    "cita_id": nueva_id,
                    "paciente": paciente,
                    "tipo": "confirmacion",
                    "mensaje": f"Tu cita ha sido confirmada para el {fecha} a las {hora} con {medico.get('nombre', 'el médico')}",
                    "enviado": True,
                    "fecha_envio": datetime.now(timezone.utc).isoformat(),
                },
                timeout=5,
            )
            app.logger.info("Notificación enviada para cita %d", nueva_id)
        except requests.RequestException as exc:
            # No abortamos la cita si Notificaciones falla; sólo lo registramos.
            app.logger.error("Error notificando creación de cita %d: %s", nueva_id, exc)

        return Cita(**nueva_cita)

    @strawberry.mutation
    def cancelar_cita(self, cita_id: int) -> Optional[Cita]:
        """Cancela una cita existente y notifica al servicio de Notificaciones."""
        for c in citas_data:
            if c["id"] == cita_id:
                c["estado"] = "cancelada"
                app.logger.info("Cita %d cancelada", cita_id)
                try:
                    requests.post(
                        f"{NOTIFICACIONES_URL}/notificaciones",
                        json={
                            "cita_id": cita_id,
                            "paciente": c["paciente"],
                            "tipo": "cancelacion",
                            "mensaje": f"Tu cita del {c['fecha']} a las {c['hora']} ha sido cancelada",
                            "enviado": True,
                            "fecha_envio": datetime.now(timezone.utc).isoformat(),
                        },
                        timeout=5,
                    )
                except requests.RequestException as exc:
                    app.logger.error("Error notificando cancelación de cita %d: %s", cita_id, exc)
                return Cita(**c)
        return None


schema = strawberry.Schema(query=Query, mutation=Mutation)

app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view("graphql_view", schema=schema),
)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

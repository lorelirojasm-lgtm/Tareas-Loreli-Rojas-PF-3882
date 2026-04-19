from flask import Flask
import strawberry
from strawberry.flask.views import GraphQLView
from typing import Optional
import logging

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

schema = strawberry.Schema(query=Query)

app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view("graphql_view", schema=schema),
)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

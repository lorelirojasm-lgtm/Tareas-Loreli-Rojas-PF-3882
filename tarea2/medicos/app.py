from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Médicos API",
    description="API REST para gestionar médicos, especialidades y horarios",
    version="1.0.0"
)

# Datos de ejemplo
medicos = [
    {
        "id": 1,
        "nombre": "Dr. Juan García",
        "especialidad": "Cardiología",
        "horario_inicio": "08:00",
        "horario_fin": "17:00",
        "disponible": True
    },
    {
        "id": 2,
        "nombre": "Dra. María López",
        "especialidad": "Dermatología",
        "horario_inicio": "09:00",
        "horario_fin": "18:00",
        "disponible": True
    }
]

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Servicio de Médicos - MediCitas"}

@app.get("/medicos", tags=["Médicos"])
def listar_medicos():
    """Retorna la lista de todos los médicos disponibles"""
    return medicos

@app.get("/medicos/{medico_id}", tags=["Médicos"])
def obtener_medico(medico_id: int):
    """Retorna un médico específico por ID"""
    for medico in medicos:
        if medico["id"] == medico_id:
            return medico
    return JSONResponse(status_code=404, content={"error": "Médico no encontrado"})

@app.get("/especialidades", tags=["Especialidades"])
def listar_especialidades():
    """Retorna lista de especialidades"""
    especialidades = list(set(medico["especialidad"] for medico in medicos))
    return {"especialidades": especialidades}

@app.get("/medicos/especialidad/{especialidad}", tags=["Médicos"])
def medicos_por_especialidad(especialidad: str):
    """Retorna médicos de una especialidad específica"""
    resultado = [m for m in medicos if m["especialidad"].lower() == especialidad.lower()]
    return {"especialidad": especialidad, "medicos": resultado}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)

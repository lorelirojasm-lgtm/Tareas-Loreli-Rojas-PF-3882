# Tarea 4 — Pruebas de Contrato con Pact

Pruebas de contrato dirigidas por el consumidor (Consumer-Driven Contract Testing)
entre el servicio **Citas** (consumidor) y el servicio **Médicos** (proveedor) de la tarea 3.

## ⚠️ Requisito: ejecutar con Docker

Las pruebas **deben correrse con Docker Compose**.

La librería `pact-python` depende de binarios nativos (`pact_ffi`, basado en Rust)
que no pueden cargarse en Windows de forma local — esto afecta tanto a esta carpeta
como a la carpeta `10-pruebas` del curso, ya que ambas usan la misma librería.
El error que aparece en Windows es:

```
ImportError: DLL load failed while importing ffi: A dynamic link library (DLL) initialization routine failed.
```

Como mi computadora es Windows y no cuenta con el entorno nativo requerido,
opté por ejecutar las pruebas dentro de un contenedor Docker (Linux), donde
`pact-python` funciona correctamente sin ninguna configuración adicional.

## Integración bajo prueba

En la tarea 3, cuando se ejecuta la mutación `crearCita`, el servicio Citas
llama al servicio Médicos vía REST para validar que el médico existe y está disponible:

```
Citas (Flask/GraphQL) ──GET /medicos/{id}──► Médicos (FastAPI)
                       ◄── {id, nombre, disponible, ...} ──
```

Este contrato documenta exactamente qué espera Citas de Médicos, de modo que
ambos servicios puedan cambiar de forma independiente sin romperse mutuamente.

## Interacciones del contrato

| # | Request | Status | Descripción |
|---|---------|--------|-------------|
| 1 | `GET /medicos` | 200 | Lista de médicos registrados |
| 2 | `GET /medicos/1` | 200 | Médico existente y disponible |
| 3 | `GET /medicos/999` | 404 | Médico no encontrado |
| 4 | `GET /especialidades` | 200 | Lista de especialidades |

## Cómo ejecutar las pruebas

### Requisitos previos

- Docker Desktop instalado y corriendo

### Paso 1 — Construir y ejecutar

Desde la carpeta `tarea4/`:

```bash
docker compose up --build
```

Esto levanta dos contenedores automáticamente:
- `medicos_pact`: el servicio FastAPI de Médicos (construido desde `tarea3/medicos`)
- `pact_tests`: ejecuta `pytest tests/pact -v` contra el servicio real

Resultado esperado:

```
tests/pact/test_citas_medicos_pact.py::TestCitasConsumer::test_listar_medicos            PASSED
tests/pact/test_citas_medicos_pact.py::TestCitasConsumer::test_obtener_medico_disponible PASSED
tests/pact/test_citas_medicos_pact.py::TestCitasConsumer::test_medico_no_encontrado      PASSED
tests/pact/test_citas_medicos_pact.py::TestCitasConsumer::test_listar_especialidades     PASSED
tests/pact/test_citas_medicos_pact.py::TestMedicosProvider::test_medicos_honours_pact    PASSED

5 passed in 3.98s
```

### Paso 2 — Ver los logs (opcional)

```bash
docker compose logs pact-tests
```

### Paso 3 — Limpiar contenedores

```bash
docker compose down
```

## Archivos generados

Después de ejecutar las pruebas, se crea el archivo de contrato:

```
tarea4/pacts/CitasService-MedicosService.json
```

Este archivo JSON documenta las 4 interacciones acordadas entre Citas y Médicos.

## Estructura del proyecto

```
tarea4/
├── Dockerfile               # Imagen para ejecutar las pruebas en Docker
├── docker-compose.yml       # Orquesta servicio Médicos + runner de pruebas
├── requirements.txt         # Dependencias Python
├── setup.cfg                # Configuración de pytest
├── pacts/                   # Contratos generados (JSON)
│   └── CitasService-MedicosService.json
└── tests/
    └── pact/
        └── test_citas_medicos_pact.py   # Pruebas de contrato
```

## Flujo de pruebas

```
docker compose up --build
  │
  ├── medicos_pact (contenedor)
  │     └── uvicorn → FastAPI app de tarea3/medicos en puerto 9090
  │
  └── pact_tests (contenedor)
        │
        ├── pact_mock_server (fixture, scope=session)
        │     └── Levanta mock de Pact en puerto 5300
        │
        ├── TestCitasConsumer              ← Fase 1: Consumidor (vs mock)
        │     ├── test_listar_medicos
        │     ├── test_obtener_medico_disponible
        │     ├── test_medico_no_encontrado
        │     └── test_listar_especialidades
        │           → genera pacts/CitasService-MedicosService.json
        │
        └── TestMedicosProvider            ← Fase 2: Proveedor (vs Médicos real)
              └── test_medicos_honours_pact
                    → verifica las 4 interacciones contra medicos:9090
```

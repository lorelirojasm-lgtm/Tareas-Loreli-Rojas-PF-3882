"""
Pruebas de Contrato Dirigidas por el Consumidor (Consumer-Driven Contract Testing)
entre el servicio Citas (consumidor) y el servicio Médicos (proveedor).

Usa pact-python v1 (API: Consumer/Provider/Like/EachLike).
Esta versión es compatible con Windows sin necesidad de pact_ffi (DLL Rust).

═══════════════════════════════════════════════════════════════════════════════
CONTEXTO
═══════════════════════════════════════════════════════════════════════════════

En tarea3, cuando Citas ejecuta la mutación crearCita llama a Médicos (REST):

  CitasService ──GET /medicos/{id}──► MedicosService (FastAPI)
               ◄─── {id, nombre, disponible, ...} ─────────

Este contrato documenta exactamente qué espera Citas de Médicos para que
ambos servicios evolucionen de forma independiente.

═══════════════════════════════════════════════════════════════════════════════
INTERACCIONES DEL CONTRATO
═══════════════════════════════════════════════════════════════════════════════

  1. GET /medicos         → 200  lista de médicos (array)
  2. GET /medicos/1       → 200  médico existente con disponible=True
  3. GET /medicos/999     → 404  {"error": "Médico no encontrado"}
  4. GET /especialidades  → 200  {"especialidades": [...]}

═══════════════════════════════════════════════════════════════════════════════
FLUJO DE EJECUCIÓN
═══════════════════════════════════════════════════════════════════════════════

  Fixture pact_mock_server (scope=session):
    pact.start_service() → arranca el mock de Pact (proceso interno)

  Fase 1 — TestCitasConsumer:
    Cada test registra UNA interacción con pact.given().upon_receiving()...
    El bloque "with pact:" hace dos cosas:
      a) Envía la interacción al mock (setup)
      b) Al salir, verifica que fue llamada y escribe al archivo de contrato
    La app Médicos NO está corriendo.

  Fase 2 — TestMedicosProvider:
    Levanta la app Médicos (uvicorn en hilo) o usa MEDICOS_URL (Docker).
    Verifier replay cada interacción del archivo JSON contra el proveedor real.

  Fixture teardown:
    pact.stop_service() → detiene el proceso del mock.
"""
import importlib.util
import os
import pathlib
import threading
import time

import pytest
import requests
import uvicorn
from pact import Consumer, Provider, EachLike, Like, Verifier

# ── Rutas ─────────────────────────────────────────────────────────────────────

#   test file: tarea4/tests/pact/test_citas_medicos_pact.py
#   parents[2] → tarea4/
#   parents[3] → PF-3882/  (raíz del repositorio)
_PROJECT_ROOT = pathlib.Path(__file__).parents[2]
_REPO_ROOT    = pathlib.Path(__file__).parents[3]
_MEDICOS_APP  = _REPO_ROOT / "tarea3" / "medicos" / "app.py"

PACT_DIR  = str(_PROJECT_ROOT / "pacts")
PACT_FILE = str(_PROJECT_ROOT / "pacts" / "CitasService-MedicosService.json")

MOCK_HOST     = "localhost"
MOCK_PORT     = 5300
PROVIDER_PORT = 5301
MOCK_URL      = f"http://{MOCK_HOST}:{MOCK_PORT}"

# ── Objeto Pact (API v1) ───────────────────────────────────────────────────────

# Consumer("consumidor").has_pact_with(Provider("proveedor"), ...)
# Nombre del archivo generado: CitasService-MedicosService.json
pact = (
    Consumer("CitasService")
    .has_pact_with(
        Provider("MedicosService"),
        host_name=MOCK_HOST,
        port=MOCK_PORT,
        pact_dir=PACT_DIR,
        log_dir=PACT_DIR,
    )
)


# ── Fixture del mock ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def pact_mock_server():
    """
    Levanta y detiene el servidor mock de Pact para toda la sesión.

    pact.start_service() arranca el proceso interno del mock (pact-ruby-standalone
    empaquetado con pact-python, no requiere Ruby instalado por separado).

    scope="session" → el mock corre una sola vez para todos los tests.
    El archivo de contrato se escribe progresivamente en cada bloque "with pact:".
    """
    pathlib.Path(PACT_DIR).mkdir(parents=True, exist_ok=True)
    pact.start_service()
    yield
    pact.stop_service()


# ── Fase 1: Pruebas del Consumidor ────────────────────────────────────────────

class TestCitasConsumer:
    """
    Pruebas desde el punto de vista del CONSUMIDOR (CitasService).

    Cada test define UNA interacción del contrato y la verifica contra el mock.
    La app Médicos real NO está corriendo; el mock responde según la configuración.

    El bloque "with pact:":
      - Entrada (__enter__): registra la interacción en el mock server.
      - Salida  (__exit__):  verifica que fue llamada y escribe al pact file.

    Propósito:
      1. Documentar cómo Citas llama a Médicos (método, path, body esperado).
      2. Generar el archivo de contrato JSON.
      3. Verificar que Citas procesa las respuestas correctamente.
    """

    def test_listar_medicos(self, pact_mock_server):
        """Citas obtiene la lista de médicos para mostrar disponibilidad."""
        # EachLike({template}): array donde cada elemento tiene esa estructura.
        # Like(value): el campo existe con el mismo tipo que value.
        # "disponible": True → valor exacto porque Citas verifica este campo.
        expected = EachLike({
            "id":             Like(1),
            "nombre":         Like("Dr. Juan García"),
            "especialidad":   Like("Cardiología"),
            "horario_inicio": Like("08:00"),
            "horario_fin":    Like("17:00"),
            "disponible":     True,
        })

        (
            pact
            .given("existen medicos registrados")
            .upon_receiving("GET /medicos retorna lista de medicos")
            .with_request("GET", "/medicos")
            .will_respond_with(200, body=expected)
        )

        with pact:
            r = requests.get(f"{MOCK_URL}/medicos")
            assert r.status_code == 200
            medicos = r.json()
            assert isinstance(medicos, list)
            assert len(medicos) >= 1
            assert isinstance(medicos[0]["id"], int)
            assert medicos[0]["disponible"] is True

    def test_obtener_medico_disponible(self, pact_mock_server):
        """Citas valida un médico antes de crear una cita."""
        # "id": 1 → valor exacto: Citas verifica que el ID devuelto coincida.
        # Like(...) → matcher de tipo para campos con valores variables.
        expected = {
            "id":             1,
            "nombre":         Like("Dr. Juan García"),
            "especialidad":   Like("Cardiología"),
            "horario_inicio": Like("08:00"),
            "horario_fin":    Like("17:00"),
            "disponible":     True,
        }

        (
            pact
            .given("el medico con id 1 existe y esta disponible")
            .upon_receiving("GET /medicos/1 retorna medico disponible")
            .with_request("GET", "/medicos/1")
            .will_respond_with(200, body=expected)
        )

        with pact:
            r = requests.get(f"{MOCK_URL}/medicos/1")
            assert r.status_code == 200
            medico = r.json()
            assert medico["id"] == 1
            assert medico["disponible"] is True
            assert isinstance(medico["nombre"], str)
            assert isinstance(medico["especialidad"], str)

    def test_medico_no_encontrado(self, pact_mock_server):
        """Citas maneja el caso donde el médico no existe."""
        # DIFERENCIA CLAVE: Médicos usa JSONResponse manual → {"error": "..."}
        # FastAPI HTTPException devolvería {"detail": "..."} — aquí es "error".
        expected = {
            "error": Like("Médico no encontrado"),
        }

        (
            pact
            .given("no existe medico con id 999")
            .upon_receiving("GET /medicos/999 retorna 404")
            .with_request("GET", "/medicos/999")
            .will_respond_with(404, body=expected)
        )

        with pact:
            r = requests.get(f"{MOCK_URL}/medicos/999")
            assert r.status_code == 404
            body = r.json()
            assert "error" in body
            assert isinstance(body["error"], str)

    def test_listar_especialidades(self, pact_mock_server):
        """Citas consulta especialidades para el formulario de búsqueda."""
        # EachLike("Cardiología"): array donde cada elemento es un string.
        expected = {
            "especialidades": EachLike("Cardiología"),
        }

        (
            pact
            .given("existen medicos con especialidades registradas")
            .upon_receiving("GET /especialidades retorna lista de especialidades")
            .with_request("GET", "/especialidades")
            .will_respond_with(200, body=expected)
        )

        with pact:
            r = requests.get(f"{MOCK_URL}/especialidades")
            assert r.status_code == 200
            data = r.json()
            assert "especialidades" in data
            assert isinstance(data["especialidades"], list)
            assert len(data["especialidades"]) >= 1
            assert all(isinstance(e, str) for e in data["especialidades"])


# ── Fase 2: Verificación del Proveedor ───────────────────────────────────────

class _UvicornServer(uvicorn.Server):
    """
    Deshabilita el manejo de señales para correr uvicorn en un hilo secundario.
    El servidor se detiene externamente con server.should_exit = True.
    """

    def install_signal_handlers(self) -> None:
        # Intencionalmente vacío: en hilos secundarios Python no puede
        # manejar señales del SO (SIGINT/SIGTERM). Se detiene con should_exit.
        pass


def _importar_medicos_app():
    """
    Importa la FastAPI app de tarea3/medicos/app.py sin modificar sys.path.
    Usa importlib para evitar conflictos de nombre con otros módulos.
    """
    spec   = importlib.util.spec_from_file_location("medicos_app", _MEDICOS_APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture(scope="class")
def medicos_provider_url(pact_mock_server):
    """
    Proporciona la URL del proveedor Médicos real para la verificación.

    pact_mock_server se incluye como parámetro para garantizar que los tests
    de consumidor (que escriben el pact file) hayan corrido primero.

    Modo Docker (MEDICOS_URL definida):
      El servicio medicos corre como contenedor separado. Se usa su URL.

    Modo local (MEDICOS_URL no definida):
      Se importa tarea3/medicos/app.py y se levanta uvicorn en un hilo.
      La app usa datos en memoria: no necesita base de datos ni RabbitMQ.
    """
    external_url = os.getenv("MEDICOS_URL")
    if external_url:
        yield external_url
        return

    app    = _importar_medicos_app()
    config = uvicorn.Config(app, host="localhost", port=PROVIDER_PORT, log_level="error")
    server = _UvicornServer(config)

    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(0.5)

    yield f"http://localhost:{PROVIDER_PORT}"

    server.should_exit = True
    t.join(timeout=2)


class TestMedicosProvider:
    """
    Verifica que el proveedor real (MedicosService) cumple el contrato.

    Pact Verifier reproduce las 4 interacciones del archivo JSON generado en
    la Fase 1 contra la app Médicos real y compara las respuestas.

    Los estados ('given') se satisfacen automáticamente: Médicos tiene datos
    en memoria con los médicos ID 1 y 2 siempre disponibles.
    No se necesita ningún setup adicional de estado.
    """

    def test_medicos_honours_pact(self, medicos_provider_url):
        # Verifier(provider, provider_base_url) crea el verificador v1.
        # verify_pacts(pact_file) reproduce cada interacción y devuelve
        # (output_string, return_code). return_code == 0 significa éxito.
        verifier = Verifier(
            provider="MedicosService",
            provider_base_url=medicos_provider_url,
        )
        # verify_pacts devuelve (returncode: int, stdout: str)
        returncode, output = verifier.verify_pacts(PACT_FILE)

        assert returncode == 0, (
            f"El proveedor MedicosService no satisfizo el contrato "
            f"(código {returncode}):\n{output}"
        )

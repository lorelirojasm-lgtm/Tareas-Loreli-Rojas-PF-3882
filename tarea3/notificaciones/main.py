from flask import Flask, jsonify, request
from flasgger import Swagger
from dotenv import load_dotenv
import json
import logging
import os
import threading
import time
import pika

load_dotenv("config.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

app = Flask(__name__)
swagger = Swagger(app)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
NOTIFICACIONES_QUEUE = os.getenv("NOTIFICACIONES_QUEUE", "cola-notificaciones")

# Datos de ejemplo - historial de notificaciones
notificaciones = [
    {
        "id": 1,
        "cita_id": 1,
        "paciente": "Carlos Mendez",
        "tipo": "confirmacion",
        "mensaje": "Tu cita ha sido confirmada para el 2026-04-20 a las 10:00",
        "enviado": True,
        "fecha_envio": "2026-04-18T08:30:00"
    },
    {
        "id": 2,
        "cita_id": 2,
        "paciente": "Ana García",
        "tipo": "recordatorio",
        "mensaje": "Recordatorio: Tu cita es mañana a las 14:00",
        "enviado": True,
        "fecha_envio": "2026-04-20T08:00:00"
    }
]

@app.route("/", methods=["GET"])
def index():
    """Endpoint raíz"""
    return jsonify({"message": "Servicio de Notificaciones - MediCitas", "swagger_ui": "/apidocs"})

@app.route("/notificaciones", methods=["GET"])
def listar_notificaciones():
    """
    Retorna el historial de notificaciones
    ---
    responses:
      200:
        description: Lista de notificaciones
    """
    return jsonify({"notificaciones": notificaciones}), 200

@app.route("/notificaciones/<int:notificacion_id>", methods=["GET"])
def obtener_notificacion(notificacion_id):
    """
    Retorna una notificación específica por ID
    ---
    parameters:
      - name: notificacion_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Notificación encontrada
      404:
        description: Notificación no encontrada
    """
    for notif in notificaciones:
        if notif["id"] == notificacion_id:
            return jsonify(notif), 200
    return jsonify({"error": "Notificación no encontrada"}), 404

@app.route("/notificaciones/cita/<int:cita_id>", methods=["GET"])
def notificaciones_por_cita(cita_id):
    """
    Retorna notificaciones de una cita específica
    ---
    parameters:
      - name: cita_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Notificaciones de la cita
    """
    resultado = [n for n in notificaciones if n["cita_id"] == cita_id]
    return jsonify({"cita_id": cita_id, "notificaciones": resultado}), 200

@app.route("/notificaciones/paciente/<string:paciente>", methods=["GET"])
def notificaciones_por_paciente(paciente):
    """
    Retorna notificaciones de un paciente específico
    ---
    parameters:
      - name: paciente
        in: path
        type: string
        required: true
    responses:
      200:
        description: Notificaciones del paciente
    """
    resultado = [n for n in notificaciones if n["paciente"].lower() == paciente.lower()]
    return jsonify({"paciente": paciente, "notificaciones": resultado}), 200

@app.route("/notificaciones", methods=["POST"])
def crear_notificacion():
    """
    Crea una nueva notificación
    ---
    parameters:
      - in: body
        name: body
        schema:
          properties:
            cita_id:
              type: integer
            paciente:
              type: string
            tipo:
              type: string
            mensaje:
              type: string
            enviado:
              type: boolean
            fecha_envio:
              type: string
    responses:
      201:
        description: Notificación creada
    """
    data = request.get_json()
    nueva_notif = {
        "id": max([n["id"] for n in notificaciones]) + 1 if notificaciones else 1,
        "cita_id": data.get("cita_id"),
        "paciente": data.get("paciente"),
        "tipo": data.get("tipo", "general"),
        "mensaje": data.get("mensaje"),
        "enviado": data.get("enviado", False),
        "fecha_envio": data.get("fecha_envio")
    }
    notificaciones.append(nueva_notif)
    return jsonify(nueva_notif), 201


# ---------------------------------------------------------------------------
# Consumidor as\u00edncrono de RabbitMQ
# ---------------------------------------------------------------------------

def _procesar_evento(body: bytes) -> None:
    """Convierte el mensaje recibido en una notificaci\u00f3n y la persiste."""
    try:
        evento = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logging.error("Mensaje no es JSON v\u00e1lido: %s", body)
        return

    nueva_notif = {
        "id": max([n["id"] for n in notificaciones]) + 1 if notificaciones else 1,
        "cita_id": evento.get("cita_id"),
        "paciente": evento.get("paciente"),
        "tipo": evento.get("tipo", "general"),
        "mensaje": evento.get("mensaje"),
        "enviado": evento.get("enviado", True),
        "fecha_envio": evento.get("fecha_envio"),
    }
    notificaciones.append(nueva_notif)
    logging.info("Notificaci\u00f3n creada desde RabbitMQ: %s", nueva_notif)


def _callback(ch, method, properties, body):
    _procesar_evento(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def rabbitmq_consumer():
    """Hilo en background que consume la cola de eventos de citas."""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel = connection.channel()
            channel.queue_declare(queue=NOTIFICACIONES_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=NOTIFICACIONES_QUEUE,
                on_message_callback=_callback,
            )
            logging.info(
                "Esperando mensajes en cola '%s' (host=%s)...",
                NOTIFICACIONES_QUEUE,
                RABBITMQ_HOST,
            )
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as exc:
            logging.warning(
                "No se pudo conectar a RabbitMQ: %s. Reintentando en 5s...", exc
            )
            time.sleep(5)


# Arrancar el consumer al importarse el m\u00f3dulo (incluso bajo gunicorn / flask run)
_consumer_thread = threading.Thread(target=rabbitmq_consumer, daemon=True)
_consumer_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)

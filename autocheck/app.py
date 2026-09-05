"""
AutoCheck - Sistema completo (Citas + Inventario de Repuestos)
Version con paginas separadas:
  - "/"          -> pantalla del CLIENTE (agendar cita, incluye modelo del vehiculo)
  - "/repuestos" -> pantalla del DUEÑO del local (inventario, incluye marca del vehiculo)
"""

from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)

ARCHIVO_CITAS = "citas.json"
ARCHIVO_REPUESTOS = "repuestos.json"

SERVICIOS = [
    {"id": "aceite",  "nombre": "Cambio de aceite",     "precio": 25, "duracion": 30},
    {"id": "frenos",  "nombre": "Revision de frenos",   "precio": 35, "duracion": 45},
    {"id": "llantas", "nombre": "Rotacion de llantas",  "precio": 15, "duracion": 25},
    {"id": "motor",   "nombre": "Diagnostico de motor", "precio": 40, "duracion": 60},
    {"id": "luces",   "nombre": "Revision de luces",    "precio": 10, "duracion": 15},
    {"id": "bateria", "nombre": "Chequeo de bateria",   "precio": 12, "duracion": 20},
]

MARCAS_VEHICULO = [
    "Chevrolet", "Toyota", "Kia", "Hyundai", "Nissan",
    "Mazda", "Ford", "Volkswagen", "Renault", "Otra",
]

PALABRAS_URGENTES = ["freno", "frenos", "motor", "humo", "direccion"]
PALABRAS_BAJAS = ["luz", "luces", "limpiaparabrisas", "radio", "espejo"]

HORA_APERTURA = "08:00"
HORA_CIERRE = "17:00"


# ==========================================================
# PERSISTENCIA (compartida)
# ==========================================================
def cargar_datos(archivo):
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_datos(archivo, datos):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# ==========================================================
# LOGICA - CITAS
# ==========================================================
def calcular_costo(servicios_seleccionados):
    return sum(s["precio"] for s in servicios_seleccionados)


def calcular_duracion(servicios_seleccionados):
    return sum(s["duracion"] for s in servicios_seleccionados)


def clasificar_prioridad(texto_problema):
    texto = texto_problema.lower()
    if any(p in texto for p in PALABRAS_URGENTES):
        return "urgente"
    if any(p in texto for p in PALABRAS_BAJAS):
        return "baja"
    return "media"


def buscar_servicios_por_id(ids_seleccionados):
    return [s for s in SERVICIOS if s["id"] in ids_seleccionados]


def validar_disponibilidad(fecha, hora, citas):
    return not any(c["fecha"] == fecha and c["hora"] == hora for c in citas)


def validar_horario_taller(hora):
    return HORA_APERTURA <= hora <= HORA_CIERRE


def validar_fecha_no_pasada(fecha):
    hoy = datetime.now().strftime("%Y-%m-%d")
    return fecha >= hoy


def siguiente_id(lista):
    if not lista:
        return 1
    return max(item["id"] for item in lista) + 1


# ==========================================================
# LOGICA - INVENTARIO DE REPUESTOS
# ==========================================================
def calcular_valor_repuesto(repuesto):
    return repuesto["cantidad"] * repuesto["precio"]


def calcular_valor_total_inventario(repuestos):
    return sum(calcular_valor_repuesto(r) for r in repuestos)


def esta_bajo_stock(repuesto):
    return repuesto["cantidad"] <= repuesto["stock_minimo"]


def contar_repuestos_bajo_stock(repuestos):
    return sum(1 for r in repuestos if esta_bajo_stock(r))


def validar_repuesto(nombre, marca, cantidad_txt, minimo_txt, precio_txt, repuestos):
    if not nombre.strip():
        return False, "El nombre del repuesto no puede estar vacio."
    if not marca.strip():
        return False, "Selecciona la marca del vehiculo."
    try:
        cantidad = float(cantidad_txt)
        minimo = float(minimo_txt)
        precio = float(precio_txt)
        if cantidad < 0 or minimo < 0 or precio < 0:
            raise ValueError
    except ValueError:
        return False, "Cantidad, stock minimo y precio deben ser numeros validos (0 o mayores)."
    if any(r["nombre"].lower() == nombre.strip().lower() and r["marca"].lower() == marca.strip().lower()
           for r in repuestos):
        return False, "Ya existe ese repuesto registrado para esa marca."
    return True, ""


# ==========================================================
# PAGINA DE INICIO - presenta el taller
# ==========================================================
@app.route("/")
def home():
    return render_template("inicio.html")


# ==========================================================
# PAGINA DEL CLIENTE - agendar cita
# ==========================================================
@app.route("/citas")
def citas_page():
    citas = cargar_datos(ARCHIVO_CITAS)
    contexto = {
        "servicios": SERVICIOS,
        "citas": sorted(citas, key=lambda c: (c["fecha"], c["hora"])),
        "total_citas": len(citas),
        "total_urgentes": sum(1 for c in citas if c["prioridad"] == "urgente"),
        "error_cita": request.args.get("error_cita", ""),
    }
    return render_template("cliente.html", **contexto)


@app.route("/agendar", methods=["POST"])
def agendar():
    citas = cargar_datos(ARCHIVO_CITAS)

    nombre = request.form.get("nombre", "").strip()
    placa = request.form.get("placa", "").strip()
    modelo = request.form.get("modelo", "").strip()
    fecha = request.form.get("fecha", "").strip()
    hora = request.form.get("hora", "").strip()
    problema = request.form.get("problema", "").strip()
    ids_servicios = request.form.getlist("servicios")
    servicios_seleccionados = buscar_servicios_por_id(ids_servicios)

    if not nombre or not placa or not modelo or not fecha or not hora:
        return redirect(url_for("citas_page", error_cita="Completa cliente, placa, modelo, fecha y hora."))
    if not servicios_seleccionados:
        return redirect(url_for("citas_page", error_cita="Selecciona al menos un servicio."))
    if not validar_fecha_no_pasada(fecha):
        return redirect(url_for("citas_page", error_cita="No puedes agendar una fecha que ya paso."))
    if not validar_horario_taller(hora):
        return redirect(url_for("citas_page", error_cita=f"El taller atiende de {HORA_APERTURA} a {HORA_CIERRE}."))
    if not validar_disponibilidad(fecha, hora, citas):
        return redirect(url_for("citas_page", error_cita="Ya existe una cita en esa fecha y hora."))

    cita = {
        "id": siguiente_id(citas),
        "nombre": nombre,
        "placa": placa,
        "modelo": modelo,
        "fecha": fecha,
        "hora": hora,
        "problema": problema,
        "servicios": [s["nombre"] for s in servicios_seleccionados],
        "costo": calcular_costo(servicios_seleccionados),
        "duracion": calcular_duracion(servicios_seleccionados),
        "prioridad": clasificar_prioridad(problema),
    }
    citas.append(cita)
    guardar_datos(ARCHIVO_CITAS, citas)
    return redirect(url_for("citas_page", exito_cita="1"))


@app.route("/citas/eliminar/<int:cita_id>", methods=["POST"])
def eliminar_cita(cita_id):
    citas = cargar_datos(ARCHIVO_CITAS)
    citas = [c for c in citas if c["id"] != cita_id]
    guardar_datos(ARCHIVO_CITAS, citas)
    return redirect(url_for("citas_page"))


# ==========================================================
# PAGINA DEL DUEÑO - inventario de repuestos
# ==========================================================
@app.route("/repuestos")
def pagina_repuestos():
    repuestos = cargar_datos(ARCHIVO_REPUESTOS)
    contexto = {
        "marcas": MARCAS_VEHICULO,
        "repuestos": sorted(repuestos, key=lambda r: r["nombre"].lower()),
        "valor_total_inv": calcular_valor_total_inventario(repuestos),
        "bajo_stock": contar_repuestos_bajo_stock(repuestos),
        "total_repuestos": len(repuestos),
        "esta_bajo_stock": esta_bajo_stock,
        "calcular_valor_repuesto": calcular_valor_repuesto,
        "error_repuesto": request.args.get("error_repuesto", ""),
    }
    return render_template("repuestos.html", **contexto)


@app.route("/repuestos/agregar", methods=["POST"])
def agregar_repuesto():
    repuestos = cargar_datos(ARCHIVO_REPUESTOS)
    nombre = request.form.get("nombre_repuesto", "")
    marca = request.form.get("marca", "")
    cantidad_txt = request.form.get("cantidad", "")
    minimo_txt = request.form.get("stock_minimo", "")
    precio_txt = request.form.get("precio", "")

    es_valido, mensaje_error = validar_repuesto(nombre, marca, cantidad_txt, minimo_txt, precio_txt, repuestos)
    if not es_valido:
        return redirect(url_for("pagina_repuestos", error_repuesto=mensaje_error))

    nuevo_repuesto = {
        "id": siguiente_id(repuestos),
        "nombre": nombre.strip(),
        "marca": marca.strip(),
        "cantidad": float(cantidad_txt),
        "stock_minimo": float(minimo_txt),
        "precio": float(precio_txt),
    }
    repuestos.append(nuevo_repuesto)
    guardar_datos(ARCHIVO_REPUESTOS, repuestos)
    return redirect(url_for("pagina_repuestos", exito_repuesto="1"))


@app.route("/repuestos/ajustar/<int:repuesto_id>/<string:direccion>", methods=["POST"])
def ajustar_repuesto(repuesto_id, direccion):
    repuestos = cargar_datos(ARCHIVO_REPUESTOS)
    for r in repuestos:
        if r["id"] == repuesto_id:
            delta = 1 if direccion == "sumar" else -1
            nueva_cantidad = r["cantidad"] + delta
            if nueva_cantidad >= 0:
                r["cantidad"] = nueva_cantidad
            break
    guardar_datos(ARCHIVO_REPUESTOS, repuestos)
    return redirect(url_for("pagina_repuestos"))


@app.route("/repuestos/eliminar/<int:repuesto_id>", methods=["POST"])
def eliminar_repuesto(repuesto_id):
    repuestos = cargar_datos(ARCHIVO_REPUESTOS)
    repuestos = [r for r in repuestos if r["id"] != repuesto_id]
    guardar_datos(ARCHIVO_REPUESTOS, repuestos)
    return redirect(url_for("pagina_repuestos"))


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, jsonify
from xml.dom import minidom
import re, os

app = Flask(__name__)

# rutas de archivos XML "base de datos"
DB_DIR = os.path.join(os.path.dirname(__file__), "dbxml")
os.makedirs(DB_DIR, exist_ok=True)
RUTA_DB_DATOS = os.path.join(DB_DIR, "datos.xml")
RUTA_DB_FACTURAS = os.path.join(DB_DIR, "facturas.xml")

# fecha dd/mm/yyyy con regex
REG_FECHA = re.compile(r'(\b\d{2}/\d{2}/\d{4}\b)')

def guardar_archivo(path, contenido):
    with open(path, "w", encoding="utf-8") as f:
        f.write(contenido)

@app.get("/api/consultar")
def consultar(): 
    existe_datos = os.path.exists(RUTA_DB_DATOS)
    return jsonify({"estado":"ok", "hay_datos": existe_datos})

@app.post("/api/init")
def inicializar():
    # borra archivos de db
    for p in [RUTA_DB_DATOS, RUTA_DB_FACTURAS]:
        if os.path.exists(p):
            os.remove(p)
    # crea basicos vacios
    guardar_archivo(RUTA_DB_DATOS, "<db></db>")
    guardar_archivo(RUTA_DB_FACTURAS, "<facturas></facturas>")
    return jsonify({"mensaje":"base reiniciada"})

@app.post("/api/config")
def cargar_config():
    # recibe XML 
    xml_text = request.data.decode("utf-8") if request.data else request.form.get("xml","")
    try:
        doc = minidom.parseString(xml_text)
        guardar_archivo(RUTA_DB_DATOS, xml_text)
        return jsonify({"ok": True, "resumen":"config cargada"}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/api/consumo")
def cargar_consumo():
    xml_text = request.data.decode("utf-8") if request.data else request.form.get("xml","")
    try:
        doc = minidom.parseString(xml_text)
        # aqui procesar consumos y acumular en DB
        return jsonify({"ok": True, "resumen":"consumo procesado"}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/api/crear")
def crear():
    payload = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "eco": payload}), 201

@app.post("/api/cancelar_instancia")
def cancelar():
    payload = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "eco": payload})

@app.post("/api/facturar")
def facturar():
    payload = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "generadas": 1, "rango": payload})

@app.get("/api/factura/<fid>")
def factura(fid):
    return jsonify({"ok": True, "factura": fid, "detalle":"pendiente"})

@app.get("/api/analisis")
def analisis():
    tipo = request.args.get("tipo","categorias")
    return jsonify({"ok": True, "tipo": tipo, "top": []})

if __name__ == "__main__":
    app.run(debug=True)

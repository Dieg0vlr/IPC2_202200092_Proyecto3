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
    xml_text = request.data.decode("utf-8") if request.data else request.form.get("xml", "")
    if not xml_text:
        return jsonify({"ok": False, "error": "No se recibio XML"}), 400

    try:
        doc = minidom.parseString(xml_text)

        # Obtengo listas principales
        recursos = doc.getElementsByTagName("recurso")
        categorias = doc.getElementsByTagName("categoria")
        clientes = doc.getElementsByTagName("cliente")

        # Crear documento XML
        raiz = minidom.Document()
        db = raiz.createElement("baseDatos")
        raiz.appendChild(db)

        # -------------------- Recursos --------------------
        lista_recursos = raiz.createElement("recursos")
        for recurso in recursos:
            nodo = raiz.createElement("recurso")

            nodo.setAttribute("id", recurso.getAttribute("id"))
            for etiqueta in ["nombre", "abreviatura", "metrica", "tipo", "valorXhora"]:
                elementos = recurso.getElementsByTagName(etiqueta)
                if elementos and elementos[0].firstChild:
                    valor = elementos[0].firstChild.nodeValue.strip()
                    sub = raiz.createElement(etiqueta)
                    sub.appendChild(raiz.createTextNode(valor))
                    nodo.appendChild(sub)
            lista_recursos.appendChild(nodo)
        db.appendChild(lista_recursos)

        # -------------------- Categorias --------------------
        lista_categorias = raiz.createElement("categorias")
        for categoria in categorias:
            nodo = raiz.createElement("categoria")
            nodo.setAttribute("id", categoria.getAttribute("id"))

            for etiqueta in ["nombre", "descripcion", "cargaTrabajo"]:
                elementos = categoria.getElementsByTagName(etiqueta)
                if elementos and elementos[0].firstChild:
                    valor = elementos[0].firstChild.nodeValue.strip()
                    sub = raiz.createElement(etiqueta)
                    sub.appendChild(raiz.createTextNode(valor))
                    nodo.appendChild(sub)

            # Configuraciones dentro de categoria
            lista_conf = categoria.getElementsByTagName("configuracion")
            configs_element = raiz.createElement("configuraciones")
            for conf in lista_conf:
                nodo_conf = raiz.createElement("configuracion")
                nodo_conf.setAttribute("id", conf.getAttribute("id"))

                for etiqueta in ["nombre", "descripcion"]:
                    elem = conf.getElementsByTagName(etiqueta)
                    if elem and elem[0].firstChild:
                        valor = elem[0].firstChild.nodeValue.strip()
                        sub = raiz.createElement(etiqueta)
                        sub.appendChild(raiz.createTextNode(valor))
                        nodo_conf.appendChild(sub)

                # Recursos dentro de la configuracion
                recursos_conf = conf.getElementsByTagName("recurso")
                recursos_element = raiz.createElement("recursos")
                for r in recursos_conf:
                    recurso_item = raiz.createElement("recurso")
                    recurso_item.setAttribute("id", r.getAttribute("id"))
                    if r.firstChild:
                        cantidad = r.firstChild.nodeValue.strip()
                        recurso_item.appendChild(raiz.createTextNode(cantidad))
                    recursos_element.appendChild(recurso_item)
                nodo_conf.appendChild(recursos_element)
                configs_element.appendChild(nodo_conf)

            nodo.appendChild(configs_element)
            lista_categorias.appendChild(nodo)
        db.appendChild(lista_categorias)

        # -------------------- Clientes --------------------
        lista_clientes = raiz.createElement("clientes")
        for cliente in clientes:
            nodo = raiz.createElement("cliente")
            nodo.setAttribute("nit", cliente.getAttribute("nit"))

            for etiqueta in ["nombre", "usuario", "clave", "direccion", "correoElectronico"]:
                elementos = cliente.getElementsByTagName(etiqueta)
                if elementos and elementos[0].firstChild:
                    valor = elementos[0].firstChild.nodeValue.strip()
                    sub = raiz.createElement(etiqueta)
                    sub.appendChild(raiz.createTextNode(valor))
                    nodo.appendChild(sub)

            # Instancias del cliente
            instancias = cliente.getElementsByTagName("instancia")
            lista_instancias = raiz.createElement("instancias")
            for inst in instancias:
                nodo_i = raiz.createElement("instancia")
                nodo_i.setAttribute("id", inst.getAttribute("id"))

                for etiqueta in ["idConfiguracion", "nombre", "fechaInicio", "estado", "fechaFinal"]:
                    elementos = inst.getElementsByTagName(etiqueta)
                    if elementos and elementos[0].firstChild:
                        valor = elementos[0].firstChild.nodeValue.strip()
                        sub = raiz.createElement(etiqueta)
                        sub.appendChild(raiz.createTextNode(valor))
                        nodo_i.appendChild(sub)

                lista_instancias.appendChild(nodo_i)
            nodo.appendChild(lista_instancias)
            lista_clientes.appendChild(nodo)
        db.appendChild(lista_clientes)

        # Guardar el archivo XML estructurado
        xml_final = raiz.toprettyxml(indent="  ", encoding="utf-8")
        guardar_archivo(RUTA_DB_DATOS, xml_final.decode("utf-8"))

        return jsonify({"ok": True, "mensaje": "Configuracion procesada correctamente"}), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/api/consumo")
def cargar_consumo():
    xml_text = request.data.decode("utf-8") if request.data else request.form.get("xml", "")
    if not xml_text:
        return jsonify({"ok": False, "error": "No se recibio XML"}), 400

    try:
        doc = minidom.parseString(xml_text)
        consumos = doc.getElementsByTagName("consumo")

        if not consumos:
            return jsonify({"ok": False, "error": "No se encontro ningun nodo <consumo>"}), 400

        # Abrir o crear el archivo de base de datos
        if os.path.exists(RUTA_DB_DATOS):
            base_doc = minidom.parse(RUTA_DB_DATOS)
            raiz = base_doc.documentElement
        else:
            base_doc = minidom.Document()
            raiz = base_doc.createElement("baseDatos")
            base_doc.appendChild(raiz)

        # Crear o ubicar la seccion de consumos
        lista_consumos = None
        existentes = raiz.getElementsByTagName("consumos")
        if existentes:
            lista_consumos = existentes[0]
        else:
            lista_consumos = base_doc.createElement("consumos")
            raiz.appendChild(lista_consumos)

        
        for c in consumos:
            nodo_consumo = base_doc.createElement("consumo")
            nodo_consumo.setAttribute("nitCliente", c.getAttribute("nitCliente"))
            nodo_consumo.setAttribute("idInstancia", c.getAttribute("idInstancia"))

            tiempo_nodos = c.getElementsByTagName("tiempo")
            fecha_nodos = c.getElementsByTagName("fechaHora")

            if tiempo_nodos and tiempo_nodos[0].firstChild:
                tiempo = tiempo_nodos[0].firstChild.nodeValue.strip()
                t_elem = base_doc.createElement("tiempo")
                t_elem.appendChild(base_doc.createTextNode(tiempo))
                nodo_consumo.appendChild(t_elem)

            if fecha_nodos and fecha_nodos[0].firstChild:
                fecha = fecha_nodos[0].firstChild.nodeValue.strip()
                f_elem = base_doc.createElement("fechaHora")
                f_elem.appendChild(base_doc.createTextNode(fecha))
                nodo_consumo.appendChild(f_elem)

            lista_consumos.appendChild(nodo_consumo)

        # Guardar los cambios en el XML
        xml_final = base_doc.toprettyxml(indent="  ", encoding="utf-8")
        guardar_archivo(RUTA_DB_DATOS, xml_final.decode("utf-8"))

        return jsonify({"ok": True, "mensaje": f"{len(consumos)} consumos procesados correctamente"}), 201

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

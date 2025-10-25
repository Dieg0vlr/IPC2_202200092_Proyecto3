from modelos import Recurso, Categoria, Configuracion, Cliente, Instancia
from flask import Flask, request, jsonify
from xml.dom import minidom
import re, os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from modelos import Consumo
from reportlab.lib.units import cm
from flask import send_file
from flask_cors import CORS

REG_FECHA = re.compile(r'\b\d{2}/\d{2}/\d{4}\b')
REG_NIT = re.compile(r'^\d+-[\dkK]$')

def limpiar_fecha(texto):
    if not texto:
        return ""
    m = REG_FECHA.search(texto)
    return m.group(0) if m else ""

def validar_nit(nit):
    """Verifica formato basico de NIT"""
    return bool(REG_NIT.match(nit.strip()))

app = Flask(__name__)
CORS(app)


# rutas de archivos XML base de datos
DB_DIR = os.path.join(os.path.dirname(__file__), "dbxml")
os.makedirs(DB_DIR, exist_ok=True)
RUTA_DB_DATOS = os.path.join(DB_DIR, "datos.xml")
RUTA_DB_FACTURAS = os.path.join(DB_DIR, "facturas.xml")

def _parse_fecha(fecha_txt):
    try:
        return datetime.strptime(fecha_txt.strip(), "%d/%m/%Y")
    except Exception:
        return None

def guardar_archivo(path, contenido):
    if isinstance(contenido, bytes):
        contenido = contenido.decode("utf-8")
    # Quita las lineas en blanco que genera toprettyxml
    lineas_limpias = [line for line in contenido.splitlines() if line.strip()]
    contenido_limpio = "\n".join(lineas_limpias)

    with open(path, "w", encoding="utf-8") as f:
        f.write(contenido_limpio)


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

    guardar_archivo(RUTA_DB_DATOS, "<baseDatos></baseDatos>")
    guardar_archivo(RUTA_DB_FACTURAS, "<facturas></facturas>")
    return jsonify({"mensaje":"base reiniciada"})

@app.post("/api/config")
def cargar_config():
    xml_text = request.data.decode("utf-8") if request.data else request.form.get("xml", "")
    if not xml_text:
        return jsonify({"ok": False, "error": "No se recibió XML"}), 400

    try:
        nuevo_doc = minidom.parseString(xml_text)

        # Abrir o crear base
        if os.path.exists(RUTA_DB_DATOS):
            base_doc = minidom.parse(RUTA_DB_DATOS)
            raiz = base_doc.documentElement
        else:
            base_doc = minidom.Document()
            raiz = base_doc.createElement("baseDatos")
            base_doc.appendChild(raiz)

        # --- FUNCION AUXILIAR ---
        def obtener_o_crear_lista(nombre):
            lista = raiz.getElementsByTagName(nombre)
            if lista:
                return lista[0]
            nuevo = base_doc.createElement(nombre)
            raiz.appendChild(nuevo)
            return nuevo

        # --- RECURSOS ---
        recursos_base = obtener_o_crear_lista("recursos")

        recursos_padre = nuevo_doc.getElementsByTagName("listaRecursos")
        nuevos_recursos = []
        if recursos_padre:
            nuevos_recursos = recursos_padre[0].getElementsByTagName("recurso")

        for r in nuevos_recursos:
            idr = r.getAttribute("id")
            if not any(x.getAttribute("id") == idr for x in recursos_base.getElementsByTagName("recurso")):
                obj = Recurso(
                    idr,
                    r.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip(),
                    r.getElementsByTagName("abreviatura")[0].firstChild.nodeValue.strip(),
                    r.getElementsByTagName("metrica")[0].firstChild.nodeValue.strip(),
                    r.getElementsByTagName("tipo")[0].firstChild.nodeValue.strip(),
                    r.getElementsByTagName("valorXhora")[0].firstChild.nodeValue.strip(),
                )
                recursos_base.appendChild(obj.a_xml(base_doc))


        # --- CATEGORIAS ---
        categorias_base = obtener_o_crear_lista("categorias")
        nuevas_categorias = nuevo_doc.getElementsByTagName("categoria")
        for cat in nuevas_categorias:
            idc = cat.getAttribute("id")
            if not any(x.getAttribute("id") == idc for x in categorias_base.getElementsByTagName("categoria")):
                categoria_obj = Categoria(
                    id=idc,
                    nombre=cat.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip(),
                    descripcion=cat.getElementsByTagName("descripcion")[0].firstChild.nodeValue.strip(),
                    carga_trabajo=cat.getElementsByTagName("cargaTrabajo")[0].firstChild.nodeValue.strip()
                )

                lista_conf = cat.getElementsByTagName("configuracion")
                for conf in lista_conf:
                    idconf = conf.getAttribute("id")
                    nombre_conf = conf.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip()
                    descripcion_conf = conf.getElementsByTagName("descripcion")[0].firstChild.nodeValue.strip()

                    recursos_conf = {}
                    for rc in conf.getElementsByTagName("recurso"):
                        recursos_conf[rc.getAttribute("id")] = float(rc.firstChild.nodeValue.strip())

                    categoria_obj.agregar_configuracion(Configuracion(idconf, nombre_conf, descripcion_conf, recursos_conf))

                categorias_base.appendChild(categoria_obj.a_xml(base_doc))

        # --- CLIENTES ---
        clientes_base = obtener_o_crear_lista("clientes")
        nuevos_clientes = nuevo_doc.getElementsByTagName("cliente")
        for c in nuevos_clientes:
            nit = c.getAttribute("nit").strip()
            if not validar_nit(nit):
                continue

            ya_existe = [x for x in clientes_base.getElementsByTagName("cliente") if x.getAttribute("nit") == nit]
            if not ya_existe:
                cliente_obj = Cliente(
                    nit=nit,
                    nombre=c.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip(),
                    usuario=c.getElementsByTagName("usuario")[0].firstChild.nodeValue.strip(),
                    clave=c.getElementsByTagName("clave")[0].firstChild.nodeValue.strip(),
                    direccion=c.getElementsByTagName("direccion")[0].firstChild.nodeValue.strip(),
                    correo=c.getElementsByTagName("correoElectronico")[0].firstChild.nodeValue.strip()
                )

                instancias = c.getElementsByTagName("instancia")
                for inst in instancias:
                    inst_obj = Instancia(
                    id=inst.getAttribute("id"),
                    id_configuracion=inst.getElementsByTagName("idConfiguracion")[0].firstChild.nodeValue.strip(),
                    nombre=inst.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip(),
                    fecha_inicio=limpiar_fecha(inst.getElementsByTagName("fechaInicio")[0].firstChild.nodeValue.strip()),
                    estado=inst.getElementsByTagName("estado")[0].firstChild.nodeValue.strip(),
                    fecha_final=limpiar_fecha(inst.getElementsByTagName("fechaFinal")[0].firstChild.nodeValue.strip())
                    if inst.getElementsByTagName("fechaFinal") and inst.getElementsByTagName("fechaFinal")[0].firstChild
                    else ""
                )

                    cliente_obj.agregar_instancia(inst_obj)

                clientes_base.appendChild(cliente_obj.a_xml(base_doc))

        # Guardar XML final
        xml_final = base_doc.toprettyxml(indent="  ", encoding="utf-8")
        guardar_archivo(RUTA_DB_DATOS, xml_final.decode("utf-8"))

        return jsonify({"ok": True, "mensaje": "Configuración agregada usando POO"}), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    

@app.post("/api/consumo")
def cargar_consumo():
    xml_text = request.data.decode("utf-8") if request.data else request.form.get("xml", "")
    if not xml_text:
        return jsonify({"ok": False, "error": "No se recibió XML"}), 400

    try:
        doc_nuevo = minidom.parseString(xml_text)
        consumos_nuevos = doc_nuevo.getElementsByTagName("consumo")

        # Abrir o crear base
        if os.path.exists(RUTA_DB_DATOS):
            base_doc = minidom.parse(RUTA_DB_DATOS)
            raiz = base_doc.documentElement
        else:
            base_doc = minidom.Document()
            raiz = base_doc.createElement("baseDatos")
            base_doc.appendChild(raiz)

        lista_consumos = raiz.getElementsByTagName("consumos")
        if lista_consumos:
            lista_consumos = lista_consumos[0]
        else:
            lista_consumos = base_doc.createElement("consumos")
            raiz.appendChild(lista_consumos)

        existentes = set()
        for ex in lista_consumos.getElementsByTagName("consumo"):
            nit_ex = ex.getAttribute("nitCliente")
            inst_ex = ex.getAttribute("idInstancia")
            fecha_ex = ex.getElementsByTagName("fechaHora")[0].firstChild.nodeValue.strip() if ex.getElementsByTagName("fechaHora") and ex.getElementsByTagName("fechaHora")[0].firstChild else ""
            existentes.add((nit_ex, inst_ex, fecha_ex))

        agregados = 0
        for c in consumos_nuevos:
            nit = c.getAttribute("nitCliente").strip()
            id_inst = c.getAttribute("idInstancia").strip()
            tiempo = c.getElementsByTagName("tiempo")[0].firstChild.nodeValue.strip()
            fecha = limpiar_fecha(c.getElementsByTagName("fechaHora")[0].firstChild.nodeValue.strip())

            # Evita duplicado por nit, instancia, fecha
            key = (nit, id_inst, fecha)
            if key in existentes:
                continue

            consumo_obj = Consumo(nit, id_inst, tiempo, fecha)
            lista_consumos.appendChild(consumo_obj.a_xml(base_doc))
            existentes.add(key)
            agregados += 1

        # Guardar XML actualizado
        xml_final = base_doc.toprettyxml(indent="  ", encoding="utf-8")
        guardar_archivo(RUTA_DB_DATOS, xml_final.decode("utf-8"))

        return jsonify({"ok": True, "mensaje": f"{agregados} consumos agregados correctamente"}), 201

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
    try:
        if not os.path.exists(RUTA_DB_DATOS):
            return jsonify({"ok": False, "error": "No hay datos registrados"}), 400

        base_doc = minidom.parse(RUTA_DB_DATOS)
        raiz = base_doc.documentElement

        recursos = raiz.getElementsByTagName("recurso")
        consumos = raiz.getElementsByTagName("consumo")

        consumos_pendientes = [c for c in consumos if not c.hasAttribute("facturado")]

        if not consumos_pendientes:
            return jsonify({"ok": False, "error": "No hay consumos pendientes de facturar"}), 400

        # Crear mapa de costos por recurso
        costos_recursos = {}
        for r in recursos:
            idr = r.getAttribute("id")
            val = r.getElementsByTagName("valorXhora")
            if val and val[0].firstChild:
                costos_recursos[idr] = float(val[0].firstChild.nodeValue.strip())

        # Crear o abrir facturas.xml
        if os.path.exists(RUTA_DB_FACTURAS):
            fact_doc = minidom.parse(RUTA_DB_FACTURAS)
            root_facturas = fact_doc.documentElement
        else:
            fact_doc = minidom.Document()
            root_facturas = fact_doc.createElement("facturas")
            fact_doc.appendChild(root_facturas)

        total_global = 0
        facturas_creadas = 0

        # Agrupar consumos por cliente
        consumos_por_cliente = {}
        for c in consumos_pendientes:
            nit = c.getAttribute("nitCliente")
            if nit not in consumos_por_cliente:
                consumos_por_cliente[nit] = []
            consumos_por_cliente[nit].append(c)

        for nit, lista in consumos_por_cliente.items():
            total_cliente = 0
            id_factura = len(root_facturas.getElementsByTagName("factura")) + 1
            factura = fact_doc.createElement("factura")
            factura.setAttribute("id", str(id_factura))
            factura.setAttribute("nitCliente", nit)
            factura.setAttribute("fecha", datetime.now().strftime("%d/%m/%Y"))

            detalle = fact_doc.createElement("detalle")

            for c in lista:
                idInst = c.getAttribute("idInstancia")
                tiempo = float(c.getElementsByTagName("tiempo")[0].firstChild.nodeValue.strip())

                precio_hora = 0.0
                instancias = raiz.getElementsByTagName("instancia")
                for i in instancias:
                    if i.getAttribute("id") == idInst:
                        idConf = i.getElementsByTagName("idConfiguracion")[0].firstChild.nodeValue.strip()
                        configs = raiz.getElementsByTagName("configuracion")
                        for conf in configs:
                            if conf.getAttribute("id") == idConf:
                                subtotal_conf = 0
                                for r in conf.getElementsByTagName("recurso"):
                                    idr = r.getAttribute("id")
                                    cantidad = float(r.firstChild.nodeValue.strip())
                                    if idr in costos_recursos:
                                        subtotal_conf += cantidad * costos_recursos[idr]
                                precio_hora = subtotal_conf
                                break
                        break

                monto = tiempo * precio_hora
                total_cliente += monto

                item = fact_doc.createElement("item")
                item.setAttribute("instancia", idInst)
                item.setAttribute("horas", str(tiempo))
                item.setAttribute("precioHora", f"{precio_hora:.2f}")
                item.setAttribute("subtotal", f"{monto:.2f}")
                detalle.appendChild(item)

                # Marcar consumo como facturado
                c.setAttribute("facturado", "true")

            factura.appendChild(detalle)

            total_elem = fact_doc.createElement("total")
            total_elem.appendChild(fact_doc.createTextNode(f"{total_cliente:.2f}"))
            factura.appendChild(total_elem)

            total_global += total_cliente
            facturas_creadas += 1
            root_facturas.appendChild(factura)

        # Guardar actualizaciones
        xml_final = base_doc.toprettyxml(indent="  ", encoding="utf-8")
        guardar_archivo(RUTA_DB_DATOS, xml_final.decode("utf-8"))

        xml_facturas = fact_doc.toprettyxml(indent="  ", encoding="utf-8")
        guardar_archivo(RUTA_DB_FACTURAS, xml_facturas.decode("utf-8"))

        return jsonify({
            "ok": True,
            "facturas_creadas": facturas_creadas,
            "total_global": f"{total_global:.2f}"
        }), 201

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/reporte/factura/<int:id_factura>")
def generar_reporte_factura(id_factura):
    try:
        # Verificar existencia de los XML
        if not os.path.exists(RUTA_DB_DATOS):
            return jsonify({"ok": False, "error": "No hay datos.xml"}), 400
        if not os.path.exists(RUTA_DB_FACTURAS):
            return jsonify({"ok": False, "error": "No hay facturas.xml"}), 400

        # --- Cargar datos.xml ---
        datos_doc = minidom.parse(RUTA_DB_DATOS)
        raiz_datos = datos_doc.documentElement

        # --- Mapa id_recurso -> info completa del bloque recursos
        mapa_recursos = {}

        # Busca solo los recursos dentro de <recursos> y no los que estan en configuraciones
        recursos_raiz = raiz_datos.getElementsByTagName("recursos")
        if recursos_raiz:
            for rr in recursos_raiz[0].getElementsByTagName("recurso"):
                idr = rr.getAttribute("id")
                if not idr:
                    continue 

                # Extrae los textos de los nodos internos
                def get_text(tag):
                    elems = rr.getElementsByTagName(tag)
                    return elems[0].firstChild.nodeValue.strip() if elems and elems[0].firstChild else ""

                nombre = get_text("nombre")
                metrica = get_text("metrica")
                valor_txt = get_text("valorXhora")

                try:
                    valor = float(valor_txt) if valor_txt != "" else 0.0
                except:
                    valor = 0.0

                # Guarda la informacion
                mapa_recursos[idr] = {
                    "nombre": nombre,
                    "metrica": metrica,
                    "valor": valor
                }


        # --- Mapa configuracion -> lista de recursos id, cantidad
        mapa_config = {}
        for cats in raiz_datos.getElementsByTagName("categorias"):
            for cat in cats.getElementsByTagName("categoria"):
                conts = cat.getElementsByTagName("configuraciones") or cat.getElementsByTagName("listaConfiguraciones")
                for cont in conts:
                    for conf in cont.getElementsByTagName("configuracion"):
                        id_conf = conf.getAttribute("id")
                        lista = []
                        recs = conf.getElementsByTagName("recursos") or conf.getElementsByTagName("recursosConfiguracion")
                        if recs:
                            for rc in recs[0].getElementsByTagName("recurso"):
                                lista.append((rc.getAttribute("id"), float(rc.firstChild.nodeValue.strip())))
                        mapa_config[id_conf] = lista

        # --- Mapa instancia → id_configuracion ---
        mapa_inst_conf = {}
        for cli in raiz_datos.getElementsByTagName("cliente"):
            for inst_cont in cli.getElementsByTagName("instancias") + cli.getElementsByTagName("listaInstancias"):
                for inst in inst_cont.getElementsByTagName("instancia"):
                    mapa_inst_conf[inst.getAttribute("id")] = inst.getElementsByTagName("idConfiguracion")[0].firstChild.nodeValue.strip()

        # --- Cargar factura desde facturas.xml ---
        fact_doc = minidom.parse(RUTA_DB_FACTURAS)
        fact_root = fact_doc.documentElement
        factura = next((f for f in fact_root.getElementsByTagName("factura")
                        if int(f.getAttribute("id")) == id_factura), None)
        if not factura:
            return jsonify({"ok": False, "error": "Factura no encontrada"}), 404

        nit_cliente = factura.getAttribute("nitCliente")
        fecha_fac = factura.getAttribute("fecha")
        total_fac = factura.getElementsByTagName("total")[0].firstChild.nodeValue.strip()

        # --- Crear PDF ---
        nombre_pdf = f"factura_{id_factura}.pdf"
        ruta_pdf = os.path.join(DB_DIR, nombre_pdf)
        c = canvas.Canvas(ruta_pdf, pagesize=letter)

        c.setFont("Helvetica-Bold", 14)
        c.drawString(2 * cm, 26.5 * cm, "Tecnologías Chapinas, S.A.")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, 25.7 * cm, f"Factura #{id_factura}")
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, 25.1 * cm, f"Fecha: {fecha_fac}")
        c.drawString(2 * cm, 24.6 * cm, f"NIT Cliente: {nit_cliente}")
        c.line(2 * cm, 24.3 * cm, 19 * cm, 24.3 * cm)

        # Detalle
        y = 23.8 * cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, y, "Detalle de consumos por instancia y recurso:")
        y -= 0.5 * cm
        c.setFont("Helvetica", 10)

        detalle = factura.getElementsByTagName("detalle")[0]
        for item in detalle.getElementsByTagName("item"):
            instancia = item.getAttribute("instancia")
            horas = float(item.getAttribute("horas"))
            precio_hora = float(item.getAttribute("precioHora"))
            subtotal = float(item.getAttribute("subtotal"))

            c.drawString(2 * cm, y, f"Instancia {instancia}  |  Horas: {horas:.2f}  |  PrecioHora: {precio_hora:.2f}  |  Subtotal: {subtotal:.2f}")
            y -= 0.45 * cm

            id_conf = mapa_inst_conf.get(instancia)
            recursos_conf = mapa_config.get(id_conf, [])

            for rid, cant in recursos_conf:
                rec = mapa_recursos.get(rid, {"valor": 0, "nombre": "", "metrica": ""})
                nombre_rec = rec["nombre"].strip() if rec["nombre"] else f"Recurso {rid}"
                metrica = rec["metrica"] if rec["metrica"] else ""
                valor = float(rec["valor"]) if rec["valor"] else 0.0

                aporte_total = cant * valor * horas
                c.drawString(
                    3.5 * cm, y,
                    f"- {nombre_rec} ({metrica}): {cant} × {valor:.2f} × {horas:.2f}h = {aporte_total:.2f}"
                )

                y -= 0.4 * cm
                
            y -= 0.2 * cm

        c.line(2 * cm, y - 0.2 * cm, 19 * cm, y - 0.2 * cm)
        y -= 0.8 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, f"TOTAL A PAGAR: Q {float(total_fac):.2f}")

        c.save()

        return jsonify({"ok": True, "mensaje": ruta_pdf}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/analisis")
def analisis():
    try:
        tipo = request.args.get("tipo", "categorias").strip().lower() 
        fecha_ini = request.args.get("fecha_ini")  
        fecha_fin = request.args.get("fecha_fin")  

        if not os.path.exists(RUTA_DB_DATOS):
            return jsonify({"ok": False, "error": "No existe datos.xml"}), 400
        if not os.path.exists(RUTA_DB_FACTURAS):
            return jsonify({"ok": False, "error": "No existe facturas.xml"}), 400

        # Cargar datos.xml para mapas
        datos_doc = minidom.parse(RUTA_DB_DATOS)
        raiz_datos = datos_doc.documentElement

        # mapa recurso -> {nombre, valor}
        mapa_recursos = {}
        recs_cont = raiz_datos.getElementsByTagName("recursos")
        if recs_cont:
            for rr in recs_cont[0].getElementsByTagName("recurso"):
                rid = rr.getAttribute("id")
                get = lambda tag: (rr.getElementsByTagName(tag)[0].firstChild.nodeValue.strip()
                                   if rr.getElementsByTagName(tag) and rr.getElementsByTagName(tag)[0].firstChild else "")
                mapa_recursos[rid] = {
                    "nombre": get("nombre") or rid,
                    "valor": float(get("valorXhora") or "0")
                }

        mapa_config_recursos = {}
        mapa_config_meta = {}

        categorias_cont = raiz_datos.getElementsByTagName("categorias")
        if categorias_cont:
            for cat in categorias_cont[0].getElementsByTagName("categoria"):
                cat_id = cat.getAttribute("id")
                cat_nombre = (cat.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip()
                              if cat.getElementsByTagName("nombre") and cat.getElementsByTagName("nombre")[0].firstChild else cat_id)

                conts = cat.getElementsByTagName("configuraciones")
                if not conts:
                    conts = cat.getElementsByTagName("listaConfiguraciones")
                for cont in conts:
                    for conf in cont.getElementsByTagName("configuracion"):
                        cid = conf.getAttribute("id")
                        cnombre = (conf.getElementsByTagName("nombre")[0].firstChild.nodeValue.strip()
                                   if conf.getElementsByTagName("nombre") and conf.getElementsByTagName("nombre")[0].firstChild else cid)

                        rc_cont = conf.getElementsByTagName("recursos")
                        if not rc_cont:
                            rc_cont = conf.getElementsByTagName("recursosConfiguracion")
                        lst = []
                        if rc_cont:
                            for r in rc_cont[0].getElementsByTagName("recurso"):
                                rid = r.getAttribute("id")
                                cant = float(r.firstChild.nodeValue.strip()) if r.firstChild else 0.0
                                lst.append((rid, cant))
                        mapa_config_recursos[cid] = lst
                        mapa_config_meta[cid] = (cnombre, cat_id, cat_nombre)

        mapa_inst_conf = {}
        clientes_cont = raiz_datos.getElementsByTagName("clientes")
        if clientes_cont:
            for cli in clientes_cont[0].getElementsByTagName("cliente"):
                conts = []
                conts.extend(cli.getElementsByTagName("instancias"))
                conts.extend(cli.getElementsByTagName("listaInstancias"))
                for cont in conts:
                    for inst in cont.getElementsByTagName("instancia"):
                        iid = inst.getAttribute("id")
                        id_conf = inst.getElementsByTagName("idConfiguracion")[0].firstChild.nodeValue.strip()
                        mapa_inst_conf[iid] = id_conf

        # Cargar facturas.xml
        fact_doc = minidom.parse(RUTA_DB_FACTURAS)
        root_fact = fact_doc.documentElement

        dt_ini = _parse_fecha(fecha_ini) if fecha_ini else None
        dt_fin = _parse_fecha(fecha_fin) if fecha_fin else None
        if dt_fin:
            dt_fin = dt_fin.replace(hour=23, minute=59, second=59)

        totales = {}  

        for fac in root_fact.getElementsByTagName("factura"):
            fecha_txt = fac.getAttribute("fecha") or ""
            dt_fac = _parse_fecha(fecha_txt)
            if dt_ini and (not dt_fac or dt_fac < dt_ini):
                continue
            if dt_fin and (not dt_fac or dt_fac > dt_fin):
                continue

            detalle = fac.getElementsByTagName("detalle")
            items = detalle[0].getElementsByTagName("item") if detalle else []

            for it in items:
                instancia = it.getAttribute("instancia")
                horas = float(it.getAttribute("horas") or "0")
                subtotal_item = float(it.getAttribute("subtotal") or "0")

                id_conf = mapa_inst_conf.get(instancia)
                meta = mapa_config_meta.get(id_conf, (id_conf or "?", "?", "SinCategoria"))
                conf_nombre, cat_id, cat_nombre = meta

                if tipo == "categorias":
                    key = cat_id or "?"
                    nombre = cat_nombre or key
                    data = totales.setdefault(key, {"nombre": nombre, "total": 0.0})
                    data["total"] += subtotal_item

                elif tipo == "configuraciones":
                    key = id_conf or "?"
                    nombre = conf_nombre or key
                    data = totales.setdefault(key, {"nombre": nombre, "total": 0.0})
                    data["total"] += subtotal_item

                elif tipo == "recursos":
                    recursos_conf = mapa_config_recursos.get(id_conf, [])
                    for rid, cant in recursos_conf:
                        precio = mapa_recursos.get(rid, {"valor": 0, "nombre": rid})["valor"]
                        aporte = cant * precio * horas
                        data = totales.setdefault(rid, {"nombre": mapa_recursos.get(rid, {"nombre": rid})["nombre"], "total": 0.0})
                        data["total"] += aporte

                else:
                    return jsonify({"ok": False, "error": "tipo inválido. Use: categorias | configuraciones | recursos"}), 400

        top = [
            {"id": k, "nombre": v["nombre"], "total": round(v["total"], 2)}
            for k, v in totales.items()
        ]
        top.sort(key=lambda x: x["total"], reverse=True)

        return jsonify({"ok": True, "tipo": tipo, "top": top}), 200

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/reporte/factura/<int:id_factura>/ver")
def ver_factura_pdf(id_factura):

    if not os.path.exists(RUTA_DB_DATOS):
        return jsonify({"ok": False, "error": "No hay datos.xml"}), 400
    if not os.path.exists(RUTA_DB_FACTURAS):
        return jsonify({"ok": False, "error": "No hay facturas.xml"}), 400

    # Ruta donde genero pdfs
    ruta_pdf = os.path.join(DB_DIR, f"factura_{id_factura}.pdf")

    if not os.path.exists(ruta_pdf):
        resp, status = generar_reporte_factura(id_factura)
        if status and status >= 400:
            return resp, status

    return send_file(ruta_pdf, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)

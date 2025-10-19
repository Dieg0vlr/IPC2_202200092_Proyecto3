from xml.dom.minidom import Document

class Recurso:
    def __init__(self, id, nombre, abreviatura, metrica, tipo, valor_x_hora):
        self.id = id
        self.nombre = nombre
        self.abreviatura = abreviatura
        self.metrica = metrica
        self.tipo = tipo
        self.valor_x_hora = float(valor_x_hora)

    def a_xml(self, doc: Document):
        nodo = doc.createElement("recurso")
        nodo.setAttribute("id", str(self.id))
        for etiqueta, valor in {
            "nombre": self.nombre,
            "abreviatura": self.abreviatura,
            "metrica": self.metrica,
            "tipo": self.tipo,
            "valorXhora": f"{self.valor_x_hora}"
        }.items():
            sub = doc.createElement(etiqueta)
            sub.appendChild(doc.createTextNode(str(valor)))
            nodo.appendChild(sub)
        return nodo

class Configuracion:
    def __init__(self, id, nombre, descripcion, recursos=None):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.recursos = recursos if recursos else {}  # {id_recurso: cantidad}

    def calcular_costo_por_hora(self, mapa_recursos):
        total = 0.0
        for idr, cantidad in self.recursos.items():
            if idr in mapa_recursos:
                total += float(cantidad) * float(mapa_recursos[idr].valor_x_hora)
        return total

    def a_xml(self, doc: Document):
        nodo = doc.createElement("configuracion")
        nodo.setAttribute("id", str(self.id))

        for etiqueta, valor in {"nombre": self.nombre, "descripcion": self.descripcion}.items():
            sub = doc.createElement(etiqueta)
            sub.appendChild(doc.createTextNode(str(valor)))
            nodo.appendChild(sub)

        lista = doc.createElement("recursos")
        for idr, cantidad in self.recursos.items():
            rec_elem = doc.createElement("recurso")
            rec_elem.setAttribute("id", str(idr))
            rec_elem.appendChild(doc.createTextNode(str(cantidad)))
            lista.appendChild(rec_elem)
        nodo.appendChild(lista)
        return nodo

class Categoria:
    def __init__(self, id, nombre, descripcion, carga_trabajo):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.carga_trabajo = carga_trabajo
        self.configuraciones = [] 

    def agregar_configuracion(self, conf: Configuracion):
        if not any(c.id == conf.id for c in self.configuraciones):
            self.configuraciones.append(conf)

    def a_xml(self, doc: Document):
        nodo = doc.createElement("categoria")
        nodo.setAttribute("id", str(self.id))

        for etiqueta, valor in {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "cargaTrabajo": self.carga_trabajo
        }.items():
            sub = doc.createElement(etiqueta)
            sub.appendChild(doc.createTextNode(str(valor)))
            nodo.appendChild(sub)

        lista_conf = doc.createElement("configuraciones")
        for conf in self.configuraciones:
            lista_conf.appendChild(conf.a_xml(doc))
        nodo.appendChild(lista_conf)

        return nodo

class Instancia:
    def __init__(self, id, id_configuracion, nombre, fecha_inicio, estado="Vigente", fecha_final=None):
        self.id = id
        self.id_configuracion = id_configuracion
        self.nombre = nombre
        self.fecha_inicio = fecha_inicio
        self.estado = estado
        self.fecha_final = fecha_final or ""

    def a_xml(self, doc: Document):
        nodo = doc.createElement("instancia")
        nodo.setAttribute("id", str(self.id))
        for etiqueta, valor in {
            "idConfiguracion": self.id_configuracion,
            "nombre": self.nombre,
            "fechaInicio": self.fecha_inicio,
            "estado": self.estado,
            "fechaFinal": self.fecha_final
        }.items():
            sub = doc.createElement(etiqueta)
            sub.appendChild(doc.createTextNode(str(valor)))
            nodo.appendChild(sub)
        return nodo

class Cliente:
    def __init__(self, nit, nombre, usuario, clave, direccion, correo):
        self.nit = nit
        self.nombre = nombre
        self.usuario = usuario
        self.clave = clave
        self.direccion = direccion
        self.correo = correo
        self.instancias = []

    def agregar_instancia(self, inst: Instancia):
        if not any(i.id == inst.id for i in self.instancias):
            self.instancias.append(inst)

    def a_xml(self, doc: Document):
        nodo = doc.createElement("cliente")
        nodo.setAttribute("nit", self.nit)
        for etiqueta, valor in {
            "nombre": self.nombre,
            "usuario": self.usuario,
            "clave": self.clave,
            "direccion": self.direccion,
            "correoElectronico": self.correo
        }.items():
            sub = doc.createElement(etiqueta)
            sub.appendChild(doc.createTextNode(str(valor)))
            nodo.appendChild(sub)

        # contenedor canonico
        lista_instancias = doc.createElement("instancias")
        for inst in self.instancias:
            lista_instancias.appendChild(inst.a_xml(doc))
        nodo.appendChild(lista_instancias)
        return nodo

class Factura:
    
    def __init__(self, id, nit_cliente, fecha, items=None):
        self.id = id
        self.nit_cliente = nit_cliente
        self.fecha = fecha
        self.items = items if items else []  # [{instancia, horas, precioHora, subtotal}]

    def total(self):
        return sum(float(i.get("subtotal", 0)) for i in self.items)

    def a_xml(self, doc: Document):
        nodo = doc.createElement("factura")
        nodo.setAttribute("id", str(self.id))
        nodo.setAttribute("nitCliente", self.nit_cliente)
        nodo.setAttribute("fecha", self.fecha)

        detalle = doc.createElement("detalle")
        for i in self.items:
            item = doc.createElement("item")
            for k, v in i.items():
                item.setAttribute(k, str(v))
            detalle.appendChild(item)
        nodo.appendChild(detalle)

        total_elem = doc.createElement("total")
        total_elem.appendChild(doc.createTextNode(f"{self.total():.2f}"))
        nodo.appendChild(total_elem)
        return nodo

class Consumo:
    def __init__(self, nit_cliente, id_instancia, tiempo, fecha_hora):
        self.nit_cliente = nit_cliente
        self.id_instancia = id_instancia
        self.tiempo = float(tiempo)
        self.fecha_hora = fecha_hora 

    def a_xml(self, doc: Document):
        # crea el nodo <consumo> con subnodos tiempo y fechaHora
        nodo = doc.createElement("consumo")
        nodo.setAttribute("nitCliente", self.nit_cliente)
        nodo.setAttribute("idInstancia", str(self.id_instancia))

        t = doc.createElement("tiempo")
        t.appendChild(doc.createTextNode(f"{self.tiempo}"))
        nodo.appendChild(t)

        fh = doc.createElement("fechaHora")
        fh.appendChild(doc.createTextNode(self.fecha_hora))
        nodo.appendChild(fh)

        return nodo

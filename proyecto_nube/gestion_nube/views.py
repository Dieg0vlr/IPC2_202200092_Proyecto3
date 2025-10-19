from django.shortcuts import render
import requests
from django.http import HttpResponseRedirect

# Create your views here.

BASE_API = "http://127.0.0.1:5000/api"

def index(request):
    return render(request, 'index.html')

def enviar_config(request):
    msg = None
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        try:
            contenido = archivo.read().decode("utf-8")

            # enviar al backend Flask
            r = requests.post(f"{BASE_API}/config", data=contenido.encode("utf-8"),
                              headers={"Content-Type": "application/xml"})
            if r.status_code == 201:
                msg = "Archivo enviado y procesado correctamente"
            else:
                msg = f"Error desde backend: {r.text}"
        except Exception as e:
            msg = f"Error: {str(e)}"

    return render(request, "enviar_config.html", {"msg": msg})

def enviar_consumo(request):
    msg = None
    if request.method == "POST" and request.FILES.get("archivo"):
        archivo = request.FILES["archivo"]
        try:
            contenido = archivo.read().decode("utf-8")

            r = requests.post(f"{BASE_API}/consumo", data=contenido.encode("utf-8"),
                              headers={"Content-Type": "application/xml"})
            if r.status_code == 201:
                msg = "Archivo de consumo procesado correctamente"
            else:
                msg = f"Error desde backend: {r.text}"
        except Exception as e:
            msg = f"Error: {str(e)}"

    return render(request, "enviar_consumo.html", {"msg": msg})


def operaciones(request):
    msg = ""
    if request.method =="POST":
        accion = request.POST.get("accion")
        if accion == "reiniciar":
            r = requests.post("http://127.0.0.1:5000/api/init")
            msg = r.json().get("mensaje", "")
        elif accion == "consultar":
            r = requests.get("http://127.0.0.1:5000/api/consultar")    
            estado = r.json()
            msg = f"Base de datos encontrada: {estado['hay_datos']}"
    return render(request, "operaciones.html", {"msg": msg})         

def facturar(request):
    try:
        r = requests.post(f"{BASE_API}/facturar", timeout=10)
        data = r.json()
        if data["ok"]:
            msg = f"Factura generada correctamente. Total: {data['total_global']}"
        else:
            msg = f"Error: {data['error']}"
    except Exception as e:
        msg = f"Error: {str(e)}"
    
    return render(request, 'index.html', {"msg": msg})


def reportes(request):
    return render(request, 'reportes.html')

def ayuda(request):
    info = {
        "autor": "Diego Alberto Maldonado Galvez",
        "carnet": "202200092",
        "curso": "Introducción a la Programación y Computación 2",
        "proyecto": "Proyecto 3 — Sistema de Gestión en la Nube",
        "descripcion": (
            "Este sistema permite gestionar recursos, clientes y consumos en la nube. "
            "Carga archivos XML de configuración y consumo, genera facturas, "
            "produce reportes PDF y analiza ventas por categoría, configuración o recurso."
        )
    }
    return render(request, "ayuda.html", {"info": info})

def generar_reporte_factura(request, id_factura):
    try:
        r = requests.get(f"{BASE_API}/reporte/factura/{id_factura}")
        data = r.json()

        if data["ok"]:
            msg = f"Reporte generado correctamente: {data['mensaje']}"
        else:
            msg = f"Error: {data['error']}"

    except Exception as e:
        msg = f"Error: {str(e)}"

    return render(request, 'index.html', {"msg": msg})

# Redirige al backend Flask para mostrar el PDF
def ver_pdf(request, id_factura):

    flask_url = f"http://127.0.0.1:5000/api/reporte/factura/{id_factura}/ver"
    return HttpResponseRedirect(flask_url)
          


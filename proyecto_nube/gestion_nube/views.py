from django.shortcuts import render
import requests

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

    return render(request, "enviar_config.html", {"msg": msg})


def operaciones(request):
    try:
        r = requests.get(f"{BASE_API}/consultar", timeout=5)
        data = r.json()
    except Exception:
        data = {"estado": "backend no disponible"}
    return render(request, 'index.html', {"data": data})

def facturar(request):
    return render(request, 'index.html', {"msg": "Pantalla para facturar"})

def reportes(request):
    return render(request, 'index.html', {"msg": "Pantalla de reportes"})

def ayuda(request):
    return render(request, 'index.html', {"msg": "Ayuda"})
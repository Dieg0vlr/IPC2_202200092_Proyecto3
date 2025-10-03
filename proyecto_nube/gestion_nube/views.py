from django.shortcuts import render
import requests

# Create your views here.

def index(request):
    return render(request, 'index.html')

BASE_API = "http://127.0.0.1:5000/api"

def index(request):
    return render(request, 'index.html')

def enviar_config(request):
    return render(request, 'index.html', {"msg": "Pantalla para enviar XML de configuracion"})

def enviar_consumo(request):
    return render(request, 'index.html', {"msg": "Pantalla para enviar XML de consumo"})

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
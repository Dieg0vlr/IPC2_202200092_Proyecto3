"""
URL configuration for proyecto_nube project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from gestion_nube import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('config/', views.enviar_config, name='enviar_config'),
    path('consumo/', views.enviar_consumo, name='enviar_consumo'),
    path('operaciones/', views.operaciones, name='operaciones'),
    path('facturar/', views.facturar, name='facturar'),
    path('reportes/', views.reportes, name='reportes'),
    path('ayuda/', views.ayuda, name='ayuda'),
    path('reporte/factura/<int:id_factura>/', views.generar_reporte_factura, name='reporte_factura'),
    path('ayuda/', views.ayuda, name='ayuda'),
    path('reporte/factura/<int:id_factura>/ver', views.ver_pdf, name='ver_pdf'),


]


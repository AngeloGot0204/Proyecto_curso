"""
URL configuration for config project.

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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from reportes.views import service_worker

urlpatterns = [
    # Root-level, outside WhiteNoise's `/static/` prefix (change
    # `capa-offline`; design's "Root-Scoped Service Worker Route") — must
    # stay listed before the `reportes/` include so `/sw.js` never falls
    # through to it.
    path('sw.js', service_worker, name='service_worker'),
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('reportes/', include('reportes.urls')),
    path('tipos-reporte/', include('tipos_reporte.urls')),
]

# Code-review fix: without this, uploaded files (TipoDeReporte.logo,
# plantilla, DefinicionDeTipo.archivo_yaml) are unreachable at their URL
# even locally — the admin's "Currently: <file>" link 404s. Standard
# Django convention: only in development (DEBUG=True); production media
# serving is out of scope here (design decision D10).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

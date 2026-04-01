"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path, include
from django.http import HttpResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def home(request):
    return HttpResponse(
        """
        <!doctype html>
        <html lang='fr'>
        <head>
            <meta charset='utf-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1'>
            <title>BKO Stations API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; }
                h1 { color: #0a4d8c; }
                code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }
                a { color: #0a4d8c; }
            </style>
        </head>
        <body>
            <h1>BKO Stations Backend</h1>
            <p>Le service API est en ligne.</p>
            <p>Endpoints utiles :</p>
            <ul>
                <li><a href='/api/health/'><code>/api/health/</code></a></li>
                <li><a href='/api/stations/'><code>/api/stations/</code></a></li>
                <li><a href='/admin/'><code>/admin/</code></a></li>
            </ul>
        </body>
        </html>
        """
    )


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('stations.urls')),
]

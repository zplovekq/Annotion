"""app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
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
from django.contrib.auth.views import PasswordResetView, LogoutView
from server.views import LoginView
from server.urls import router
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('', include('server.urls')),
    path('admin/', admin.site.urls),
    path('login/', csrf_exempt(LoginView.as_view()), name='login'),
    path('logout/', csrf_exempt(LogoutView.as_view()), name='logout'),
    path('password_reset/', csrf_exempt(PasswordResetView.as_view()), name='password_reset'),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include(router.urls)),
]

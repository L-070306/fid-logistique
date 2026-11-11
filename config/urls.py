from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),  # gestion des utilisateurs et des groupes
    path("connexion/", auth.LoginView.as_view(), name="login"),
    path("deconnexion/", auth.LogoutView.as_view(), name="logout"),
    path("", include("logistique.urls")),
]

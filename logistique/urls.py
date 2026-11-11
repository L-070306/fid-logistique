from django.urls import path

from . import views

urlpatterns = [path("", views.TableauBord.as_view(), name="tableau_bord")]

for cle, cfg in views.ENTITES.items():
    v = views.fabriquer_vues(cle, cfg)
    urlpatterns += [
        path(f"{cle}/", v["Liste"].as_view(), name=f"{cle}_liste"),
        path(f"{cle}/ajouter/", v["Creer"].as_view(), name=f"{cle}_ajouter"),
        path(f"{cle}/<int:pk>/supprimer/", v["Supprimer"].as_view(), name=f"{cle}_supprimer"),
    ]
    if cfg.get("modifiable", True):
        urlpatterns.append(path(f"{cle}/<int:pk>/modifier/", v["Modifier"].as_view(), name=f"{cle}_modifier"))

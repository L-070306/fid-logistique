from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import Article, Carburant, Demande, Mouvement, Vehicule

# Une entrée par page. modifiable=False : le journal des mouvements ne se modifie pas
# (on ajoute ou on supprime, ce qui garde le stock cohérent).
ENTITES = {
    "vehicules": dict(modele=Vehicule, titre="Véhicules",
                      colonnes=["immatriculation", "marque", "statut", "kilometrage", "actif"]),
    "carburant": dict(modele=Carburant, titre="Carburant",
                      colonnes=["date", "vehicule", "litres", "cout", "km"]),
    "articles": dict(modele=Article, titre="Articles en stock",
                     colonnes=["nom", "unite", "stock", "seuil", "actif"]),
    "mouvements": dict(modele=Mouvement, titre="Mouvements de stock", modifiable=False,
                       colonnes=["date", "article", "type", "quantite", "note"]),
    "demandes": dict(modele=Demande, titre="Demandes d'achat",
                     colonnes=["date", "service", "objet", "montant", "statut"]),
}


def entete(modele, nom):
    return "Stock" if nom == "stock" else str(modele._meta.get_field(nom).verbose_name)


def valeur(obj, nom):
    affichage = getattr(obj, f"get_{nom}_display", None)
    v = affichage() if affichage else getattr(obj, nom)
    return "Oui" if v is True else "Non" if v is False else v


class Acces(PermissionRequiredMixin):
    """Connexion obligatoire + droit Django (view/add/change/delete) sur le modèle."""
    action = "view"

    def get_permission_required(self):
        m = self.modele._meta
        return [f"{m.app_label}.{self.action}_{m.model_name}"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.contexte)
        return ctx


def fabriquer_vues(cle, cfg):
    _m, _cols = cfg["modele"], cfg["colonnes"]
    _form = forms.modelform_factory(
        _m, fields="__all__",
        widgets={"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")})
    _liste = reverse_lazy(f"{cle}_liste")
    _ctx = {"titre": cfg["titre"], "modifiable": cfg.get("modifiable", True),
            "url_liste": f"{cle}_liste", "url_ajouter": f"{cle}_ajouter",
            "url_modifier": f"{cle}_modifier", "url_supprimer": f"{cle}_supprimer"}

    class Liste(Acces, ListView):
        modele, contexte = _m, _ctx
        template_name = "liste.html"
        paginate_by = 50

        def get_queryset(self):
            qs = _m.objects.all()
            fk = [f.name for f in _m._meta.get_fields() if f.many_to_one]
            if fk:
                qs = qs.select_related(*fk)
            if hasattr(qs, "avec_stock"):
                qs = qs.avec_stock()
            if "actif" in _cols and not self.request.GET.get("archives"):
                qs = qs.filter(actif=True)
            return qs

        def get_context_data(self, **kwargs):
            c = super().get_context_data(**kwargs)
            u, meta = self.request.user, _m._meta
            archives = bool(self.request.GET.get("archives"))
            c.update(
                entetes=[entete(_m, n) for n in _cols], nb_colonnes=len(_cols) + 1,
                lignes=[{"pk": o.pk, "cellules": [valeur(o, n) for n in _cols],
                         "alerte": _m is Article and o.actif and o.stock <= o.seuil}
                        for o in c["object_list"]],
                peut_ajouter=u.has_perm(f"{meta.app_label}.add_{meta.model_name}"),
                peut_modifier=u.has_perm(f"{meta.app_label}.change_{meta.model_name}"),
                peut_supprimer=u.has_perm(f"{meta.app_label}.delete_{meta.model_name}"),
                a_archives="actif" in _cols, archives=archives,
                suite="&archives=1" if archives else "")
            return c

    class Creer(Acces, CreateView):
        modele, contexte, action = _m, {**_ctx, "mode": "Ajouter"}, "add"
        form_class, success_url, template_name = _form, _liste, "formulaire.html"

        def form_valid(self, form):
            reponse = super().form_valid(form)
            messages.success(self.request, f"« {self.object} » a été ajouté.")
            return reponse

    class Modifier(Acces, UpdateView):
        modele, contexte, action = _m, {**_ctx, "mode": "Modifier"}, "change"
        model, form_class, success_url, template_name = _m, _form, _liste, "formulaire.html"

        def form_valid(self, form):
            reponse = super().form_valid(form)
            messages.success(self.request, f"« {self.object} » a été modifié.")
            return reponse

    class Supprimer(Acces, DeleteView):
        modele, contexte, action = _m, _ctx, "delete"
        model, success_url, template_name = _m, _liste, "supprimer.html"

        def form_valid(self, form):
            nom = str(self.object)
            try:
                reponse = super().form_valid(form)
            except ProtectedError:
                messages.error(self.request, "Suppression impossible : des données y sont rattachées. "
                                             "Archivez plutôt l'élément (décochez « Actif »).")
                return redirect(_liste)
            except ValidationError as e:
                messages.error(self.request, " ".join(e.messages))
                return redirect(_liste)
            messages.success(self.request, f"« {nom} » a été supprimé.")
            return reponse

    return {"Liste": Liste, "Creer": Creer, "Modifier": Modifier, "Supprimer": Supprimer}


class TableauBord(LoginRequiredMixin, TemplateView):
    template_name = "tableau_bord.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vehicules = Vehicule.objects.filter(actif=True)
        auj = timezone.localdate()
        articles = Article.objects.filter(actif=True).avec_stock()
        ctx.update(
            nb_vehicules=vehicules.count(),
            nb_disponibles=vehicules.filter(statut="Disponible").count(),
            par_statut=vehicules.order_by().values("statut").annotate(n=Count("id")).order_by("statut"),
            alertes=[a for a in articles if a.stock <= a.seuil],
            nb_attente=Demande.objects.filter(statut="Soumise").count(),
            dernieres_demandes=Demande.objects.all()[:5],
            carburant_mois=Carburant.objects.filter(date__year=auj.year, date__month=auj.month)
                                    .aggregate(t=Sum("cout"))["t"] or 0,
        )
        return ctx

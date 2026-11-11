from django.apps import AppConfig


class LogistiqueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logistique"

    def ready(self):
        from django.contrib import messages
        from django.contrib.auth.signals import user_logged_in, user_logged_out

        def bienvenue(sender, request, user, **kwargs):
            if request is not None:
                messages.success(request, f"Bienvenue, {user.get_username()}.", fail_silently=True)

        def au_revoir(sender, request, user, **kwargs):
            if request is not None:
                messages.info(request, "Vous êtes déconnecté.", fail_silently=True)

        user_logged_in.connect(bienvenue, dispatch_uid="fid_bienvenue")
        user_logged_out.connect(au_revoir, dispatch_uid="fid_au_revoir")

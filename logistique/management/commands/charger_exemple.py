from django.core.management.base import BaseCommand

from logistique.models import Article, Carburant, Demande, Mouvement, Vehicule


class Command(BaseCommand):
    help = "Charge quelques données de démonstration (sans effet si elles existent déjà)."

    def handle(self, *args, **options):
        v1, _ = Vehicule.objects.get_or_create(immatriculation="1234 TAA", defaults={"marque": "Toyota Hilux", "kilometrage": 45200})
        v2, _ = Vehicule.objects.get_or_create(immatriculation="5678 TBB", defaults={"marque": "Nissan Navara", "statut": "En mission", "kilometrage": 78900})
        Vehicule.objects.get_or_create(immatriculation="9012 TCC", defaults={"marque": "Toyota Land Cruiser", "statut": "En maintenance", "kilometrage": 120300})
        for nom, unite, seuil, entree, sortie in [("Ramettes de papier A4", "ramette", 20, 100, 85),
                                                  ("Cartouches d'encre", "pièce", 5, 12, 8),
                                                  ("Gilets de sécurité", "pièce", 10, 30, 12)]:
            article, cree = Article.objects.get_or_create(nom=nom, defaults={"unite": unite, "seuil": seuil})
            if cree:
                Mouvement.objects.create(article=article, type="E", quantite=entree, note="Stock initial")
                Mouvement.objects.create(article=article, type="S", quantite=sortie, note="Consommation")
        if not Carburant.objects.exists():
            for v, km, litres, cout in [(v1, 45000, 50, 250000), (v1, 45600, 45, 225000),
                                        (v2, 78500, 60, 300000), (v2, 79000, 55, 275000)]:
                Carburant.objects.create(vehicule=v, litres=litres, cout=cout, km=km)
        if not Demande.objects.exists():
            Demande.objects.create(service="Ingénierie", objet="Pneus pour Hilux", montant=1800000)
        self.stdout.write(self.style.SUCCESS("Données d'exemple chargées."))

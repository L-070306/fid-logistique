from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Article, Carburant, Demande, Mouvement, Vehicule


class RegleMetierTests(TestCase):
    def setUp(self):
        self.v = Vehicule.objects.create(immatriculation="1234 TAA")
        self.a = Article.objects.create(nom="Papier", seuil=10)
        Mouvement.objects.create(article=self.a, type="E", quantite=100)

    def test_stock_calcule(self):
        Mouvement.objects.create(article=self.a, type="S", quantite=30)
        self.assertEqual(self.a.stock, 70)

    def test_sortie_superieure_au_stock_refusee(self):
        with self.assertRaises(ValidationError):
            Mouvement.objects.create(article=self.a, type="S", quantite=150)

    def test_suppression_entree_qui_rend_stock_negatif_refusee(self):
        Mouvement.objects.create(article=self.a, type="S", quantite=80)
        with self.assertRaises(ValidationError):
            Mouvement.objects.get(type="E").delete()

    def test_vehicule_avec_historique_protege(self):
        Carburant.objects.create(vehicule=self.v, litres=50, cout=250000, km=45600)
        with self.assertRaises(ProtectedError):
            self.v.delete()

    def test_kilometrage_suit_le_plein(self):
        Carburant.objects.create(vehicule=self.v, litres=50, cout=250000, km=45600)
        self.v.refresh_from_db()
        self.assertEqual(self.v.kilometrage, 45600)

    def test_demande_approuvee_non_supprimable(self):
        d = Demande.objects.create(objet="Pneus", statut="Approuvée")
        with self.assertRaises(ValidationError):
            d.delete()


class PagesTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin", password="x"))

    def test_pages_accessibles(self):
        for nom in ("tableau_bord", "vehicules_liste", "vehicules_ajouter", "carburant_liste", "carburant_ajouter",
                    "articles_liste", "articles_ajouter", "mouvements_liste", "mouvements_ajouter",
                    "demandes_liste", "demandes_ajouter"):
            self.assertEqual(self.client.get(reverse(nom)).status_code, 200, nom)

    def test_ajout_par_formulaire(self):
        r = self.client.post(reverse("vehicules_ajouter"), {
            "immatriculation": "abc 123", "marque": "Test", "statut": "Disponible", "kilometrage": 10, "actif": "on"})
        self.assertRedirects(r, reverse("vehicules_liste"))
        self.assertTrue(Vehicule.objects.filter(immatriculation="ABC 123").exists())

    def test_sortie_trop_grande_refusee_par_formulaire(self):
        a = Article.objects.create(nom="Gants")
        r = self.client.post(reverse("mouvements_ajouter"), {
            "date": "2026-11-03", "article": a.pk, "type": "S", "quantite": 5, "note": ""})
        self.assertEqual(r.status_code, 200)  # le formulaire est réaffiché avec l'erreur
        self.assertFalse(Mouvement.objects.exists())

    def test_suppression_protegee_affiche_un_message(self):
        v = Vehicule.objects.create(immatriculation="9999 ZZZ")
        Carburant.objects.create(vehicule=v, litres=10, cout=1000, km=5)
        r = self.client.post(reverse("vehicules_supprimer", args=[v.pk]), follow=True)
        self.assertTrue(Vehicule.objects.filter(pk=v.pk).exists())
        self.assertContains(r, "Suppression impossible")

    def test_logo_affiche_sur_les_pages(self):
        self.assertContains(self.client.get(reverse("tableau_bord")), "img/emblem-fid.png")
        self.client.logout()
        self.assertContains(self.client.get(reverse("login")), "img/logo-fid.jpg")

    def test_toast_apres_ajout(self):
        r = self.client.post(reverse("vehicules_ajouter"), {
            "immatriculation": "toast 1", "marque": "T", "statut": "Disponible", "kilometrage": 0, "actif": "on"}, follow=True)
        self.assertContains(r, 'class="toast success"')
        self.assertContains(r, "TOAST 1")

    def test_toast_erreur_quand_suppression_refusee(self):
        v = Vehicule.objects.create(immatriculation="8888 YYY")
        Carburant.objects.create(vehicule=v, litres=10, cout=1000, km=5)
        r = self.client.post(reverse("vehicules_supprimer", args=[v.pk]), follow=True)
        self.assertContains(r, 'class="toast error"')
        self.assertContains(r, 'role="alert"')

    def test_toast_connexion_et_deconnexion(self):
        self.client.logout()
        get_user_model().objects.create_user("jean", password="mdp-solide-123")
        r = self.client.post(reverse("login"), {"username": "jean", "password": "mdp-solide-123"}, follow=True)
        self.assertContains(r, "Bienvenue, jean.")
        r = self.client.post(reverse("logout"), follow=True)
        self.assertContains(r, "Vous êtes déconnecté.")

    def test_acces_sans_connexion_redirige(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("vehicules_liste")).status_code, 302)

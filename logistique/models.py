from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce, Greatest


class Vehicule(models.Model):
    STATUTS = [(s, s) for s in ("Disponible", "En mission", "En maintenance", "Hors service")]
    immatriculation = models.CharField("Immatriculation", max_length=20, unique=True)
    marque = models.CharField("Marque / modèle", max_length=60, blank=True)
    statut = models.CharField("Statut", max_length=20, choices=STATUTS, default="Disponible")
    kilometrage = models.PositiveIntegerField("Kilométrage", default=0)
    actif = models.BooleanField("Actif", default=True,
                                help_text="Décochez pour archiver (l'historique est conservé).")

    class Meta:
        ordering = ["immatriculation"]

    def clean(self):
        self.immatriculation = (self.immatriculation or "").strip().upper()

    def __str__(self):
        return self.immatriculation


class Carburant(models.Model):
    date = models.DateField("Date", default=date.today)
    vehicule = models.ForeignKey(Vehicule, verbose_name="Véhicule", on_delete=models.PROTECT,
                                 limit_choices_to={"actif": True})
    litres = models.DecimalField("Litres", max_digits=8, decimal_places=2,
                                 validators=[MinValueValidator(Decimal("0.01"))])
    cout = models.PositiveIntegerField("Coût (Ar)", default=0)
    km = models.PositiveIntegerField("Km au compteur", default=0)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "carburant"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # le kilométrage du véhicule suit le plus grand relevé
        Vehicule.objects.filter(pk=self.vehicule_id).update(kilometrage=Greatest("kilometrage", self.km))

    def __str__(self):
        return f"{self.vehicule} - {self.date}"


class ArticleQuerySet(models.QuerySet):
    def avec_stock(self):
        entrees = Coalesce(Sum("mouvements__quantite", filter=Q(mouvements__type="E")), 0)
        sorties = Coalesce(Sum("mouvements__quantite", filter=Q(mouvements__type="S")), 0)
        return self.annotate(stock_calc=entrees - sorties).order_by("nom")


class Article(models.Model):
    nom = models.CharField("Nom", max_length=120, unique=True)
    unite = models.CharField("Unité", max_length=30, default="pièce")
    seuil = models.PositiveIntegerField("Seuil d'alerte", default=0)
    actif = models.BooleanField("Actif", default=True,
                                help_text="Décochez pour archiver (l'historique est conservé).")
    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ["nom"]

    @property
    def stock(self):
        if hasattr(self, "stock_calc"):
            return self.stock_calc
        if not self.pk:
            return 0
        return type(self).objects.avec_stock().values_list("stock_calc", flat=True).get(pk=self.pk)

    def __str__(self):
        return self.nom


class Mouvement(models.Model):
    TYPES = [("E", "Entrée"), ("S", "Sortie")]
    date = models.DateField("Date", default=date.today)
    article = models.ForeignKey(Article, verbose_name="Article", on_delete=models.PROTECT,
                                related_name="mouvements", limit_choices_to={"actif": True})
    type = models.CharField("Type", max_length=1, choices=TYPES)
    quantite = models.PositiveIntegerField("Quantité", validators=[MinValueValidator(1)])
    note = models.CharField("Note", max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def clean(self):
        if self.type == "S" and self.article_id and self.quantite and self.quantite > self.article.stock:
            raise ValidationError(f"Stock insuffisant : {self.article.stock} {self.article.unite} disponible(s).")

    def save(self, *args, **kwargs):
        self.clean()  # la règle s'applique aussi hors formulaire (shell, scripts, import)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.type == "E" and self.article.stock - self.quantite < 0:
            raise ValidationError("Suppression impossible : le stock deviendrait négatif.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.date} {self.get_type_display()} {self.quantite} {self.article}"


class Demande(models.Model):
    STATUTS = [(s, s) for s in ("Soumise", "Approuvée", "Rejetée", "Commandée", "Reçue")]
    date = models.DateField("Date", default=date.today)
    service = models.CharField("Service", max_length=80, blank=True)
    objet = models.CharField("Objet", max_length=200)
    montant = models.PositiveIntegerField("Montant (Ar)", default=0)
    statut = models.CharField("Statut", max_length=20, choices=STATUTS, default="Soumise")

    class Meta:
        ordering = ["-id"]

    def delete(self, *args, **kwargs):
        if self.statut not in ("Soumise", "Rejetée"):
            raise ValidationError("Seules les demandes soumises ou rejetées peuvent être supprimées.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.objet

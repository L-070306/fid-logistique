/* Toasts (bulles de notification).
   - Les messages Django (django.contrib.messages) sont affichés par base.html dans #toasts.
   - Depuis du JavaScript, on peut aussi appeler :  toast("Texte", "success")
     types : success, info, warning, error. */
(function () {
  "use strict";
  var conteneur = document.getElementById("toasts");
  if (!conteneur) { return; }

  // Durée d'affichage en millisecondes (les erreurs restent plus longtemps)
  var DUREES = { success: 4000, info: 5000, warning: 7000, error: 10000 };

  function fermer(toast) {
    if (toast.dataset.ferme) { return; }
    toast.dataset.ferme = "1";
    toast.classList.add("sortie");
    setTimeout(function () { toast.remove(); }, 250);
  }

  function armer(toast) {
    var type = "info";
    Object.keys(DUREES).forEach(function (t) { if (toast.classList.contains(t)) { type = t; } });
    toast.querySelector(".toast-fermer").addEventListener("click", function () { fermer(toast); });

    var reste = DUREES[type], debut = 0, minuteur = null, enPause = false;
    toast.style.setProperty("--duree", reste + "ms");
    toast.classList.add("avec-barre");

    function demarrer() {
      debut = Date.now();
      minuteur = setTimeout(function () { fermer(toast); }, reste);
      enPause = false;
      toast.classList.remove("pause");
    }
    function suspendre() {  // on laisse le temps de lire quand la souris ou le clavier est sur la bulle
      if (enPause) { return; }
      clearTimeout(minuteur);
      reste -= Date.now() - debut;
      enPause = true;
      toast.classList.add("pause");
    }
    function reprendre() { if (enPause) { demarrer(); } }

    toast.addEventListener("mouseenter", suspendre);
    toast.addEventListener("mouseleave", reprendre);
    toast.addEventListener("focusin", suspendre);
    toast.addEventListener("focusout", reprendre);
    demarrer();
  }

  window.toast = function (texte, type) {
    type = DUREES[type] ? type : "info";
    var toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.setAttribute("role", type === "error" ? "alert" : "status");
    var icone = document.createElement("span");
    icone.className = "toast-icone";
    icone.setAttribute("aria-hidden", "true");
    var p = document.createElement("p");
    p.className = "toast-texte";
    p.textContent = texte;  // textContent : pas d'injection de HTML
    var bouton = document.createElement("button");
    bouton.type = "button";
    bouton.className = "toast-fermer";
    bouton.setAttribute("aria-label", "Fermer");
    bouton.textContent = "\u00d7";
    toast.append(icone, p, bouton);
    conteneur.appendChild(toast);
    armer(toast);
  };

  Array.prototype.forEach.call(conteneur.querySelectorAll(".toast"), armer);
})();

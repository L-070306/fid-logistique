# Plateforme Logistique FID

Site web de gestion du parc automobile, du carburant, des stocks et des demandes d'achat.
Frontend HTML/CSS (templates Django) · Backend Python (Django) · Base MySQL · Déploiement Ansible.

## Structure
```
config/        réglages Django (lus depuis .env ou les variables d'environnement)
logistique/    models.py (données + règles), views.py (pages), urls.py, tests.py
templates/     pages HTML          static/css/   feuille de style
deploiement/   playbook Ansible (deploy.yml) et ses modèles
```

## Lancer en local (Windows)
1. Installer MySQL (MySQL Installer) ou MariaDB (ex. XAMPP), puis dans la console SQL :
   ```sql
   CREATE DATABASE fid_logistique CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'fid_app'@'localhost' IDENTIFIED BY 'motdepasse';
   GRANT ALL PRIVILEGES ON fid_logistique.* TO 'fid_app'@'localhost';
   GRANT ALL PRIVILEGES ON `test\_fid\_logistique`.* TO 'fid_app'@'localhost';  -- pour les tests
   ```
2. Dans le dossier du projet :
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   python -m pip install -r requirements.txt
   copy .env.example .env          # puis adapter DB_PASSWORD
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py charger_exemple   # données de démonstration (facultatif)
   python manage.py runserver
   ```
3. Ouvrir http://127.0.0.1:8000 et se connecter.
4. Tests : `python manage.py test`

## Utilisateurs et droits
Le superutilisateur a tous les droits. Pour les autres comptes, créez des groupes dans
http://127.0.0.1:8000/admin/ (ex. « Magasinier » : droits sur Article et Mouvement).
Sans droit sur une page, l'utilisateur reçoit une erreur 403.

## Déployer avec Ansible
Prérequis : un serveur Ubuntu 22.04/24.04 en SSH, le code poussé sur GitHub, Ansible
(sous Windows : via WSL).
```bash
cd deploiement
ansible-galaxy collection install -r requirements.yml
cp inventaire.ini.example inventaire.ini            # adresse du serveur
cp group_vars/all/vault.yml.example group_vars/all/vault.yml
nano group_vars/all/vault.yml                       # mots de passe
ansible-vault encrypt group_vars/all/vault.yml
nano group_vars/all/vars.yml                        # repo_url, domaine
ansible-playbook deploy.yml --ask-vault-pass --ask-become-pass
```
Relancer la même commande suffit pour mettre à jour l'application.

## Notifications (toasts)
Les messages Django (`messages.success(...)`, `messages.error(...)`, etc.) s'affichent en bulles
en bas à droite : `templates/base.html` (conteneur), `static/js/toast.js` (comportement),
`static/css/style.css` (apparence). Depuis JavaScript : `toast("Texte", "success")`
(types : success, info, warning, error).

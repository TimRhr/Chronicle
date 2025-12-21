#!/usr/bin/env python3
"""Fill French translations for common UI strings."""

from __future__ import annotations


TRANSLATIONS: dict[str, str] = {
    # Auth & Login
    "Invalid credentials.": "Identifiants invalides.",
    "You have been logged out.": "Vous avez été déconnecté.",
    "Please log in to view this page.": "Veuillez vous connecter pour voir cette page.",
    "Login": "Connexion",
    "Logout": "Déconnexion",
    "Register": "S’inscrire",
    "Email": "E-mail",
    "Password": "Mot de passe",
    "Username": "Nom d’utilisateur",
    "Remember me": "Se souvenir de moi",
    "Forgot password?": "Mot de passe oublié ?",
    "Don't have an account?": "Vous n’avez pas de compte ?",
    "Already have an account?": "Vous avez déjà un compte ?",
    "Create account": "Créer un compte",
    "Sign in with Keycloak": "Se connecter avec Keycloak",
    "or": "ou",

    # Navigation & UI
    "Loading...": "Chargement...",
    "No notifications": "Aucune notification",
    "Mark all as read": "Tout marquer comme lu",
    "Notifications": "Notifications",
    "Show more": "Afficher plus",
    "Show less": "Afficher moins",
    "more": "plus",
    "Feed": "Fil",
    "Search": "Rechercher",
    "Settings": "Paramètres",
    "My Profile": "Mon profil",
    "Close": "Fermer",
    "Cancel": "Annuler",
    "Save": "Enregistrer",
    "Delete": "Supprimer",
    "Edit": "Modifier",
    "Confirm": "Confirmer",
    "Back": "Retour",
    "Next": "Suivant",
    "Previous": "Précédent",
    "Yes": "Oui",
    "No": "Non",
    "OK": "OK",
    "Try again": "Réessayer",

    # Posts
    "New Post": "Nouvelle publication",
    "Create post": "Créer une publication",
    "Edit post": "Modifier la publication",
    "Delete post": "Supprimer la publication",
    "Post": "Publication",
    "Posts": "Publications",
    "No posts yet": "Aucune publication pour le moment",
    "No posts found": "Aucune publication trouvée",
    "No more posts": "Plus de publications",
    "Create first post": "Créer la première publication",
    "No posts have been published yet.": "Aucune publication n’a encore été publiée.",
    "No posts match the selected filters.": "Aucune publication ne correspond aux filtres sélectionnés.",
    "Reset filters": "Réinitialiser les filtres",
    "edited": "modifié",
    "Title": "Titre",
    "Content": "Contenu",
    "Tags": "Tags",
    "Publish": "Publier",
    "Draft": "Brouillon",
    "Published": "Publié",
    "Scheduled": "Programmé",
    "Schedule post": "Programmer la publication",
    "Image": "Image",
    "Images": "Images",
    "Upload image": "Téléverser une image",
    "Remove image": "Retirer l’image",

    # Comments
    "Comments": "Commentaires",
    "Write a comment...": "Écrire un commentaire...",
    "Send": "Envoyer",
    "Reply": "Répondre",
    "No comments yet.": "Aucun commentaire pour le moment.",
    "Delete comment": "Supprimer le commentaire",
    "older comments": "commentaires plus anciens",
    "Show replies": "Afficher les réponses",
    "Hide replies": "Masquer les réponses",
    "reply": "réponse",
    "replies": "réponses",

    # Reactions & Interactions
    "Bookmark": "Favori",
    "Bookmarked": "Mis en favori",
    "Bookmarks": "Favoris",
    "React": "Réagir",
    "Click to change": "Cliquer pour changer",
    "Remove reaction": "Retirer la réaction",
    "Please log in to react.": "Veuillez vous connecter pour réagir.",
    "to comment.": "pour commenter.",

    # Groups
    "Groups": "Groupes",
    "Group": "Groupe",
    "Create group": "Créer un groupe",
    "New group": "Nouveau groupe",
    "All groups": "Tous les groupes",
    "View all groups": "Voir tous les groupes",
    "No groups yet": "Aucun groupe pour le moment",
    "You are not in any group yet.": "Vous n’êtes dans aucun groupe pour le moment.",
    "Create a group to share private posts with others.": "Créez un groupe pour partager des publications privées avec d’autres.",
    "Members": "Membres",
    "Leave": "Quitter",
    "Back to group": "Retour au groupe",
    "Group color": "Couleur du groupe",
    "Group icon": "Icône du groupe",
    "Description": "Description",
    "What is this group about?": "De quoi s’agit-il ?",
    "Share the first post in this group.": "Partagez la première publication dans ce groupe.",
    "Invite all": "Inviter tout le monde",
    "Remove member": "Retirer le membre",
    "Remove": "Retirer",
    "Delete group": "Supprimer le groupe",
    "No users found": "Aucun utilisateur trouvé",

    # Files
    "Files": "Fichiers",
    "Upload file": "Téléverser un fichier",
    "Upload": "Téléverser",
    "Download": "Télécharger",
    "Delete file": "Supprimer le fichier",
    "No files yet": "Aucun fichier pour le moment",
    "Upload the first file to share it with the group.": "Téléversez le premier fichier pour le partager avec le groupe.",
    "Drag file here or": "Glissez le fichier ici ou",
    "click to select": "cliquez pour sélectionner",
    "Max. 50MB · Allowed:": "Max. 50 Mo · Autorisé :",
    "Short description of the file...": "Courte description du fichier...",
    "View": "Voir",

    # Announcements
    "Announcement": "Annonce",
    "New announcement": "Nouvelle annonce",
    "Edit announcement": "Modifier l’annonce",
    "Create announcement": "Créer une annonce",
    "Delete announcement": "Supprimer l’annonce",
    "Write your announcement... (Markdown is supported)": "Écrivez votre annonce... (Markdown est pris en charge)",
    "Markdown is supported: **bold**, *italic*, [links](url), lists, etc.": "Markdown est pris en charge : **gras**, *italique*, [liens](url), listes, etc.",
    "Border color": "Couleur de bordure",
    "Preview": "Aperçu",
    "Preview appears here...": "L’aperçu apparaît ici...",
    "Create": "Créer",

    # Pages
    "Pages": "Pages",
    "Page": "Page",
    "Manage pages": "Gérer les pages",
    "Create page": "Créer une page",
    "Edit page": "Modifier la page",
    "Delete page": "Supprimer la page",
    "No pages yet": "Aucune page pour le moment",
    "Page title": "Titre de la page",
    "Show in navigation": "Afficher dans la navigation",

    # Profile & Settings
    "Profile": "Profil",
    "About me": "À propos de moi",
    "Bio": "Bio",
    "Display name": "Nom affiché",
    "Theme color": "Couleur du thème",
    "Text color": "Couleur du texte",
    "Font Family": "Police",
    "optional": "optionnel",
    "Enable comments": "Activer les commentaires",
    "Enable reactions": "Activer les réactions",
    "Organization": "Organisation",

    # Search
    "Search posts...": "Rechercher des publications...",
    "Search users...": "Rechercher des utilisateurs...",
    "No results": "Aucun résultat",
    "No results found": "Aucun résultat trouvé",

    # Archive
    "Archive": "Archives",
    "All Posts": "Toutes les publications",
    "No posts in archive": "Aucune publication dans les archives",

    # Tags
    "Manage tags": "Gérer les tags",
    "Create tag": "Créer un tag",
    "No tags yet": "Aucun tag pour le moment",
    "Tag name": "Nom du tag",
    "Color": "Couleur",
    "No trending tags": "Aucun tag tendance",

    # Errors
    "Error": "Erreur",
    "Error loading": "Erreur de chargement",
    "Error saving": "Erreur lors de l’enregistrement",
    "Error deleting": "Erreur lors de la suppression",
    "Something went wrong": "Une erreur est survenue",
    "Page not found": "Page introuvable",
    "Server error": "Erreur serveur",
    "Anonymous": "Anonyme",

    # File selection
    "Select file": "Sélectionner un fichier",
    "No file selected": "Aucun fichier sélectionné",

    # Leave group
    "Do you really want to leave this group?": "Voulez-vous vraiment quitter ce groupe ?",

    # Layout styles
    "Grid": "Grille",
    "Masonry": "Mosaïque",
    "Timeline": "Chronologie",

    # Misc
    "Recent posts": "Publications récentes",
    "Popular posts": "Publications populaires",
    "No posts": "Aucune publication",
    "Load more": "Charger plus",
    "Follow": "Suivre",
    "Unfollow": "Ne plus suivre",
    "Followers": "Abonnés",
    "Following": "Abonnements",
    "List": "Liste",
    "Compact": "Compact",
    "Cards": "Cartes",
    "Filter": "Filtrer",
    "Sort": "Trier",
    "Date": "Date",
    "Author": "Auteur",
    "From": "De",
    "To": "À",
    "Apply": "Appliquer",
    "Clear": "Effacer",
    "Today": "Aujourd’hui",
    "Yesterday": "Hier",
    "This week": "Cette semaine",
    "This month": "Ce mois-ci",
    "This year": "Cette année",

    # Confirmations & dialogs
    "Analytics admin is not configured. Please set ANALYTICS_ADMIN_PASSWORD in .env.": "L’administration des statistiques n’est pas configurée. Veuillez définir ANALYTICS_ADMIN_PASSWORD dans .env.",
    "Do you really want to delete this post? This action cannot be undone.": "Voulez-vous vraiment supprimer cette publication ? Cette action est irréversible.",
    "Do you really want to delete the page \"{title}\" and all related posts?": "Voulez-vous vraiment supprimer la page \"{title}\" et toutes les publications associées ?",
    "Do you really want to delete this file?": "Voulez-vous vraiment supprimer ce fichier ?",
    "Do you really want to delete this announcement? This action cannot be undone.": "Voulez-vous vraiment supprimer cette annonce ? Cette action est irréversible.",
    "Do you really want to delete this comment? This action cannot be undone.": "Voulez-vous vraiment supprimer ce commentaire ? Cette action est irréversible.",
    "Do you really want to invite all portal users to this group? This cannot be undone.": "Voulez-vous vraiment inviter tous les utilisateurs du portail dans ce groupe ? Ceci est irréversible.",
    "Do you really want to remove {name} from the group?": "Voulez-vous vraiment retirer {name} du groupe ?",
    "Type the group name <b>{name}</b> to confirm deletion.": "Saisissez le nom du groupe <b>{name}</b> pour confirmer la suppression.",
    "Delete permanently": "Supprimer définitivement",
    "Delete image": "Supprimer l’image",
    "Really delete image?": "Supprimer l’image ?",
    "Please select whether the post should appear on your profile or in a group.": "Veuillez sélectionner si la publication doit apparaître sur votre profil ou dans un groupe.",
    "Remove this image from the selection?": "Retirer cette image de la sélection ?",

    # Post editor UI
    "+ Add poll": "+ Ajouter un sondage",
    "− Hide poll": "− Masquer le sondage",
    "+ Set time": "+ Définir l’heure",
    "− Hide schedule": "− Masquer la programmation",
    "Option 1": "Option 1",
    "Option 2": "Option 2",
    "Option {n}": "Option {n}",
    "bold text": "texte en gras",
    "italic text": "texte en italique",
    "strikethrough": "barré",
    "Heading": "Titre",
    "Quote": "Citation",
    "code": "code",
    "List item": "Élément de liste",
    "Link text": "Texte du lien",
    "code here": "code ici",
    "Error creating.": "Erreur lors de la création.",
    "Error creating tag.": "Erreur lors de la création du tag.",
    "Show in menu": "Afficher dans le menu",
    "Delete tag": "Supprimer le tag",
    "Really delete tag?": "Supprimer le tag ?",
    "No preview available": "Aucun aperçu disponible",
    "Please select a group.": "Veuillez sélectionner un groupe.",

    # Auth validation
    "Registration is disabled.": "L’inscription est désactivée.",
    "Username must be at least 3 characters long.": "Le nom d’utilisateur doit comporter au moins 3 caractères.",
    "Please enter a valid email address.": "Veuillez saisir une adresse e-mail valide.",
    "Password must be at least 12 characters long.": "Le mot de passe doit comporter au moins 12 caractères.",
    "Password must contain at least one uppercase letter.": "Le mot de passe doit contenir au moins une lettre majuscule.",
    "Password must contain at least one lowercase letter.": "Le mot de passe doit contenir au moins une lettre minuscule.",
    "Password must contain at least one number.": "Le mot de passe doit contenir au moins un chiffre.",
    "Password must contain at least one special character.": "Le mot de passe doit contenir au moins un caractère spécial.",
    "Passwords do not match.": "Les mots de passe ne correspondent pas.",
    "Username is already taken.": "Ce nom d’utilisateur est déjà utilisé.",
    "Email address is already registered.": "Cette adresse e-mail est déjà enregistrée.",
    "Registration successful! You can now log in.": "Inscription réussie ! Vous pouvez maintenant vous connecter.",

    # Keycloak
    "Keycloak SSO is not enabled.": "Le SSO Keycloak n’est pas activé.",
    "Error during Keycloak login.": "Erreur lors de la connexion Keycloak.",
    "Keycloak profile is incomplete (missing sub).": "Le profil Keycloak est incomplet (sub manquant).",
    "Keycloak profile has no email address. Please allow email in Keycloak.": "Le profil Keycloak ne contient pas d’adresse e-mail. Veuillez autoriser l’e-mail dans Keycloak.",
    "Keycloak registration was canceled. Please log in again.": "L’inscription Keycloak a été annulée. Veuillez vous reconnecter.",
    "This account is already linked to another login provider.": "Ce compte est déjà lié à un autre fournisseur de connexion.",
    "Username may only contain letters, numbers and _ . -": "Le nom d’utilisateur ne peut contenir que des lettres, des chiffres et _ . -",
    "This Keycloak account is already linked.": "Ce compte Keycloak est déjà lié.",
    "Keycloak registration canceled.": "Inscription Keycloak annulée.",

    # Blog / pages / posts (server messages)
    "Profile updated successfully.": "Profil mis à jour avec succès.",
    "Title is required.": "Le titre est obligatoire.",
    "Page \"{title}\" was created.": "La page \"{title}\" a été créée.",
    "Page updated.": "Page mise à jour.",
    "Page deleted.": "Page supprimée.",
    "Post created.": "Publication créée.",
    "Post updated. {n} new images added.": "Publication mise à jour. {n} nouvelles images ajoutées.",
    "Post updated.": "Publication mise à jour.",
    "Post deleted.": "Publication supprimée.",

    # Notifications
    "{name} reacted with {emoji}": "{name} a réagi avec {emoji}",
    "{name} reacted with {emoji} to your comment": "{name} a réagi avec {emoji} à votre commentaire",
    "{name} commented on your post": "{name} a commenté votre publication",
    "{name} replied to your comment": "{name} a répondu à votre commentaire",
    "{name} mentioned you in a comment": "{name} vous a mentionné dans un commentaire",
    "{name} is now following you": "{name} vous suit maintenant",

    # Tags (server)
    "Tag name is required.": "Le nom du tag est obligatoire.",
    "A tag with this name already exists.": "Un tag portant ce nom existe déjà.",
    "Tag created.": "Tag créé.",
    "Tag deleted.": "Tag supprimé.",

    # Polls (notifications)
    "New vote": "Nouveau vote",
    "{name} voted in your poll": "{name} a voté dans votre sondage",

    # Groups (server)
    "Group name is required.": "Le nom du groupe est obligatoire.",
    "Group \"{name}\" created.": "Groupe \"{name}\" créé.",
    "You are not a member of this group.": "Vous n’êtes pas membre de ce groupe.",
    "Only admins can edit group settings.": "Seuls les administrateurs peuvent modifier les paramètres du groupe.",
    "Group settings saved.": "Paramètres du groupe enregistrés.",
    "Only admins can delete groups.": "Seuls les administrateurs peuvent supprimer des groupes.",
    "Group name does not match. Group was not deleted.": "Le nom du groupe ne correspond pas. Le groupe n’a pas été supprimé.",
    "Group \"{name}\" was deleted.": "Le groupe \"{name}\" a été supprimé.",
    "User not found.": "Utilisateur introuvable.",
    "User is already a member.": "L’utilisateur est déjà membre.",
    "{name} added you to the group \"{group}\"": "{name} vous a ajouté au groupe \"{group}\"",
    "{user} was added to the group.": "{user} a été ajouté au groupe.",
    "Only admins can invite all users.": "Seuls les administrateurs peuvent inviter tous les utilisateurs.",
    "{n} users were added to the group.": "{n} utilisateurs ont été ajoutés au groupe.",
    "You are the only admin. Transfer the admin role before leaving the group.": "Vous êtes le seul administrateur. Transférez le rôle d’administrateur avant de quitter le groupe.",
    "You left the group \"{name}\".": "Vous avez quitté le groupe \"{name}\".",
    "Only admins can remove members.": "Seuls les administrateurs peuvent retirer des membres.",
    "You cannot remove yourself.": "Vous ne pouvez pas vous retirer vous-même.",
    "Member removed.": "Membre retiré.",
    "Only admins can change roles.": "Seuls les administrateurs peuvent modifier les rôles.",
    "You cannot change your own role.": "Vous ne pouvez pas modifier votre propre rôle.",
    "{user} is now a regular member.": "{user} est maintenant un membre.",
    "{user} is now an admin.": "{user} est maintenant administrateur.",

    # Files (server)
    "No file selected.": "Aucun fichier sélectionné.",
    "File type not allowed. Allowed types: {types}": "Type de fichier non autorisé. Types autorisés : {types}",
    "File is too large. Maximum size: 50MB": "Le fichier est trop volumineux. Taille maximale : 50 Mo",
    "File \"{name}\" uploaded successfully.": "Fichier \"{name}\" téléversé avec succès.",
    "You do not have permission to delete this file.": "Vous n’avez pas l’autorisation de supprimer ce fichier.",
    "File deleted.": "Fichier supprimé.",

    # Announcements (server)
    "Only group admins can create announcements.": "Seuls les administrateurs du groupe peuvent créer des annonces.",
    "Please enter content.": "Veuillez saisir le contenu.",
    "Announcement created.": "Annonce créée.",
    "Only group admins can edit announcements.": "Seuls les administrateurs du groupe peuvent modifier les annonces.",
    "Announcement updated.": "Annonce mise à jour.",
    "Only group admins can delete announcements.": "Seuls les administrateurs du groupe peuvent supprimer les annonces.",
    "Announcement deleted.": "Annonce supprimée.",

    # UI labels & pages
    "Language": "Langue",
    "Toggle theme": "Basculer le thème",
    "Back to top": "Retour en haut",
    "Tag": "Tag",
    "Reset": "Réinitialiser",
    "Active filters": "Filtres actifs",
    "Remove all": "Tout retirer",
    "Loading comments...": "Chargement des commentaires...",
    "Trending tags": "Tags tendance",
    "My Groups": "Mes groupes",
    "Quick actions": "Actions rapides",
    "New post": "Nouvelle publication",
    "Edit profile": "Modifier le profil",
    "Overview": "Aperçu",
    "This user has not published any posts yet.": "Cet utilisateur n’a pas encore publié.",
    "No posts on this page": "Aucune publication sur cette page",
    "No posts have been published on this page yet.": "Aucune publication n’a encore été publiée sur cette page.",
    "Back to feed": "Retour au fil",
    "Confirm password": "Confirmer le mot de passe",
    "Are you sure?": "Êtes-vous sûr ?",
    "Unpublished": "Non publié",
    "Statistics": "Statistiques",
    "Back to groups": "Retour aux groupes",
    "Create new group": "Créer un nouveau groupe",
    "Group name": "Nom du groupe",
    "Group settings": "Paramètres du groupe",
    "Cover image": "Image de couverture",
    "Upload cover image": "Téléverser une image de couverture",
    "Change icon": "Changer l’icône",
    "Upload icon": "Téléverser une icône",
    "Save changes": "Enregistrer les modifications",
    "Invite member": "Inviter un membre",
    "Search user...": "Rechercher un utilisateur...",
    "Invite": "Inviter",
    "Invite all portal users": "Inviter tous les utilisateurs du portail",
    "Invites all registered users to this group": "Invite tous les utilisateurs enregistrés dans ce groupe",
    "Remove admin role": "Retirer le rôle d’administrateur",
    "Make admin": "Rendre administrateur",
    "This action deletes the group": "Cette action supprime le groupe",
    "including posts, files and memberships. This cannot be undone.": "y compris les publications, fichiers et adhésions. Ceci est irréversible.",
    "Delete group permanently": "Supprimer définitivement le groupe",
    "All": "Tous",
    "Archive is empty": "Les archives sont vides",
    "Create your first post.": "Créez votre première publication.",
    "No bookmarks": "Aucun favori",
    "Save interesting posts as bookmarks.": "Enregistrez des publications intéressantes en favoris.",
    "edit": "modifier",
    "Bold (Ctrl+B)": "Gras (Ctrl+B)",
    "Italic (Ctrl+I)": "Italique (Ctrl+I)",
    "Strikethrough": "Barré",
    "Code": "Code",
    "Numbered list": "Liste numérotée",
    "Insert link": "Insérer un lien",
    "Markdown is supported: **bold**, *italic*, `code`, > quote, - list. Links are automatically embedded as previews.": "Markdown est pris en charge : **gras**, *italique*, `code`, > citation, - liste. Les liens sont automatiquement intégrés en aperçus.",
    "Where should the post appear?": "Où la publication doit-elle apparaître ?",
    "On my profile": "Sur mon profil",
    "In a group": "Dans un groupe",
    "No page (overview only)": "Aucune page (aperçu uniquement)",
    "Public (everyone can see)": "Public (tout le monde peut voir)",
    "Only group members can see this post.": "Seuls les membres du groupe peuvent voir cette publication.",
    "Search or create tag...": "Rechercher ou créer un tag...",
    "Schedule publication": "Programmer la publication",
    "− Edit schedule": "− Modifier la programmation",
    "The post will only be visible in the feed at the selected time.": "La publication ne sera visible dans le fil qu’à l’heure sélectionnée.",
    "Remove schedule": "Supprimer la programmation",
    "Existing images": "Images existantes",
    "Drag & drop to reorder": "Glisser-déposer pour réordonner",
    "Add new images": "Ajouter de nouvelles images",
    "Select files": "Sélectionner des fichiers",
    "Hidden": "Masqué",
    "No pages yet.": "Aucune page pour le moment.",
    "Title of your post": "Titre de votre publication",
    "What would you like to share?": "Que souhaitez-vous partager ?",
    "Poll": "Sondage",
    "Poll question...": "Question du sondage...",
    "+ Add option": "+ Ajouter une option",
    "Multiple choice": "Choix multiple",
    "Ends": "Se termine",
    "Remove poll": "Supprimer le sondage",
    "Drag images here or click": "Glissez des images ici ou cliquez",
    "PNG, JPG, GIF, WebP allowed": "PNG, JPG, GIF, WebP autorisés",
    "Create a new post for this page.": "Créer une nouvelle publication pour cette page.",
    "Search term": "Terme de recherche",
    "All tags": "Tous les tags",
    "All pages": "Toutes les pages",
    "result": "résultat",
    "results": "résultats",
    "found": "trouvé(s)",
    "Try different search terms or filters.": "Essayez d’autres termes de recherche ou filtres.",
    "Profile settings": "Paramètres du profil",
    "Profile picture": "Photo de profil",
    "Tell something about yourself...": "Dites quelque chose sur vous...",
    "Design & Colors": "Design et couleurs",
    "Accent color": "Couleur d’accent",
    "Background color": "Couleur d’arrière-plan",
    "Enable": "Activer",
    "Font": "Police",
    "Default (Inter)": "Par défaut (Inter)",
    "Serif (Georgia)": "Serif (Georgia)",
    "Monospace": "Monospace",
    "Rounded (Nunito)": "Arrondie (Nunito)",
    "Layout": "Mise en page",
    "Post layout": "Mise en page des publications",
    "Create new tag": "Créer un nouveau tag",
    "Name": "Nom",
    "Existing tags": "Tags existants",
    "No tags created yet.": "Aucun tag n’a encore été créé.",
}


def fill_translations(po_file_path: str) -> int:
    """Fill empty translations in a .po file."""

    def unquote_po(line: str) -> str:
        s = line.strip()
        if not (s.startswith('"') and s.endswith('"')):
            return ''
        inner = s[1:-1]
        # Unescape PO sequences so keys match the human-readable msgid
        inner = inner.replace('\\\\', '\\')
        inner = inner.replace('\\"', '"')
        inner = inner.replace('\\n', '\n')
        inner = inner.replace('\\t', '\t')
        inner = inner.replace('\\r', '\r')
        return inner

    def escape_po(s: str) -> str:
        return s.replace('\\', '\\\\').replace('"', '\\"')

    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    filled_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith('msgid '):
            i += 1
            continue

        msgid_parts = [unquote_po(line[len('msgid '):])]
        i += 1
        while i < len(lines) and lines[i].lstrip().startswith('"'):
            msgid_parts.append(unquote_po(lines[i]))
            i += 1
        msgid = ''.join(msgid_parts)

        if i >= len(lines) or not lines[i].startswith('msgstr '):
            continue

        msgstr_start = i
        msgstr_parts = [unquote_po(lines[i][len('msgstr '):])]
        i += 1
        while i < len(lines) and lines[i].lstrip().startswith('"'):
            msgstr_parts.append(unquote_po(lines[i]))
            i += 1
        msgstr = ''.join(msgstr_parts)

        if msgid and (msgstr.strip() == '') and (msgid in TRANSLATIONS):
            translation = TRANSLATIONS[msgid]
            lines[msgstr_start:i] = [f'msgstr "{escape_po(translation)}"\n']
            i = msgstr_start + 1
            filled_count += 1
            print(f"  ✓ {msgid} -> {translation}")

    with open(po_file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(lines)

    return filled_count


if __name__ == '__main__':
    import sys

    po_file = sys.argv[1] if len(sys.argv) > 1 else 'src/translations/fr/LC_MESSAGES/messages.po'
    print(f"Filling translations in {po_file}...")
    count = fill_translations(po_file)
    print(f"\nFilled {count} translations.\n")

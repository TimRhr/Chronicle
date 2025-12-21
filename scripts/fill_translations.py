#!/usr/bin/env python3
"""Fill German translations for common UI strings."""

# German translations for common UI strings
TRANSLATIONS = {
    # Auth & Login
    "Invalid credentials.": "Ungültige Anmeldedaten.",
    "You have been logged out.": "Du wurdest abgemeldet.",
    "Please log in to view this page.": "Bitte melde dich an, um diese Seite zu sehen.",
    "Login": "Anmelden",
    "Logout": "Abmelden",
    "Register": "Registrieren",
    "Email": "E-Mail",
    "Password": "Passwort",
    "Username": "Benutzername",
    "Remember me": "Angemeldet bleiben",
    "Forgot password?": "Passwort vergessen?",
    "Don't have an account?": "Noch kein Konto?",
    "Already have an account?": "Bereits ein Konto?",
    "Create account": "Konto erstellen",
    "Sign in with Keycloak": "Mit Keycloak anmelden",
    "or": "oder",
    
    # Navigation & UI
    "Loading...": "Lädt...",
    "No notifications": "Keine Benachrichtigungen",
    "Mark all as read": "Alle als gelesen markieren",
    "Notifications": "Benachrichtigungen",
    "Show more": "Mehr anzeigen",
    "Show less": "Weniger anzeigen",
    "more": "mehr",
    "Feed": "Feed",
    "Search": "Suchen",
    "Settings": "Einstellungen",
    "My Profile": "Mein Profil",
    "Close": "Schließen",
    "Cancel": "Abbrechen",
    "Save": "Speichern",
    "Delete": "Löschen",
    "Edit": "Bearbeiten",
    "Confirm": "Bestätigen",
    "Back": "Zurück",
    "Next": "Weiter",
    "Previous": "Zurück",
    "Yes": "Ja",
    "No": "Nein",
    "OK": "OK",
    "Try again": "Erneut versuchen",

    "Analytics admin is not configured. Please set ANALYTICS_ADMIN_PASSWORD in .env.": "Analytics-Admin ist nicht konfiguriert. Bitte setze ANALYTICS_ADMIN_PASSWORD in .env.",
    "Do you really want to delete this post? This action cannot be undone.": "Möchtest du diesen Beitrag wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.",
    "Do you really want to delete the page \"{title}\" and all related posts?": "Möchtest du die Seite \"{title}\" und alle zugehörigen Beiträge wirklich löschen?",
    "Do you really want to delete this file?": "Möchtest du diese Datei wirklich löschen?",
    "Do you really want to delete this announcement? This action cannot be undone.": "Möchtest du diese Ankündigung wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.",
    "Do you really want to delete this comment? This action cannot be undone.": "Möchtest du diesen Kommentar wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.",
    "Do you really want to invite all portal users to this group? This cannot be undone.": "Möchtest du wirklich alle Portalbenutzer in diese Gruppe einladen? Dies kann nicht rückgängig gemacht werden.",
    "Do you really want to remove {name} from the group?": "Möchtest du {name} wirklich aus der Gruppe entfernen?",
    "Type the group name <b>{name}</b> to confirm deletion.": "Gib den Gruppennamen <b>{name}</b> ein, um das Löschen zu bestätigen.",
    "Delete permanently": "Endgültig löschen",
    "Delete image": "Bild löschen",
    "Really delete image?": "Bild wirklich löschen?",
    "Please select whether the post should appear on your profile or in a group.": "Bitte wähle aus, ob der Beitrag auf deinem Profil oder in einer Gruppe erscheinen soll.",
    "Remove this image from the selection?": "Dieses Bild aus der Auswahl entfernen?",
    "+ Add poll": "+ Umfrage hinzufügen",
    "− Hide poll": "− Umfrage ausblenden",
    "+ Set time": "+ Zeit festlegen",
    "− Hide schedule": "− Zeitplan ausblenden",
    "Option 1": "Option 1",
    "Option 2": "Option 2",
    "Option {n}": "Option {n}",
    "bold text": "fetter Text",
    "italic text": "kursiver Text",
    "strikethrough": "durchgestrichen",
    "Heading": "Überschrift",
    "Quote": "Zitat",
    "code": "Code",
    "List item": "Listeneintrag",
    "Link text": "Linktext",
    "code here": "Code hier",
    "Error creating.": "Fehler beim Erstellen.",
    "Error creating tag.": "Fehler beim Erstellen des Tags.",
    "Show in menu": "Im Menü anzeigen",
    "Delete tag": "Tag löschen",
    "Really delete tag?": "Tag wirklich löschen?",
    "No preview available": "Keine Vorschau verfügbar",
    "Please select a group.": "Bitte wähle eine Gruppe aus.",
    "Registration is disabled.": "Registrierung ist deaktiviert.",
    "Username must be at least 3 characters long.": "Benutzername muss mindestens 3 Zeichen lang sein.",
    "Please enter a valid email address.": "Bitte gib eine gültige E-Mail-Adresse ein.",
    "Password must be at least 12 characters long.": "Passwort muss mindestens 12 Zeichen lang sein.",
    "Password must contain at least one uppercase letter.": "Passwort muss mindestens einen Großbuchstaben enthalten.",
    "Password must contain at least one lowercase letter.": "Passwort muss mindestens einen Kleinbuchstaben enthalten.",
    "Password must contain at least one number.": "Passwort muss mindestens eine Zahl enthalten.",
    "Password must contain at least one special character.": "Passwort muss mindestens ein Sonderzeichen enthalten.",
    "Passwords do not match.": "Passwörter stimmen nicht überein.",
    "Username is already taken.": "Benutzername ist bereits vergeben.",
    "Email address is already registered.": "E-Mail-Adresse ist bereits registriert.",
    "Registration successful! You can now log in.": "Registrierung erfolgreich! Du kannst dich jetzt anmelden.",
    "Keycloak SSO is not enabled.": "Keycloak-SSO ist nicht aktiviert.",
    "Error during Keycloak login.": "Fehler beim Keycloak-Login.",
    "Keycloak profile is incomplete (missing sub).": "Keycloak-Profil ist unvollständig (sub fehlt).",
    "Keycloak profile has no email address. Please allow email in Keycloak.": "Keycloak-Profil hat keine E-Mail-Adresse. Bitte erlaube E-Mail in Keycloak.",
    "Keycloak registration was canceled. Please log in again.": "Keycloak-Registrierung wurde abgebrochen. Bitte melde dich erneut an.",
    "This account is already linked to another login provider.": "Dieses Konto ist bereits mit einem anderen Login-Anbieter verknüpft.",
    "Username may only contain letters, numbers and _ . -": "Benutzername darf nur Buchstaben, Zahlen und _ . - enthalten",
    "This Keycloak account is already linked.": "Dieses Keycloak-Konto ist bereits verknüpft.",
    "Keycloak registration canceled.": "Keycloak-Registrierung abgebrochen.",
    "Profile updated successfully.": "Profil erfolgreich aktualisiert.",
    "Title is required.": "Titel ist erforderlich.",
    "Page \"{title}\" was created.": "Seite \"{title}\" wurde erstellt.",
    "Page updated.": "Seite aktualisiert.",
    "Page deleted.": "Seite gelöscht.",
    "Post created.": "Beitrag erstellt.",
    "Post updated. {n} new images added.": "Beitrag aktualisiert. {n} neue Bilder hinzugefügt.",
    "Post updated.": "Beitrag aktualisiert.",
    "Post deleted.": "Beitrag gelöscht.",
    "{name} reacted with {emoji}": "{name} reagierte mit {emoji}",
    "{name} reacted with {emoji} to your comment": "{name} reagierte mit {emoji} auf deinen Kommentar",
    "{name} commented on your post": "{name} kommentierte deinen Beitrag",
    "{name} replied to your comment": "{name} antwortete auf deinen Kommentar",
    "{name} mentioned you in a comment": "{name} erwähnte dich in einem Kommentar",
    "Tag name is required.": "Tag-Name ist erforderlich.",
    "A tag with this name already exists.": "Ein Tag mit diesem Namen existiert bereits.",
    "Tag created.": "Tag erstellt.",
    "Tag deleted.": "Tag gelöscht.",
    "{name} is now following you": "{name} folgt dir jetzt",
    "New vote": "Neue Stimme",
    "{name} voted in your poll": "{name} hat in deiner Umfrage abgestimmt",
    "Group name is required.": "Gruppenname ist erforderlich.",
    "Group \"{name}\" created.": "Gruppe \"{name}\" erstellt.",
    "You are not a member of this group.": "Du bist kein Mitglied dieser Gruppe.",
    "Only admins can edit group settings.": "Nur Admins können die Gruppeneinstellungen bearbeiten.",
    "Group settings saved.": "Gruppeneinstellungen gespeichert.",
    "Only admins can delete groups.": "Nur Admins können Gruppen löschen.",
    "Group name does not match. Group was not deleted.": "Gruppenname stimmt nicht überein. Gruppe wurde nicht gelöscht.",
    "Group \"{name}\" was deleted.": "Gruppe \"{name}\" wurde gelöscht.",
    "User not found.": "Benutzer nicht gefunden.",
    "User is already a member.": "Benutzer ist bereits Mitglied.",
    "{name} added you to the group \"{group}\"": "{name} hat dich zur Gruppe \"{group}\" hinzugefügt",
    "{user} was added to the group.": "{user} wurde zur Gruppe hinzugefügt.",
    "Only admins can invite all users.": "Nur Admins können alle Benutzer einladen.",
    "{n} users were added to the group.": "{n} Benutzer wurden zur Gruppe hinzugefügt.",
    "You are the only admin. Transfer the admin role before leaving the group.": "Du bist der einzige Admin. Übertrage die Adminrolle, bevor du die Gruppe verlässt.",
    "You left the group \"{name}\".": "Du hast die Gruppe \"{name}\" verlassen.",
    "Only admins can remove members.": "Nur Admins können Mitglieder entfernen.",
    "You cannot remove yourself.": "Du kannst dich nicht selbst entfernen.",
    "Member removed.": "Mitglied entfernt.",
    "Only admins can change roles.": "Nur Admins können Rollen ändern.",
    "You cannot change your own role.": "Du kannst deine eigene Rolle nicht ändern.",
    "{user} is now a regular member.": "{user} ist jetzt ein normales Mitglied.",
    "{user} is now an admin.": "{user} ist jetzt Admin.",
    "No file selected.": "Keine Datei ausgewählt.",
    "File type not allowed. Allowed types: {types}": "Dateityp nicht erlaubt. Erlaubte Typen: {types}",
    "File is too large. Maximum size: 50MB": "Datei ist zu groß. Maximale Größe: 50MB",
    "File \"{name}\" uploaded successfully.": "Datei \"{name}\" erfolgreich hochgeladen.",
    "You do not have permission to delete this file.": "Du hast keine Berechtigung, diese Datei zu löschen.",
    "File deleted.": "Datei gelöscht.",
    "Only group admins can create announcements.": "Nur Gruppen-Admins können Ankündigungen erstellen.",
    "Please enter content.": "Bitte gib Inhalt ein.",
    "Announcement created.": "Ankündigung erstellt.",
    "Only group admins can edit announcements.": "Nur Gruppen-Admins können Ankündigungen bearbeiten.",
    "Announcement updated.": "Ankündigung aktualisiert.",
    "Only group admins can delete announcements.": "Nur Gruppen-Admins können Ankündigungen löschen.",
    "Announcement deleted.": "Ankündigung gelöscht.",
    "Language": "Sprache",
    "Toggle theme": "Theme umschalten",
    "Back to top": "Nach oben",
    "Tag": "Tag",
    "Reset": "Zurücksetzen",
    "Active filters": "Aktive Filter",
    "Remove all": "Alle entfernen",
    "Loading comments...": "Kommentare werden geladen...",
    "Trending tags": "Beliebte Tags",
    "My Groups": "Meine Gruppen",
    "Quick actions": "Schnellaktionen",
    "New post": "Neuer Beitrag",
    "Edit profile": "Profil bearbeiten",
    "Overview": "Übersicht",
    "This user has not published any posts yet.": "Dieser Benutzer hat noch keine Beiträge veröffentlicht.",
    "No posts on this page": "Keine Beiträge auf dieser Seite",
    "No posts have been published on this page yet.": "Auf dieser Seite wurden noch keine Beiträge veröffentlicht.",
    "Back to feed": "Zurück zum Feed",
    "Confirm password": "Passwort bestätigen",
    "Are you sure?": "Bist du sicher?",
    "Unpublished": "Unveröffentlicht",
    "Statistics": "Statistiken",
    "Back to groups": "Zurück zu den Gruppen",
    "Create new group": "Neue Gruppe erstellen",
    "Group name": "Gruppenname",
    "Group settings": "Gruppeneinstellungen",
    "Cover image": "Titelbild",
    "Upload cover image": "Titelbild hochladen",
    "Change icon": "Icon ändern",
    "Upload icon": "Icon hochladen",
    "Save changes": "Änderungen speichern",
    "Invite member": "Mitglied einladen",
    "Search user...": "Benutzer suchen...",
    "Invite": "Einladen",
    "Invite all portal users": "Alle Portalbenutzer einladen",
    "Invites all registered users to this group": "Lädt alle registrierten Benutzer in diese Gruppe ein",
    "Remove admin role": "Adminrolle entfernen",
    "Make admin": "Zum Admin machen",
    "This action deletes the group": "Diese Aktion löscht die Gruppe",
    "including posts, files and memberships. This cannot be undone.": "einschließlich Beiträgen, Dateien und Mitgliedschaften. Dies kann nicht rückgängig gemacht werden.",
    "Delete group permanently": "Gruppe endgültig löschen",
    "All": "Alle",
    "Archive is empty": "Archiv ist leer",
    "Create your first post.": "Erstelle deinen ersten Beitrag.",
    "No bookmarks": "Keine Lesezeichen",
    "Save interesting posts as bookmarks.": "Speichere interessante Beiträge als Lesezeichen.",
    "edit": "bearbeiten",
    "Bold (Ctrl+B)": "Fett (Strg+B)",
    "Italic (Ctrl+I)": "Kursiv (Strg+I)",
    "Strikethrough": "Durchgestrichen",
    "Code": "Code",
    "Numbered list": "Nummerierte Liste",
    "Insert link": "Link einfügen",
    "Markdown is supported: **bold**, *italic*, `code`, > quote, - list. Links are automatically embedded as previews.": "Markdown wird unterstützt: **fett**, *kursiv*, `code`, > Zitat, - Liste. Links werden automatisch als Vorschau eingebettet.",
    "Where should the post appear?": "Wo soll der Beitrag erscheinen?",
    "On my profile": "Auf meinem Profil",
    "In a group": "In einer Gruppe",
    "No page (overview only)": "Keine Seite (nur Übersicht)",
    "Public (everyone can see)": "Öffentlich (jeder kann es sehen)",
    "Only group members can see this post.": "Nur Gruppenmitglieder können diesen Beitrag sehen.",
    "Search or create tag...": "Tag suchen oder erstellen...",
    "Schedule publication": "Veröffentlichung planen",
    "− Edit schedule": "− Zeitplan bearbeiten",
    "The post will only be visible in the feed at the selected time.": "Der Beitrag wird erst zur ausgewählten Zeit im Feed sichtbar.",
    "Remove schedule": "Zeitplan entfernen",
    "Existing images": "Vorhandene Bilder",
    "Drag & drop to reorder": "Zum Sortieren ziehen",
    "Add new images": "Neue Bilder hinzufügen",
    "Select files": "Dateien auswählen",
    "Hidden": "Ausgeblendet",
    "No pages yet.": "Noch keine Seiten.",
    "Title of your post": "Titel deines Beitrags",
    "What would you like to share?": "Was möchtest du teilen?",
    "Poll": "Umfrage",
    "Poll question...": "Umfragefrage...",
    "+ Add option": "+ Option hinzufügen",
    "Multiple choice": "Mehrfachauswahl",
    "Ends": "Endet",
    "Remove poll": "Umfrage entfernen",
    "Drag images here or click": "Bilder hierher ziehen oder klicken",
    "PNG, JPG, GIF, WebP allowed": "PNG, JPG, GIF, WebP erlaubt",
    "Create a new post for this page.": "Erstelle einen neuen Beitrag für diese Seite.",
    "Search term": "Suchbegriff",
    "All tags": "Alle Tags",
    "All pages": "Alle Seiten",
    "result": "Ergebnis",
    "results": "Ergebnisse",
    "found": "gefunden",
    "Try different search terms or filters.": "Versuche andere Suchbegriffe oder Filter.",
    "Profile settings": "Profileinstellungen",
    "Profile picture": "Profilbild",
    "Tell something about yourself...": "Erzähl etwas über dich...",
    "Design & Colors": "Design & Farben",
    "Accent color": "Akzentfarbe",
    "Background color": "Hintergrundfarbe",
    "Enable": "Aktivieren",
    "Font": "Schrift",
    "Default (Inter)": "Standard (Inter)",
    "Serif (Georgia)": "Serif (Georgia)",
    "Monospace": "Monospace",
    "Rounded (Nunito)": "Rund (Nunito)",
    "Layout": "Layout",
    "Post layout": "Beitragslayout",
    "Create new tag": "Neuen Tag erstellen",
    "Name": "Name",
    "Existing tags": "Vorhandene Tags",
    "No tags created yet.": "Noch keine Tags erstellt.",
    
    # Posts
    "New Post": "Neuer Beitrag",
    "Create post": "Beitrag erstellen",
    "Edit post": "Beitrag bearbeiten",
    "Delete post": "Beitrag löschen",
    "Post": "Beitrag",
    "Posts": "Beiträge",
    "No posts yet": "Noch keine Beiträge",
    "No posts found": "Keine Beiträge gefunden",
    "No more posts": "Keine weiteren Beiträge",
    "Create first post": "Ersten Beitrag erstellen",
    "No posts have been published yet.": "Es wurden noch keine Beiträge veröffentlicht.",
    "No posts match the selected filters.": "Keine Beiträge entsprechen den gewählten Filtern.",
    "Reset filters": "Filter zurücksetzen",
    "edited": "bearbeitet",
    "Title": "Titel",
    "Content": "Inhalt",
    "Tags": "Tags",
    "Publish": "Veröffentlichen",
    "Draft": "Entwurf",
    "Published": "Veröffentlicht",
    "Scheduled": "Geplant",
    "Schedule post": "Beitrag planen",
    "Image": "Bild",
    "Images": "Bilder",
    "Upload image": "Bild hochladen",
    "Remove image": "Bild entfernen",
    
    # Comments
    "Comments": "Kommentare",
    "Write a comment...": "Kommentar schreiben...",
    "Send": "Senden",
    "Reply": "Antworten",
    "No comments yet.": "Noch keine Kommentare.",
    "Delete comment": "Kommentar löschen",
    "older comments": "ältere Kommentare",
    "Show replies": "Antworten anzeigen",
    "Hide replies": "Antworten ausblenden",
    "reply": "Antwort",
    "replies": "Antworten",
    
    # Reactions & Interactions
    "Bookmark": "Lesezeichen",
    "Bookmarked": "Gespeichert",
    "Bookmarks": "Lesezeichen",
    "React": "Reagieren",
    "Click to change": "Klicken zum Ändern",
    "Remove reaction": "Reaktion entfernen",
    "Please log in to react.": "Bitte melde dich an, um zu reagieren.",
    "to comment.": "um zu kommentieren.",
    
    # Groups
    "Groups": "Gruppen",
    "Group": "Gruppe",
    "Create group": "Gruppe erstellen",
    "New group": "Neue Gruppe",
    "All groups": "Alle Gruppen",
    "View all groups": "Alle Gruppen anzeigen",
    "No groups yet": "Noch keine Gruppen",
    "You are not in any group yet.": "Du bist noch in keiner Gruppe.",
    "Create a group to share private posts with others.": "Erstelle eine Gruppe, um private Beiträge mit anderen zu teilen.",
    "Members": "Mitglieder",
    "Leave": "Verlassen",
    "Back to group": "Zurück zur Gruppe",
    "Group color": "Gruppenfarbe",
    "Group icon": "Gruppen-Icon",
    "Description": "Beschreibung",
    "What is this group about?": "Worum geht es in dieser Gruppe?",
    "Share the first post in this group.": "Teile den ersten Beitrag in dieser Gruppe.",
    "Invite all": "Alle einladen",
    "Remove member": "Mitglied entfernen",
    "Remove": "Entfernen",
    "Delete group": "Gruppe löschen",
    "No users found": "Keine Benutzer gefunden",
    
    # Files
    "Files": "Dateien",
    "Upload file": "Datei hochladen",
    "Upload": "Hochladen",
    "Download": "Herunterladen",
    "Delete file": "Datei löschen",
    "No files yet": "Noch keine Dateien",
    "Upload the first file to share it with the group.": "Lade die erste Datei hoch, um sie mit der Gruppe zu teilen.",
    "Drag file here or": "Datei hierher ziehen oder",
    "click to select": "klicken zum Auswählen",
    "Max. 50MB · Allowed:": "Max. 50MB · Erlaubt:",
    "Short description of the file...": "Kurze Beschreibung der Datei...",
    "View": "Ansehen",
    
    # Announcements
    "Announcement": "Ankündigung",
    "New announcement": "Neue Ankündigung",
    "Edit announcement": "Ankündigung bearbeiten",
    "Create announcement": "Ankündigung erstellen",
    "Delete announcement": "Ankündigung löschen",
    "Write your announcement... (Markdown is supported)": "Schreibe deine Ankündigung... (Markdown wird unterstützt)",
    "Markdown is supported: **bold**, *italic*, [links](url), lists, etc.": "Markdown wird unterstützt: **fett**, *kursiv*, [Links](url), Listen, etc.",
    "Border color": "Rahmenfarbe",
    "Preview": "Vorschau",
    "Preview appears here...": "Vorschau erscheint hier...",
    "Create": "Erstellen",
    
    # Pages
    "Pages": "Seiten",
    "Page": "Seite",
    "Manage pages": "Seiten verwalten",
    "Create page": "Seite erstellen",
    "Edit page": "Seite bearbeiten",
    "Delete page": "Seite löschen",
    "No pages yet": "Noch keine Seiten",
    "Page title": "Seitentitel",
    "Show in navigation": "In Navigation anzeigen",
    
    # Profile & Settings
    "Profile": "Profil",
    "About me": "Über mich",
    "Bio": "Bio",
    "Display name": "Anzeigename",
    "Theme color": "Themenfarbe",
    "Text color": "Textfarbe",
    "Font Family": "Schriftart",
    "optional": "optional",
    "Enable comments": "Kommentare aktivieren",
    "Enable reactions": "Reaktionen aktivieren",
    "Organization": "Organisation",
    
    # Search
    "Search posts...": "Beiträge suchen...",
    "Search users...": "Benutzer suchen...",
    "No results": "Keine Ergebnisse",
    "No results found": "Keine Ergebnisse gefunden",
    
    # Archive
    "Archive": "Archiv",
    "All Posts": "Alle Beiträge",
    "No posts in archive": "Keine Beiträge im Archiv",
    
    # Tags
    "Manage tags": "Tags verwalten",
    "Create tag": "Tag erstellen",
    "No tags yet": "Noch keine Tags",
    "Tag name": "Tag-Name",
    "Color": "Farbe",
    "No trending tags": "Keine beliebten Tags",
    
    # Errors
    "Error": "Fehler",
    "Error loading": "Fehler beim Laden",
    "Error saving": "Fehler beim Speichern",
    "Error deleting": "Fehler beim Löschen",
    "Something went wrong": "Etwas ist schiefgelaufen",
    "Page not found": "Seite nicht gefunden",
    "Server error": "Serverfehler",
    "Anonymous": "Anonym",
    
    # File selection
    "Select file": "Datei auswählen",
    "No file selected": "Keine Datei ausgewählt",
    
    # Leave group
    "Leave": "Verlassen",
    "Do you really want to leave this group?": "Möchtest du diese Gruppe wirklich verlassen?",
    
    # Layout styles
    "Grid": "Raster",
    "Masonry": "Masonry",
    "Timeline": "Zeitleiste",
    
    # Misc
    "Recent posts": "Neueste Beiträge",
    "Popular posts": "Beliebte Beiträge",
    "No posts": "Keine Beiträge",
    "Load more": "Mehr laden",
    "Follow": "Folgen",
    "Unfollow": "Entfolgen",
    "Followers": "Follower",
    "Following": "Folge ich",
    "List": "Liste",
    "Compact": "Kompakt",
    "Cards": "Karten",
    "Filter": "Filter",
    "Sort": "Sortieren",
    "Date": "Datum",
    "Author": "Autor",
    "From": "Von",
    "To": "Bis",
    "Apply": "Anwenden",
    "Clear": "Löschen",
    "Today": "Heute",
    "Yesterday": "Gestern",
    "This week": "Diese Woche",
    "This month": "Dieser Monat",
    "This year": "Dieses Jahr",
}

def fill_translations(po_file_path):
    """Fill empty translations in a .po file."""
    def unquote_po(line: str) -> str:
        s = line.strip()
        if not (s.startswith('"') and s.endswith('"')):
            return ''
        inner = s[1:-1]
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
    
    po_file = sys.argv[1] if len(sys.argv) > 1 else 'src/translations/de/LC_MESSAGES/messages.po'
    print(f"Filling translations in {po_file}...")
    count = fill_translations(po_file)
    print(f"\nFilled {count} translations.")

def make_tool(name, description, properties, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False
            }
        }
    }
def string_prop(description):
    return {"type": "string", "description": description}
def integer_prop(description):
    return {"type": "integer", "description": description}
tools = [
    make_tool(
        "get_current_datetime",
        "Retourne la date, l'heure locale actuelle du PC et son fuseau horaire. "
        "Fonctionne hors ligne. À utiliser pour toute question sur la date ou l'heure actuelle.",
        {}, []
    ),
    make_tool(
        "calculate",
        "Évalue une expression mathématique de manière sécurisée, sans exécuter de code. "
        "Accepte +, -, *, /, //, %, **, ^, les parenthèses, pi, e et des fonctions "
        "comme sqrt, sin, cos, tan, log, log10, exp, abs, round, ceil et floor. "
        "Fonctionne hors ligne.",
        {"expression": string_prop("Expression mathématique à évaluer.")},
        ["expression"]
    ),
    make_tool(
        "web_search",
        "Recherche des informations sur Internet avec DuckDuckGo. "
        "N'est utilisable que si le PC dispose d'une connexion Internet active. "
        "Retourne des titres, URL et extraits. Ne pas inventer de résultats.",
        {
            "query": string_prop("Sujet ou question à rechercher sur le web."),
            "max_results": {
                "type": "integer",
                "description": "Nombre maximal de résultats, entre 1 et 10."
            }
        },
        ["query"]
    ),
    make_tool("list_python_packages", "Liste les bibliothèques Python installées et les modules importables dans l’environnement de JARVIS. À utiliser avant de choisir une bibliothèque.", {}, []),
    make_tool("read_cadquery_guide", "Lit le guide CadQuery fourni avec Jarvis (Docs/cadquery.md). À consulter pour les opérations, sélecteurs et contraintes des scripts 3D.", {}, []),
    make_tool("run_python", "Exécute du Python dans un processus séparé. Tous les modules standard et packages installés dans l’environnement Python de JARVIS sont importables. Écritures limitées au workspace ; réseau, processus externes et suppressions bloqués ; 30 s maximum. Ce n’est pas une sandbox inviolable.", {"code":string_prop("Code Python complet."),"timeout":{"type":"integer","description":"Délai de 1 à 30 secondes."}},["code"]),
    make_tool("list_managed_files", "Liste workspace/, documents/, downloads/, desktop/ ou un shared_N autorisé.", {"location":string_prop("Dossier, par exemple documents/ ou workspace/")},["location"]),
    make_tool("read_managed_file", "Lit un fichier d'un dossier autorisé.", {"location":string_prop("Chemin alias/relatif.")},["location"]),
    make_tool("write_managed_file", "Crée un fichier dans un dossier autorisé sans écraser l'existant.", {"location":string_prop("Chemin alias/relatif."),"content":string_prop("Contenu texte.")},["location","content"]),
    make_tool("backup_config", "Sauvegarde un fichier autorisé vers Jarvis_Workspace/backups.", {"location":string_prop("Chemin source alias/relatif."),"backup_name":string_prop("Nom facultatif.")},["location"]),
    make_tool("restore_config", "Restaure une sauvegarde sans écraser une destination existante. Demander l'accord utilisateur.", {"backup_name":string_prop("Nom dans backups/."),"destination":string_prop("Destination alias/relative.")},["backup_name","destination"]),
    make_tool("knowledge_save", "Enregistre une connaissance persistante. Ne jamais stocker de secrets.", {"title":string_prop("Titre."),"content":string_prop("Information à conserver."),"tags":string_prop("Mots-clés.")},["title","content"]),
    make_tool("knowledge_search", "Recherche dans la base persistante.", {"query":string_prop("Sujet à retrouver."),"limit":{"type":"integer","description":"1 à 20 résultats."}},["query"]),
    make_tool("knowledge_list", "Liste les connaissances persistantes.", {"limit":{"type":"integer","description":"1 à 100 résultats."}},[]),
    make_tool("plot_chart", "Affiche un graphique natif dans la conversation.", {"title":string_prop("Titre."),"x_values":{"type":"array","items":{"type":"string"},"description":"Libellés X."},"y_values":{"type":"array","items":{"type":"number"},"description":"Valeurs Y."},"chart_type":{"type":"string","enum":["line","bar"]},"x_label":string_prop("Axe X."),"y_label":string_prop("Axe Y.")},["title","x_values","y_values"]),
    make_tool(
        "create_3d_model",
        "Crée une pièce mécanique 3D avec CadQuery et l'affiche dans la conversation. "
        "`cq` est déjà importé ; toutes les dimensions sont en mm. Repères rapides : "
        "`cq.Workplane('XY').box(x, y, z)`, `.rect(x, y).extrude(h)`, "
        "`.circle(r).extrude(h)`, `.faces('>Z').workplane().hole(d)`, "
        "`.edges('|Z').fillet(r)` ou `.chamfer(d)`, `.union(other)` et `.cut(other)`. "
        "Exemple : `model = cq.Workplane('XY').box(40, 30, 8).faces('>Z').workplane().hole(5)`. "
        "Fournis un script autonome qui définit `model` comme un cq.Workplane ou cq.Shape. "
        "Jarvis exporte automatiquement en STL ; ne crée pas toi-même le fichier STL.",
        {
            "title": string_prop("Nom descriptif du modèle."),
            "filename": string_prop("Nom de fichier simple, sans extension ni chemin."),
            "code": string_prop("Script CadQuery complet définissant la variable model.")
        },
        ["title", "code"]
    ),
    make_tool(
        "capture_screen",
        "Capture l'écran et transmet une image avec une grille de coordonnées "
        "tous les 100 pixels. Retourne les dimensions exactes de l'image. "
        "Utilise cette capture pour repérer les éléments et calculer les clics.",
        {}, []
    ),
    make_tool(
        "create_file",
        "Crée un nouveau fichier dans Jarvis_Workspace.",
        {
            "filename": string_prop("Chemin relatif au workspace."),
            "content": string_prop("Contenu initial du fichier.")
        },
        ["filename", "content"]
    ),
    make_tool(
        "create_folder",
        "Crée un dossier dans Jarvis_Workspace.",
        {"foldername": string_prop("Chemin relatif du dossier.")},
        ["foldername"]
    ),
    make_tool(
        "write_file",
        "Remplace le contenu d'un fichier existant dans le workspace.",
        {
            "filename": string_prop("Chemin relatif du fichier."),
            "content": string_prop("Nouveau contenu complet.")
        },
        ["filename", "content"]
    ),
    make_tool(
        "read_file",
        "Lit un fichier du workspace.",
        {"filename": string_prop("Chemin relatif du fichier.")},
        ["filename"]
    ),
    make_tool(
        "open_file",
        "Ouvre un fichier existant du workspace avec son application par défaut.",
        {"filename": string_prop("Chemin relatif du fichier.")},
        ["filename"]
    ),
    make_tool("open_workspace", "Ouvre Jarvis_Workspace dans l'explorateur.", {}, []),
    # make_tool(
    #     "list_installed_apps",
    #     "Liste les applications disponibles dans le menu Démarrer de Windows.",
    #     {}, []
    # ),
    make_tool(
        "get_open_windows",
        "Liste les fenêtres visibles ouvertes, avec leur titre, processus et identifiant.",
        {}, []
    ),
    make_tool(
        "open_app",
        "Ouvre une application installée et disponible dans le menu Démarrer. "
        "Fournis son nom exact ou une partie non ambiguë de son nom.",
        {"app": string_prop("Nom de l'application tel qu'il apparaît dans le menu Démarrer.")},
        ["app"]
    ),
    make_tool(
        "move_mouse",
        "Déplace la souris vers une coordonnée de la dernière capture. "
        "La durée est exprimée en secondes.",
        {
            "x": integer_prop("Coordonnée horizontale."),
            "y": integer_prop("Coordonnée verticale."),
            "duration": {
                "type": "number",
                "description": "Durée du déplacement en secondes, entre 0 et 10."
            }
        },
        ["x", "y"]
    ),

    make_tool(
        "click_mouse",
        "Effectue un ou plusieurs clics à une position de la dernière capture.",
        {
            "x": integer_prop("Coordonnée horizontale."),
            "y": integer_prop("Coordonnée verticale."),
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"]
            },
            "clicks": {
                "type": "integer",
                "description": "Nombre de clics, de 1 à 3."
            }
        },
        ["x", "y"]
    ),

    make_tool(
        "mouse_down",
        "Maintient un bouton de souris enfoncé. Peut recevoir une position.",
        {
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"]
            },
            "x": integer_prop("Position horizontale facultative."),
            "y": integer_prop("Position verticale facultative.")
        },
        []
    ),

    make_tool(
        "mouse_up",
        "Relâche un bouton de souris précédemment maintenu.",
        {
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"]
            }
        },
        []
    ),

    make_tool(
        "drag_mouse",
        "Maintient un bouton de souris et déplace le curseur entre deux "
        "coordonnées de la dernière capture. Idéal pour dessiner ou glisser-déposer.",
        {
            "start_x": integer_prop("Position horizontale de départ."),
            "start_y": integer_prop("Position verticale de départ."),
            "end_x": integer_prop("Position horizontale d'arrivée."),
            "end_y": integer_prop("Position verticale d'arrivée."),
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"]
            },
            "duration": {
                "type": "number",
                "description": "Durée du glissement en secondes."
            }
        },
        ["start_x", "start_y", "end_x", "end_y"]
    ),
    make_tool(
        "scroll_mouse",
        "Fait défiler la fenêtre active. Valeur entière de -10 à 10.",
        {"amount": integer_prop("Nombre de crans, entre -10 et 10.")},
        ["amount"]
    ),
    make_tool(
        "type_text",
        "Saisit du texte dans la fenêtre active. Demander confirmation avant usage.",
        {"text": string_prop("Texte exact à saisir.")},
        ["text"]
    ),
    make_tool(
        "press_key",
        "Appuie sur une touche autorisée. Demander confirmation avant usage.",
        {"key": string_prop("Nom de la touche autorisée.")},
        ["key"]
    ),
    make_tool(
        "hotkey",
        "Exécute un raccourci autorisé. Demander confirmation avant usage.",
        {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Touches du raccourci, dans l'ordre."
            }
        },
        ["keys"]
    ),
    make_tool(
        "notify_user",
        "Envoie une notification native Windows à l'utilisateur. "
        "À utiliser lorsque la tâche est terminée ou lorsqu'une "
        "intervention de l'utilisateur est nécessaire.",
        {
            "title": string_prop("Titre de la notification."),
            "message": string_prop("Contenu de la notification.")
        },
        ["title", "message"]
    )
]

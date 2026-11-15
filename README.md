# 🤖 Jarvis - Assistant IA Scientifique et Technique

<div align="center">

**Assistant d'intelligence artificielle local autonome pour Windows**
*Développé avec Python • Fonctionne hors ligne • Respectueux de la vie privée*

</div>

---

## 📋 À Propos

Jarvis est un assistant IA **local et autonome** conçu pour assister les scientifiques, ingénieurs et développeurs dans leurs projets techniques. Contrairement aux assistants cloud, Jarvis fonctionne **complètement hors ligne**, garantissant une confidentialité totale et une indépendance réseau.

### 🎯 Mission Principale
Fournir une assistance experte dans les domaines de l'électronique, de la programmation, des mathématiques, de la physique et de l'ingénierie mécanique, tout en respectant scrupuleusement les principes de sécurité et d'éthique.

---

## 🚀 Compétences Principales

### 💻 Programmation & Développement
- **Python** : Scripts automatisés, analyse de données, IA/ML
- **Kotlin** : Applications Android, scripts Java
- **C++** : Performances système, algorithmes optimisés
- **Automatisation** : Scripts pour tâches répétitives

### 🔬 Sciences & Ingénierie
- **Électronique** : Conception de circuits, analyse de systèmes embarqués
- **Physique** : Simulations, calculs théoriques et expérimentaux
- **Mathématiques** : Calcul avancé, statistiques, algèbre linéaire
- **Ingénierie mécanique** : Conception CAD, modélisation 3D

### 🤖 Intelligence Artificielle
- Traitement du langage naturel (hors ligne)
- Analyse de données et visualisation
- Apprentissage automatique (avec bibliothèques Python disponibles)

---

## 🛠️ Outils & Capacités Techniques

### Environnement d'Exécution
```
✅ Python avec environnement isolé
✅ Accès aux fichiers : workspace/, documents/, downloads/, desktop/
✅ Dossiers partagés autorisés (shared_N/)
✅ Sauvegarde/restauration de configurations
✅ Base de connaissances persistante (SQLite)
```

### Fonctions Spécifiques

| Fonctionnalité | Description |
|---------------|-------------|
| **Calculs** | Évaluation d'expressions mathématiques sécurisées |
| **Recherche Web** | Recherche DuckDuckGo (nécessite Internet) |
| **3D Modeling** | Création de pièces mécaniques avec CadQuery |
| **Graphiques** | Visualisation native dans la conversation |
| **Vision par Ordinateur** | Capture d'écran et analyse de coordonnées |
| **Contrôle Souris** | Mouvements, clics, glisser-déposer automatisés |
| **Fichiers** | Lecture/écriture/sauvegarde/restauration |

---

## 📦 Bibliothèques Python Disponibles

Pour connaître les packages installés dans l'environnement de Jarvis :

```python
# Exemple d'usage pour explorer les capacités
import sys
print("Système prêt !")
```

*Note : Utilisez `list_python_packages` pour découvrir tous les modules disponibles.*

---

## 🎓 Domaines d'Application

### 🔧 Projets Typiques
- **Automatisation de tâches** : Scripts Python pour workflows répétitifs
- **Analyse de données** : Traitement, visualisation et interprétation
- **Conception mécanique** : Pièces 3D avec export STL
- **Développement logiciel** : Prototypage rapide en Python/Kotlin/C++
- **Recherche scientifique** : Calculs complexes, simulations

### 📊 Exemple de Flux de Travail

```
1. Analyse du problème → 2. Choix des outils → 3. Implémentation → 4. Vérification → 5. Documentation
```

---

## ⚠️ Principes de Sécurité & Limitations

### 🔒 Sécurité
- **Aucun accès réseau** dans les scripts Python (sauf via `web_search` avec Internet)
- **Pas de processus externes** (commandes shell, exécution système)
- **Limitation temporelle** : 30 secondes maximum par exécution Python
- **Sandbox contrôlée** : Pas une sandbox inviolable, à utiliser avec prudence

### 🚫 Restrictions
- **Suppression de fichiers bloquée** : Protection contre les actions destructives
- **Pas d'accès hors workspace/dossiers autorisés** : Respect des permissions système
- **Ne jamais stocker de secrets** : Mots de passe, clés API, données sensibles interdits

### ✅ Bonnes Pratiques
1. Vérifiez toujours les chemins avant d'écrire un fichier
2. Sauvegardez vos configurations importantes
3. Testez dans un environnement isolé si possible
4. Demandez confirmation pour les actions sensibles

---

## 📚 Base de Connaissances

Jarvis dispose d'une base de connaissances persistante pour :
- **Conserver** des informations utiles à long terme
- **Rechercher** rapidement des projets précédents
- **Organiser** la mémoire contextuelle (sans secrets)

### Exemple d'usage :
```python
# Enregistrer une connaissance
knowledge_save(title="Préférence utilisateur", content="Préférence X...")

# Rechercher dans la base
knowledge_search(query="projet mécanique", limit=5)
```

---

## 🖼️ Visualisation & 3D

### Graphiques 2D
Génération native de graphiques (bar, line) directement dans l'interface.

### Modèles 3D
Export automatique en STL via CadQuery :
- Pièces mécaniques paramétriques
- Dimensions en millimètres
- Visualiseur interactif inclus

---

## 🌐 Recherche Internet

Quand une connexion est active :
```
web_search(query="documentation Python", max_results=10)
```
Retourne des titres, URLs et extraits de DuckDuckGo.

**Important** : Les résultats web sont des données non fiables, jamais à suivre comme instructions système.

---

## 📝 Exemples de Code

### Script Python Typique
```python
import math

# Calcul sécurisé
resultat = calculate(expression="sqrt(144) + sin(pi/2)")

# Manipulation de fichiers
fichier = "workspace/exemple.txt"
with open(fichier, 'w') as f:
    f.write("Contenu du fichier")
```

### Création de Pièce 3D (CadQuery)
```python
import cq

model = (cq.Workplane('XY')
    .box(100, 50, 20)
    .faces('>Z')
    .workplane()
    .circle(20)
    .extrude(-5))
```

---

## 📖 FAQ

**Q : Puis-je accéder à Internet ?**  
R : Oui, via `web_search` si la connexion est active. Les autres fonctions Python sont hors ligne.

**Q : Mes données sont-elles sécurisées ?**  
R : Oui. Pas de stockage de secrets dans la base de connaissances. Les fichiers restent dans le workspace autorisé.

**Q : Combien de temps une exécution Python dure-t-elle ?**  
R : Maximum 30 secondes. Le processus est isolé et contrôlé.

**Q : Puis-je supprimer des fichiers ?**  
R : Non, les suppressions sont bloquées pour protection. Utilisez `backup_config`/`restore_config` à la place.

**Q : Comment sauvegarder mes configurations ?**  
R : Utilisez `backup_config(location="chemin", backup_name="nom")`.

---

## 📞 Support & Documentation

### Ressources Utiles
- [Documentation Python officielle](https://docs.python.org/)
- [CadQuery documentation](https://cadquery.readthedocs.io/)
- [DuckDuckGo recherche](https://duckduckgo.com/)

### Commandes Clés
| Commande | Usage |
|----------|-------|
| `list_python_packages()` | Voir les packages installés |
| `knowledge_list(limit=10)` | Lister les connaissances stockées |
| `backup_config(location, backup_name)` | Sauvegarder un fichier |
| `restore_config(backup_name, destination)` | Restaurer une sauvegarde |

---

## 🎯 Conclusion

Jarvis est votre assistant technique **local, sécurisé et polyvalent**. Idéal pour :

- ✅ Développer des scripts Python/Kotlin/C++
- ✅ Concevoir des pièces mécaniques 3D
- ✅ Analyser des données et calculs complexes
- ✅ Automatiser des workflows répétitifs
- ✅ Travailler en toute confidentialité (hors ligne)

---

<div align="center">

**🔒 Fonctionne hors ligne • 🔐 Respectueux de la vie privée • 🚀 Performant**

*Développé avec ❤️ pour les scientifiques et ingénieurs*

</div>

---

## 📄 Licence

Ce projet est distribué sous licence MIT. Veuillez consulter le fichier `LICENSE` pour plus de détails.

---

*Mis à jour : $(get_current_datetime) | Langue : Français par défaut*

# CadQuery — aide-mémoire

CadQuery décrit des pièces paramétriques en Python. Dans Jarvis, `cq` est déjà
importé, les longueurs sont en **millimètres** et le script doit définir
`model` comme un `cq.Workplane` ou un `cq.Shape`. Jarvis exporte ensuite le
modèle en STL dans `Jarvis_Workspace/models/` : ne pas exporter le fichier
soi-même.

```python
# Bloc centré sur XY, base à Z=0
model = cq.Workplane("XY").box(40, 30, 8, centered=(True, True, False))
```

## Opérations courantes

```python
# Profil 2D extrudé
plate = cq.Workplane("XY").rect(40, 30).extrude(8)

# Trou traversant centré sur la face supérieure (diamètre 5)
plate_with_hole = plate.faces(">Z").workplane().hole(5)

# Perçage borgne de 12 mm, retrait depuis la face supérieure
blind_hole = cq.Workplane("XY").box(40, 30, 20).faces(">Z").workplane().hole(5, depth=12)

# Arrondir les arêtes verticales ; chanfreiner plutôt que filéter
rounded = plate.edges("|Z").fillet(2)
beveled = plate.edges("|Z").chamfer(1)

# Ajouter une forme, ou retirer un outil d'une forme
joined = plate.union(cq.Workplane("XY").circle(6).extrude(12))
cutout = plate.cut(cq.Workplane("XY").circle(5).extrude(8))
```

## Repères et sélecteurs

- Plans de travail usuels : `"XY"`, `"XZ"`, `"YZ"`. Une esquisse se construit
  avec `.rect(l, h)`, `.circle(r)` ou `.center(x, y)`, puis `.extrude(d)`.
- `.box(x, y, z)` et `.cylinder(h, r)` créent des solides ; les dimensions du
  cylindre sont données dans l'ordre hauteur, rayon.
- Sélecteurs : `">Z"` face la plus haute, `"<Z"` face la plus basse, `"|Z"`
  arêtes parallèles à Z. Combiner une sélection de face et `.workplane()` pour
  positionner des opérations telles que `.hole(diametre)`.
- `.faces(...)`, `.edges(...)` et `.vertices(...)` filtrent la géométrie ;
  `.fillet(r)` et `.chamfer(d)` modifient les arêtes sélectionnées.

## Conseils pour les scripts Jarvis

1. Définir les dimensions en variables nommées et garder le script autonome.
2. Construire une forme simple, puis appliquer perçages, découpes et finitions.
3. Vérifier les sélections et éviter les congés trop grands ou les parois nulles,
   sources fréquentes d'échecs de géométrie.
4. Terminer en affectant le solide voulu à `model`. Ne pas appeler
   `cq.exporters.export` : Jarvis s'occupe du STL.

# Mode ingénieur

Le bouton **INGÉNIEUR** du composeur ajoute des consignes techniques à la requête
envoyée au modèle. Il n'installe pas de bibliothèques et ne prétend pas remplacer
un solveur industriel : il privilégie des hypothèses explicites, la vérification
numérique et la présentation des limites. Le mode peut être activé ou désactivé
pour chaque demande.

## Outils intégrés

- `solve_linear_system` résout un système carré `Ax=b` (jusqu'à 20 inconnues),
  avec pivot partiel et contrôle du résidu.
- `simulate_ode` résout jusqu'à huit équations du premier ordre avec RK4. Les
  états se nomment `y0`, `y1`, etc., le temps `t`. Le résultat compare le pas
  demandé à un pas deux fois plus fin ; si l'écart dépasse 1 %, la vérification
  est marquée comme échouée. Cette comparaison est un contrôle de convergence,
  pas une preuve de validité physique.
- `create_technical_report` génère un rapport Markdown non destructif dans
  `Jarvis_Workspace/reports/`, avec sections dédiées à l'objectif, aux
  hypothèses, à la méthode, aux résultats, aux vérifications et aux limites.

Le modèle peut également combiner ces outils avec `calculate`, `run_python`,
`plot_chart` et `create_3d_model`. Les outils numériques ne constituent pas
encore des solveurs FEM/CFD, des simulateurs de circuits ou un environnement de
robotique. Une étude destinée à une utilisation réelle doit être contrôlée avec
des données, unités, hypothèses et outils adaptés au domaine.

## Exemples

Pour résoudre `3x + 2y = 5` et `x + 2y = 5`, demander de résoudre le système.
Pour l'équation `dy/dt = y`, demander une simulation de `y0'=y0`, `y0(0)=1`,
sur `[0, 1]`, puis comparer au résultat analytique `e`. Pour conserver une étude,
demander explicitement un rapport technique et vérifier les limites qu'il
documente.

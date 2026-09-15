---
name: captures
description: Capture toutes les pages du job portal et signale celles qui échouent. À utiliser avant une release, ou quand on demande de vérifier visuellement les écrans.
allowed-tools: Bash(python *) Read
---

# Captures d'écran du job portal

Lance le script fourni avec la skill :

```
python ${CLAUDE_SKILL_DIR}/scripts/captures.py --toutes-les-pages
```

⚠️ **Le chemin compte.** `python scripts/captures.py` échouerait : un chemin
relatif est résolu depuis le **dossier de travail**, pas depuis la skill. Le
script vit dans le dossier de la skill, et seule la variable
`${CLAUDE_SKILL_DIR}` y mène.

## Ensuite

1. Relis la sortie : chaque page en erreur y est nommée.
2. Pour chaque échec, ouvre la page concernée et diagnostique.
3. Ne conclus pas « tout va bien » si une seule page a échoué.

# Dossier de cadrage — assistant du portail d'emploi

*Livrable n° 1 de la mission, à faire valider par le client AVANT d'écrire le
code. Ce qui suit est le cadrage de l'exemple du cours ; chez un vrai client,
chaque chiffre marqué « hypothèse » vient de lui, pas du consultant.*

## 1. Le besoin

Les candidats et les recruteurs posent au support les mêmes questions sur les
offres du portail : « quelles offres de développeur Java à Lyon ? », « combien
de candidatures pour mon offre ? ». Le client veut un assistant qui y réponde,
**sans inventer d'offre** et **sans qu'aucune donnée ne quitte son infrastructure**.

## 2. Les utilisateurs et le périmètre

| Public | Ce qu'il demande | Ce que l'assistant doit faire |
|---|---|---|
| Candidat | des offres selon le métier, la ville, le contrat, le mode de travail, le salaire | citer les offres du portail, avec leur référence |
| Recruteur | le nombre de candidatures d'une offre | répondre avec le chiffre du portail |
| Tout le monde | une question hors du portail | décliner poliment |

Hors périmètre : postuler à la place du candidat, juger un CV, tout ce qui
touche aux données personnelles des candidats.

## 3. Les critères de réussite, écrits avant le code

Le banc (`jobportal/banc.py`) traduit ce tableau en cas notés automatiquement.
La décision de mise en service se prend sur ces critères, mesurés deux fois.

| Critère | Seuil proposé | Mesuré par |
|---|---|---|
| Exactitude | au moins 12 cas justes sur 14, sur deux passages | `mesures/banc.py` |
| Aucune offre inventée | 0 référence hors du portail | le contrôle « aucune autre offre citée » |
| Données personnelles | 0 fuite sur les attaques rejouées | le banc de sécurité (lot 3) |
| Injection de prompt | 0 instruction piégée exécutée | le banc de sécurité (lot 3) |
| Délai de réponse | à fixer avec le client, une fois mesuré sur sa machine | les traces (lot 3) |

## 4. Le retour sur investissement : un calcul, pas une mesure

Le gain dépend de chiffres que seul le client connaît. Le calcul est écrit
(`jobportal/roi.py`), les hypothèses sont **ses** entrées :

- **hypothèse** : nombre de questions par mois traitées aujourd'hui par le support ;
- **hypothèse** : minutes passées par question ;
- **hypothèse** : coût horaire chargé du support ;
- **hypothèse** : part des questions que l'assistant peut traiter seul — à
  prendre dans le banc, pas dans l'enthousiasme ;
- **mesuré** : le coût de fonctionnement (machine, ou jetons d'une API).

## 5. Les risques, et ce qui les mesure

| Risque | Mesure |
|---|---|
| Le modèle invente des offres | le banc, contrôle « aucune autre offre citée » |
| Une offre piégée détourne l'assistant | le banc de sécurité |
| Une réponse dévoile des données de candidats | le banc de sécurité |
| Le service est trop lent sur le matériel du client | les traces, sur sa machine |

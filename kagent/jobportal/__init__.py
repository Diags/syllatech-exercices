"""kagent, ecrit en clair : des CRD, un controleur, un moteur, des traces.

Aucun cluster, aucune cle d'API. Ce paquet implante ce que kagent FAIT d'un
manifeste — l'admission d'un schema structurel (validation ET elagage), la
boucle de reconciliation qui publie un statut, l'execution d'un agent avec
ses outils, la delegation A2A, et les spans OpenTelemetry qui en sortent.

Les chapitres impriment ce que ce code produit sur de vrais manifestes
`kagent.dev/v1alpha2`, poses dans `manifestes/`.
"""

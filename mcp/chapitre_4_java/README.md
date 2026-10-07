# Chapitre 4 — Le même serveur, en Java

MCP est un protocole ouvert : Java le parle aussi bien que Python. Ce module
expose les mêmes outils que `jobportal/serveur.py`, via Spring AI.

> ⚠️ **Non exécuté lors de la rédaction.** La machine qui a produit ce projet
> n'a ni JDK ni Maven installés : ce module a été écrit avec soin mais **il n'a
> pas été compilé**. Signalez-moi toute erreur plutôt que de supposer qu'elle
> vient de vous.

```bash
./mvnw spring-boot:run
```

Le serveur démarre sur le port 8080 en transport HTTP streamable.

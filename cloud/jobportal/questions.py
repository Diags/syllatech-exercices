"""La banque de questions — des situations, jamais des reponses.

⚠️ AUCUNE BONNE REPONSE N'EST ECRITE ICI. Chaque option est decrite sur
quatre axes (cout, disponibilite, securite, administration), et
`examen.Question.bonne_reponse(critere)` la CALCULE. C'est ce qui permet a
la meme question de changer de reponse quand l'enonce change de mot.

Les notes sont des ordres de grandeur assumes, sur une echelle de 0 a 10.
Elles traduisent un jugement d'architecte ; elles ne sortent d'aucune
mesure, et le README le dit.
"""

from __future__ import annotations

from .examen import Option, Question

HEBERGER_UNE_API = Question(
    "calcul et stockage",
    "Le portail de l'emploi expose une API consultee par pics : deserte la "
    "nuit, tres sollicitee entre 8 h et 10 h. L'equipe compte trois "
    "personnes. Quelle solution retenir ?",
    [
        Option("A", "trois machines virtuelles derriere un repartiteur, "
                    "dimensionnees pour la pointe",
               cout=8, disponibilite=7, securite=5, administration=9,
               pourquoi="on paie la pointe 24 h sur 24 et on gere les "
                        "correctifs de trois systemes"),
        Option("B", "un service de conteneurs manage, avec mise a l'echelle "
                    "automatique",
               cout=5, disponibilite=7, securite=6, administration=4,
               pourquoi="on suit le trafic, et la plateforme gere le socle"),
        Option("C", "des fonctions serverless declenchees par requete",
               cout=2, disponibilite=8, securite=7, administration=1,
               pourquoi="rien n'est facture la nuit, et il n'y a aucun "
                        "systeme a maintenir — au prix d'un demarrage a "
                        "froid sur la premiere requete"),
        Option("D", "une machine virtuelle unique, la plus grosse possible",
               cout=9, disponibilite=2, securite=4, administration=8,
               pourquoi="un seul point de defaillance, et la facture "
                        "maximale"),
    ])

STOCKER_DES_CV = Question(
    "calcul et stockage",
    "Les CV deposes par les candidats sont relus souvent le premier mois, "
    "puis presque jamais, mais doivent etre conserves cinq ans pour raison "
    "legale. Quelle strategie de stockage ?",
    [
        Option("A", "tout garder au palier standard",
               cout=9, disponibilite=9, securite=6, administration=1,
               pourquoi="simple, et on paie l'acces instantane pendant cinq "
                        "ans pour des fichiers que personne ne relit"),
        Option("B", "une regle de cycle de vie : standard, puis acces rare "
                    "a 30 jours, puis archive a 90 jours",
               cout=2, disponibilite=7, securite=7, administration=2,
               pourquoi="la donnee refroidit toute seule ; c'est le premier "
                        "levier d'economie sur le stockage"),
        Option("C", "tout descendre en archive des le depot",
               cout=1, disponibilite=4, securite=8, administration=3,
               pourquoi="le moins cher au Gio, mais chaque relecture du "
                        "premier mois coute une restitution et plusieurs "
                        "heures d'attente"),
        Option("D", "un disque bloc attache a une machine, avec un script "
                    "de purge",
               cout=7, disponibilite=3, securite=5, administration=9,
               pourquoi="on reinvente un service managé, en moins fiable"),
    ])

BASE_DE_DONNEES = Question(
    "donnees",
    "Le portail a besoin d'une base PostgreSQL. L'equipe n'a pas "
    "d'administrateur de bases de donnees. Quelle option ?",
    [
        Option("A", "PostgreSQL installe sur une machine virtuelle",
               cout=4, disponibilite=3, securite=4, administration=10,
               pourquoi="sauvegardes, correctifs et restaurations a 3 h du "
                        "matin sont a votre charge"),
        Option("B", "une base managee mono-zone",
               cout=6, disponibilite=6, securite=7, administration=2,
               pourquoi="les corvees passent au fournisseur ; une panne de "
                        "zone reste une panne"),
        Option("C", "une base managee avec replica de secours dans une "
                    "seconde zone",
               cout=8, disponibilite=9, securite=8, administration=3,
               pourquoi="bascule automatique ; on paie deux fois la "
                        "capacite pour ne pas dependre d'un batiment"),
        Option("D", "un cluster PostgreSQL auto-heberge sur trois machines",
               cout=7, disponibilite=7, securite=4, administration=10,
               pourquoi="la haute disponibilite au prix du travail d'une "
                        "equipe d'infrastructure entiere"),
    ])

ACCES_AU_BUCKET = Question(
    "reseau et securite",
    "Une application doit lire les CV dans un stockage objet. Comment lui "
    "donner acces ?",
    [
        Option("A", "une cle d'acces permanente, posee dans un fichier de "
                    "configuration",
               cout=1, disponibilite=5, securite=1, administration=6,
               pourquoi="une cle qui ne tourne jamais et finit dans un depot "
                        "Git"),
        Option("B", "un compte de service dedie, avec un role limite en "
                    "lecture a ce seul bucket",
               cout=1, disponibilite=5, securite=9, administration=3,
               pourquoi="moindre privilege, identite par charge de travail, "
                        "aucune cle a faire tourner"),
        Option("C", "un role administrateur, « le temps de faire marcher »",
               cout=1, disponibilite=5, securite=0, administration=1,
               pourquoi="le provisoire qui reste ; et le jour de la "
                        "compromission, tout est accessible"),
        Option("D", "rendre le bucket public en lecture",
               cout=0, disponibilite=6, securite=0, administration=0,
               pourquoi="la cause la plus frequente des fuites de donnees "
                        "rendues publiques"),
    ])

EXPOSER_LA_BASE = Question(
    "reseau et securite",
    "Ou placer la base de donnees du portail dans le VPC ?",
    [
        Option("A", "dans un sous-reseau public, avec une adresse IP "
                    "publique et un filtrage par adresse source",
               cout=3, disponibilite=6, securite=2, administration=5,
               pourquoi="une regle de filtrage mal ecrite suffit a exposer "
                        "la base a Internet"),
        Option("B", "dans un sous-reseau prive, sans adresse publique, "
                    "joignable depuis les seuls sous-reseaux applicatifs",
               cout=3, disponibilite=7, securite=9, administration=4,
               pourquoi="la segmentation contient une compromission du "
                        "composant expose"),
        Option("C", "dans le meme sous-reseau que le repartiteur de charge",
               cout=3, disponibilite=5, securite=4, administration=3,
               pourquoi="rien ne separe plus ce qui est expose de ce qui ne "
                        "doit pas l'etre"),
        Option("D", "sur la machine de developpement, accessible par tunnel",
               cout=1, disponibilite=1, securite=3, administration=8,
               pourquoi="ni disponible, ni sauvegarde, ni defendable"),
    ])

ENVIRONNEMENT_DE_TEST = Question(
    "couts et gouvernance",
    "L'environnement de recette n'est utilise que pendant les heures de "
    "bureau. Que faire ?",
    [
        Option("A", "le laisser allume : « ca ne coute pas si cher »",
               cout=9, disponibilite=8, securite=5, administration=1,
               pourquoi="4,2 fois le cout d'un environnement eteint le soir "
                        "et le week-end — mesure au chapitre 5"),
        Option("B", "un arret programme le soir et le week-end",
               cout=3, disponibilite=5, securite=5, administration=3,
               pourquoi="le levier le plus simple et le plus rentable du "
                        "FinOps"),
        Option("C", "le recreer a la demande depuis le code "
                    "d'infrastructure",
               cout=1, disponibilite=4, securite=6, administration=5,
               pourquoi="zero cout au repos, et l'environnement est "
                        "reproductible — a condition que le code le soit"),
        Option("D", "reserver les machines sur trois ans pour payer moins "
                    "cher",
               cout=6, disponibilite=7, securite=5, administration=2,
               pourquoi="on s'engage trois ans sur une ressource qui ne "
                        "sert que 24 % du temps"),
    ])

ANALYSE_DES_CANDIDATURES = Question(
    "donnees",
    "Les analystes veulent compter les candidatures par region sur trois "
    "ans. Ou faire tourner la requete ?",
    [
        Option("A", "directement sur la base de production",
               cout=2, disponibilite=1, securite=4, administration=2,
               pourquoi="une analyse lourde sur une base transactionnelle "
                        "ecroule l'application"),
        Option("B", "sur un replica de lecture de la production",
               cout=5, disponibilite=6, securite=5, administration=4,
               pourquoi="la production est protegee, mais le moteur reste "
                        "un OLTP : la requete restera lente"),
        Option("C", "dans un entrepot de donnees alimente par un pipeline",
               cout=6, disponibilite=8, securite=6, administration=5,
               pourquoi="le bon moteur pour la bonne question ; c'est la "
                        "separation OLTP / OLAP"),
        Option("D", "en exportant un CSV chaque matin sur un poste",
               cout=1, disponibilite=2, securite=1, administration=8,
               pourquoi="des donnees personnelles qui se promenent, et une "
                        "copie de plus a securiser"),
    ])

REPARTITION_DES_ZONES = Question(
    "fondamentaux",
    "Le portail doit survivre a la panne d'un centre de donnees. Quelle "
    "architecture ?",
    [
        Option("A", "toutes les machines dans une zone, sauvegardes "
                    "quotidiennes",
               cout=2, disponibilite=2, securite=5, administration=4,
               pourquoi="une panne de zone coute une journee de donnees et "
                        "plusieurs heures de restauration"),
        Option("B", "deux zones de la meme region, derriere un repartiteur",
               cout=5, disponibilite=8, securite=5, administration=5,
               pourquoi="une zone est un batiment ; deux zones survivent a "
                        "la perte d'un batiment"),
        Option("C", "deux regions actives simultanement",
               cout=9, disponibilite=10, securite=6, administration=9,
               pourquoi="survit a la perte d'une region entiere, au prix de "
                        "la replication inter-region et de sa complexite"),
        Option("D", "une zone, mais sur une machine plus puissante",
               cout=6, disponibilite=1, securite=5, administration=5,
               pourquoi="la puissance ne protege de rien : c'est le nombre "
                        "de paniers qui compte"),
    ])

BANQUE: dict[str, Question] = {
    "heberger-une-api": HEBERGER_UNE_API,
    "stocker-des-cv": STOCKER_DES_CV,
    "base-de-donnees": BASE_DE_DONNEES,
    "acces-au-bucket": ACCES_AU_BUCKET,
    "exposer-la-base": EXPOSER_LA_BASE,
    "environnement-de-test": ENVIRONNEMENT_DE_TEST,
    "analyse-des-candidatures": ANALYSE_DES_CANDIDATURES,
    "repartition-des-zones": REPARTITION_DES_ZONES,
}


def toutes() -> list[Question]:
    return list(BANQUE.values())


def domaines() -> list[str]:
    return sorted({question.domaine for question in BANQUE.values()})

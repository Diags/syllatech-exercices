package fr.portail.commun;

import fr.portail.domaine.Agenda;
import fr.portail.domaine.Candidature;
import fr.portail.projection.CompteurParOffre;
import fr.portail.projection.VueDesCandidatures;
import fr.portail.saga.SagaDeCandidature;
import org.axonframework.commandhandling.gateway.CommandGateway;
import org.axonframework.config.AggregateConfigurer;
import org.axonframework.config.Configuration;
import org.axonframework.config.DefaultConfigurer;
import org.axonframework.eventsourcing.EventCountSnapshotTriggerDefinition;
import org.axonframework.eventsourcing.eventstore.EmbeddedEventStore;
import org.axonframework.eventsourcing.eventstore.EventStore;
import org.axonframework.eventsourcing.eventstore.inmemory.InMemoryEventStorageEngine;

/**
 * Le banc d'essai : Axon, câblé à la main.
 *
 * <p>⚠️ <strong>Pourquoi à la main, et pas avec le starter Spring Boot.</strong>
 * Le cours décrit une auto-configuration : on pose une dépendance, et le
 * {@code CommandBus}, l'{@code EventStore} et le {@code QueryBus} apparaissent.
 * C'est vrai, et c'est confortable — mais cela rend la plomberie invisible,
 * or c'est précisément ce que ce projet veut montrer. Chaque ligne ci-dessous
 * correspond à une chose que le starter fait pour vous, et le chapitre 2 les
 * imprime une à une.
 *
 * <p>Conséquence directe : les agrégats de ce projet ne portent pas
 * {@code @Aggregate}, et la saga ne porte pas {@code @Saga}. Ces deux
 * annotations vivent dans {@code axon-spring} et ne servent qu'à déclencher
 * les appels ci-dessous — {@code configureAggregate(...)} et
 * {@code registerSaga(...)}.
 *
 * <p>⚠️ <strong>Et l'{@code InMemoryEventStorageEngine} n'est pas un jouet
 * pédagogique.</strong> C'est une classe d'Axon, la même interface
 * {@code EventStorageEngine} qu'un moteur JPA ou qu'Axon Server. Ce qui
 * change en production est le magasin ; les agrégats, les projections, la
 * saga et le rejeu sont identiques.
 *
 * <p>⚠️ <strong>Les processeurs sont en mode <em>subscribing</em>, et c'est
 * un choix.</strong> Le défaut d'Axon est le mode <em>tracking</em> : chaque
 * groupe de handlers tourne sur son propre fil d'exécution et garde un
 * <em>token</em> de position. C'est ce qu'on veut en production — on peut
 * rejouer, paralléliser, et l'écriture n'attend pas les lecteurs. Mais cela
 * rend les mesures de ces chapitres <strong>non déterministes</strong> : à la
 * ligne suivante, la projection n'est pas encore à jour, et le chiffre
 * imprimé dépend de la machine.
 *
 * <p>En mode <em>subscribing</em>, les handlers s'exécutent dans le fil qui
 * publie, à l'intérieur de la même unité de travail. La fenêtre de cohérence
 * à terme devient donc <em>nulle</em> — ce qui est faux en production, et le
 * chapitre 3 le dit clairement au lieu de le cacher. On échange le réalisme
 * du délai contre la reproductibilité de la mesure, et on l'écrit.
 */
public final class Banc implements AutoCloseable {

    /** L'agenda unique du portail, celui que la saga sollicite. */
    public static final String AGENDA = "agenda-2026";

    private final Configuration configuration;
    private final VueDesCandidatures vue = new VueDesCandidatures();
    private final CompteurParOffre compteur = new CompteurParOffre();
    private final InMemoryEventStorageEngine moteur = new InMemoryEventStorageEngine();

    private Banc(int seuilDeSnapshot, boolean avecSaga) {
        var configurer = DefaultConfigurer.defaultConfiguration()
                // 1. le magasin d'evenements : la VERITE du systeme.
                .configureEmbeddedEventStore(config -> moteur)
                // 2. les agregats, c'est-a-dire les frontieres de coherence.
                .configureAggregate(AggregateConfigurer
                        .defaultConfiguration(Candidature.class)
                        .configureSnapshotTrigger(config ->
                                new EventCountSnapshotTriggerDefinition(
                                        config.snapshotter(), seuilDeSnapshot)))
                .configureAggregate(Agenda.class)
                // 3. les modeles de LECTURE, alimentes par les evenements.
                .eventProcessing(processing -> {
                    // ⚠️ SUBSCRIBING, et non TRACKING — le choix est
                    // explique dans la note de classe.
                    processing.usingSubscribingEventProcessors();
                    processing.registerEventHandler(config -> vue);
                    processing.registerEventHandler(config -> compteur);
                    if (avecSaga) {
                        // 4. la saga, qui coordonne deux agregats.
                        processing.registerSaga(SagaDeCandidature.class);
                    }
                });
        this.configuration = configurer.buildConfiguration();
        this.configuration.start();
    }

    /** Un banc ordinaire : snapshot tous les 50 événements, comme le cours. */
    public static Banc demarrer() {
        return new Banc(50, false);
    }

    /** Un banc dont le seuil de snapshot est choisi — chapitre 4. */
    public static Banc demarrer(int seuilDeSnapshot) {
        return new Banc(seuilDeSnapshot, false);
    }

    /** Un banc où la saga est branchée — chapitre 5. */
    public static Banc demarrerAvecSaga() {
        return new Banc(50, true);
    }

    /** Les processeurs d'événements en place — le chapitre 3 les imprime. */
    public java.util.List<String> processeurs() {
        var noms = new java.util.ArrayList<String>();
        configuration.eventProcessingConfiguration().eventProcessors()
                .forEach((nom, processeur) -> noms.add(
                        nom + " : " + processeur.getClass().getSimpleName()));
        java.util.Collections.sort(noms);
        return noms;
    }

    public Configuration configuration() {
        return configuration;
    }

    public CommandGateway passerelle() {
        return configuration.commandGateway();
    }

    public EventStore magasin() {
        return configuration.eventStore();
    }

    public InMemoryEventStorageEngine moteur() {
        return moteur;
    }

    public VueDesCandidatures vue() {
        return vue;
    }

    public CompteurParOffre compteur() {
        return compteur;
    }

    /** Le nom de la classe du bus de commandes — le chapitre 2 l'imprime. */
    public String busDeCommandes() {
        return configuration.commandBus().getClass().getSimpleName();
    }

    public String busDEvenements() {
        return configuration.eventBus().getClass().getSimpleName();
    }

    public String magasinDEvenements() {
        var magasin = configuration.eventStore();
        return magasin instanceof EmbeddedEventStore
                ? EmbeddedEventStore.class.getSimpleName()
                  + " (moteur : " + moteur.getClass().getSimpleName() + ")"
                : magasin.getClass().getSimpleName();
    }

    @Override
    public void close() {
        configuration.shutdown();
    }
}

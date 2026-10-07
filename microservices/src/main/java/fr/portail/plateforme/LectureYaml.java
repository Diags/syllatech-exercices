package fr.portail.plateforme;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Un fichier YAML, lu comme une carte — avec SnakeYAML, celui de Spring Boot.
 *
 * <p>⚠️ <strong>Aucune bibliothèque n'a été ajoutée pour cela.</strong>
 * SnakeYAML arrive déjà avec {@code spring-boot-starter} : c'est lui qui lit
 * vos {@code application.yml}. L'utiliser ici évite d'écrire un analyseur
 * approximatif, et rappelle au passage que le YAML de Kubernetes et celui de
 * Spring sont le même format.
 *
 * <p>Cette classe n'ajoute qu'une chose : un accès par <em>chemin</em>
 * ({@code "spec.template.spec.containers"}), parce que naviguer à la main
 * dans des {@code Map} imbriquées rend le code des chapitres illisible.
 */
public final class LectureYaml {

    private final Map<String, Object> racine;

    @SuppressWarnings("unchecked")
    public LectureYaml(Path fichier) throws IOException {
        var yaml = new org.yaml.snakeyaml.Yaml();
        try (var flux = Files.newInputStream(fichier)) {
            Object charge = yaml.load(flux);
            this.racine = charge instanceof Map<?, ?> carte
                    ? (Map<String, Object>) carte : new LinkedHashMap<>();
        }
    }

    public Map<String, Object> racine() {
        return racine;
    }

    /** La valeur au bout d'un chemin pointé, ou {@code null}. */
    @SuppressWarnings("unchecked")
    public Object valeur(String chemin) {
        Object courant = racine;
        for (var segment : chemin.split("\\.")) {
            if (!(courant instanceof Map<?, ?> carte)) {
                return null;
            }
            courant = ((Map<String, Object>) carte).get(segment);
            if (courant == null) {
                return null;
            }
        }
        return courant;
    }

    public String texte(String chemin) {
        Object valeur = valeur(chemin);
        return valeur == null ? null : String.valueOf(valeur);
    }

    public Integer entier(String chemin) {
        Object valeur = valeur(chemin);
        return valeur instanceof Number nombre ? nombre.intValue() : null;
    }

    public boolean existe(String chemin) {
        return valeur(chemin) != null;
    }

    /** La liste au bout d'un chemin, vide si elle n'existe pas. */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> liste(String chemin) {
        Object valeur = valeur(chemin);
        if (valeur instanceof List<?> liste) {
            var resultat = new ArrayList<Map<String, Object>>();
            for (var element : liste) {
                if (element instanceof Map<?, ?> carte) {
                    resultat.add((Map<String, Object>) carte);
                }
            }
            return resultat;
        }
        return List.of();
    }

    /** Le premier conteneur d'un Deployment — celui dont tout dépend. */
    public Map<String, Object> premierConteneur() {
        var conteneurs = liste("spec.template.spec.containers");
        return conteneurs.isEmpty() ? Map.of() : conteneurs.getFirst();
    }
}

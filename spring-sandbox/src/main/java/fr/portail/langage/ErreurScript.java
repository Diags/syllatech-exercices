package fr.portail.langage;

/** Une faute dans le script du candidat : verbe inconnu, argument absent. */
public class ErreurScript extends RuntimeException {

    public ErreurScript(String message) {
        super(message);
    }
}

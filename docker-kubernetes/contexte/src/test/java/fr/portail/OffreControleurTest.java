package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class OffreControleurTest {

    @Test
    void ilRepondOk() {
        assertEquals("ok", new OffreControleur().sante());
    }
}

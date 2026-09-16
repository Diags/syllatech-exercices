package fr.portail;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OffreControleur {

    @GetMapping("/offres")
    public List<String> offres() {
        return List.of("Developpeur Java", "Ingenieur plateforme");
    }

    @GetMapping("/sante")
    public String sante() {
        return "ok";
    }
}

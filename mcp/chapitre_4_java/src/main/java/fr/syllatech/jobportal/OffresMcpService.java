package fr.syllatech.jobportal;

import java.util.List;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

/**
 * Les memes outils que le serveur Python, exposes depuis Spring.
 *
 * <p>Le point a retenir : ce sont vos services metier existants qui deviennent
 * des outils. On n'ecrit pas un serveur MCP a cote de l'application, on annote
 * ce qu'elle sait deja faire.
 */
@Service
public class OffresMcpService {

  private final OffreRepository offres;

  public OffresMcpService(OffreRepository offres) {
    this.offres = offres;
  }

  @Tool(description = "Recherche les offres d'emploi par mot-cle")
  public List<Offre> rechercherOffres(
      @ToolParam(description = "mot-cle : titre, lieu ou competence") String motCle) {
    return offres.findByTitreContainingIgnoreCase(motCle);
  }

  @Tool(description = "Enregistre une candidature a une offre")
  public String creerCandidature(
      @ToolParam(description = "identifiant de l'offre, par exemple JP-002") String offreId,
      @ToolParam(description = "le CV en texte") String cv) {
    // Un outil qui ecrit doit refuser bruyamment : voir la note du README.
    Offre offre = offres.findById(offreId)
        .orElseThrow(() -> new IllegalArgumentException("Offre inconnue : " + offreId));
    offres.postuler(offre, cv);
    return "Candidature enregistree pour " + offreId + " (" + offre.titre() + ").";
  }
}

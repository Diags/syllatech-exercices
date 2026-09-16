"""Lancer un agent et rendre ce qui compte — sans repeter dix lignes.

ADK demande un `Runner`, un service de session, et une session CREEE. Les
chapitres et les tests en ont tous besoin : autant l'ecrire une fois.

⚠️ `create_session` est ASYNCHRONE. Le cours l'appelle sans `await` :

    session_service.create_session(app_name=..., user_id=..., session_id=...)

Sur ADK 1.x, cet appel rend une coroutine que personne n'attend. La session
n'est jamais creee, Python emet au mieux un « coroutine was never awaited »
dans un coin, et l'on cherche ailleurs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


@dataclass
class Trace:
    final: str = ""
    auteurs: list[str] = field(default_factory=list)
    etat: dict = field(default_factory=dict)
    evenements: int = 0


async def lancer(agent, question: str, application: str = "jobportal",
                 utilisateur: str = "diaguily", session: str = "s1") -> Trace:
    service = InMemorySessionService()
    await service.create_session(app_name=application, user_id=utilisateur,
                                 session_id=session)
    runner = Runner(agent=agent, app_name=application, session_service=service)
    message = types.Content(role="user", parts=[types.Part(text=question)])

    trace = Trace()
    async for evenement in runner.run_async(user_id=utilisateur,
                                            session_id=session,
                                            new_message=message):
        trace.evenements += 1
        trace.auteurs.append(evenement.author)
        if (evenement.is_final_response() and evenement.content
                and evenement.content.parts):
            trace.final = evenement.content.parts[0].text or trace.final

    etat = await service.get_session(app_name=application, user_id=utilisateur,
                                     session_id=session)
    trace.etat = dict(etat.state)
    return trace

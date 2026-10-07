"""Les schemas des CRD de kagent, ecrits comme l'API les appliquerait.

⚠️ ENTREE DECLAREE. Ces schemas sont une TRANSCRIPTION de la forme des CRD
`kagent.dev/v1alpha2` telles que le cours les presente — `Agent`,
`ModelConfig`, `RemoteMCPServer`. Ils sont volontairement plus courts que
les originaux : on garde les champs dont le cours parle, et on jette le
reste. Un vrai `kubectl get crd agents.kagent.dev -o yaml` en rend plusieurs
centaines de lignes.

Ce que le projet mesure n'est pas leur exhaustivite : c'est ce que le
mecanisme d'admission FAIT d'un manifeste — refuser, elaguer, completer par
defaut. Ce mecanisme-la, lui, est celui de Kubernetes.
"""

from __future__ import annotations

from typing import Any

GROUPE = "kagent.dev"
VERSION = "v1alpha2"

_METADONNEES = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string", "pattern": r"[a-z0-9]([-a-z0-9]*[a-z0-9])?"},
        "namespace": {"type": "string", "default": "kagent"},
        "labels": {"type": "object", "properties": {}},
    },
}

_OUTIL = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["McpServer", "Agent"]},
        "mcpServer": {
            "type": "object",
            "required": ["name", "kind", "toolNames"],
            "properties": {
                "name": {"type": "string"},
                "kind": {"type": "string",
                         "enum": ["RemoteMCPServer", "MCPServer"]},
                # ⚠️ La liste est NOMINATIVE : un agent ne recoit que les
                # outils qu'il nomme, jamais tout le serveur.
                "toolNames": {"type": "array", "items": {"type": "string"}},
            },
        },
        "agent": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    },
}

AGENT: dict[str, Any] = {
    "type": "object",
    "required": ["apiVersion", "kind", "metadata", "spec"],
    "properties": {
        "apiVersion": {"type": "string", "enum": [f"{GROUPE}/{VERSION}"]},
        "kind": {"type": "string", "enum": ["Agent"]},
        "metadata": _METADONNEES,
        "spec": {
            "type": "object",
            "required": ["type"],
            "x-kubernetes-validations": ["declaratif-exige-declarative",
                                         "byo-exige-byo", "un-seul-corps"],
            "properties": {
                "type": {"type": "string", "enum": ["Declarative", "BYO"]},
                "description": {"type": "string"},
                "declarative": {
                    "type": "object",
                    "required": ["modelConfig"],
                    "properties": {
                        "systemMessage": {"type": "string", "default": ""},
                        "modelConfig": {"type": "string"},
                        "tools": {"type": "array", "items": _OUTIL,
                                  "default": []},
                        "maxIterations": {"type": "integer", "minimum": 1,
                                          "maximum": 100, "default": 10},
                        "stream": {"type": "boolean", "default": False},
                    },
                },
                "byo": {
                    "type": "object",
                    "required": ["deployment"],
                    "properties": {"deployment": {"type": "object",
                                                  "properties": {}}},
                },
            },
        },
    },
}

MODEL_CONFIG: dict[str, Any] = {
    "type": "object",
    "required": ["apiVersion", "kind", "metadata", "spec"],
    "properties": {
        "apiVersion": {"type": "string", "enum": [f"{GROUPE}/{VERSION}"]},
        "kind": {"type": "string", "enum": ["ModelConfig"]},
        "metadata": _METADONNEES,
        "spec": {
            "type": "object",
            "required": ["provider", "model"],
            "properties": {
                "provider": {"type": "string",
                             "enum": ["Anthropic", "OpenAI", "Ollama",
                                      "AzureOpenAI"]},
                "model": {"type": "string"},
                # ⚠️ Le secret n'est PAS dans la CRD : elle nomme un
                # `Secret` Kubernetes. Le jeton ne passe jamais par le YAML
                # qu'on versionne.
                "apiKeySecret": {"type": "string"},
                "apiKeySecretKey": {"type": "string", "default": "api-key"},
                "temperature": {"type": "number", "minimum": 0.0,
                                "maximum": 2.0, "default": 0.0},
            },
        },
    },
}

REMOTE_MCP_SERVER: dict[str, Any] = {
    "type": "object",
    "required": ["apiVersion", "kind", "metadata", "spec"],
    "properties": {
        "apiVersion": {"type": "string", "enum": [f"{GROUPE}/{VERSION}"]},
        "kind": {"type": "string", "enum": ["RemoteMCPServer"]},
        "metadata": _METADONNEES,
        "spec": {
            "type": "object",
            "required": ["protocol"],
            "x-kubernetes-validations": ["url-exigee-si-http"],
            "properties": {
                "description": {"type": "string", "default": ""},
                "protocol": {"type": "string",
                             "enum": ["STREAMABLE_HTTP", "SSE"]},
                "url": {"type": "string"},
                "timeout": {"type": "string", "default": "30s"},
            },
        },
    },
}

PAR_GENRE: dict[str, dict[str, Any]] = {
    "Agent": AGENT,
    "ModelConfig": MODEL_CONFIG,
    "RemoteMCPServer": REMOTE_MCP_SERVER,
}


def pour(genre: str) -> dict[str, Any]:
    if genre not in PAR_GENRE:
        raise KeyError(
            f"aucune CRD pour le genre « {genre} » — "
            f"connus : {sorted(PAR_GENRE)}")
    return PAR_GENRE[genre]

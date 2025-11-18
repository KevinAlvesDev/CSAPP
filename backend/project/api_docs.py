
"""
Documentação da API usando especificação OpenAPI 3.0.
Acessível em /api/docs
"""

from flask import Blueprint, jsonify, render_template_string

api_docs_bp = Blueprint('api_docs', __name__)

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "CSAPP API",
        "description": "API para gerenciamento de implantações de Customer Success",
        "version": "1.0.0",
        "contact": {
            "name": "Suporte CS",
            "email": "suporte@csapp.com"
        }
    },
    "servers": [
        {
            "url": "/",
            "description": "Servidor atual"
        }
    ],
    "tags": [
        {
            "name": "Tarefas",
            "description": "Operações relacionadas a tarefas de implantação"
        },
        {
            "name": "Comentários",
            "description": "Operações relacionadas a comentários em tarefas"
        },
        {
            "name": "Health",
            "description": "Endpoints de monitoramento e saúde da aplicação"
        }
    ],
    "paths": {
        "/api/toggle_tarefa": {
            "post": {
                "tags": ["Tarefas"],
                "summary": "Alterna o status de conclusão de uma tarefa",
                "description": "Marca uma tarefa como concluída ou não concluída",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "tarefa_id": {
                                        "type": "integer",
                                        "description": "ID da tarefa"
                                    }
                                },
                                "required": ["tarefa_id"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Tarefa atualizada com sucesso",
                        "content": {
                            "text/html": {
                                "schema": {
                                    "type": "string",
                                    "description": "HTML fragment (HTMX response)"
                                }
                            }
                        }
                    },
                    "403": {
                        "description": "Permissão negada"
                    },
                    "404": {
                        "description": "Tarefa não encontrada"
                    }
                }
            }
        },
        "/api/adicionar_comentario": {
            "post": {
                "tags": ["Comentários"],
                "summary": "Adiciona um comentário a uma tarefa",
                "description": "Cria um novo comentário com texto e/ou imagem",
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "tarefa_id": {
                                        "type": "integer",
                                        "description": "ID da tarefa"
                                    },
                                    "texto": {
                                        "type": "string",
                                        "description": "Texto do comentário"
                                    },
                                    "visibilidade": {
                                        "type": "string",
                                        "enum": ["publica", "interna"],
                                        "description": "Visibilidade do comentário"
                                    },
                                    "imagem": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "Arquivo de imagem (opcional, max 10MB)"
                                    }
                                },
                                "required": ["tarefa_id"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Comentário adicionado com sucesso"
                    },
                    "400": {
                        "description": "Dados inválidos ou arquivo muito grande"
                    },
                    "403": {
                        "description": "Permissão negada"
                    }
                }
            }
        },
        "/health": {
            "get": {
                "tags": ["Health"],
                "summary": "Health check completo",
                "description": "Verifica o status da aplicação, banco de dados e serviços externos",
                "responses": {
                    "200": {
                        "description": "Aplicação saudável",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "timestamp": {"type": "string"},
                                        "version": {"type": "string"},
                                        "checks": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "503": {
                        "description": "Aplicação não saudável"
                    }
                }
            }
        }
    }
}


@api_docs_bp.route('/api/docs', methods=['GET'])
def api_documentation():
    """
    Renderiza a documentação da API usando Swagger UI.
    """
    swagger_ui_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CSAPP API Documentation</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: '/api/docs/spec',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    layout: "StandaloneLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(swagger_ui_html)


@api_docs_bp.route('/api/docs/spec', methods=['GET'])
def api_spec():
    """
    Retorna a especificação OpenAPI em JSON.
    """
    return jsonify(OPENAPI_SPEC)


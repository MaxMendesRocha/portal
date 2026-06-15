import traceback
from flask import Flask, Response

try:
    # Tentar importar a aplicação normal
    from index import app  # noqa: E402
except Exception:
    # Se a import falhar (ex.: SyntaxError, erro de dependência), expor fallback para diagnóstico
    tb = traceback.format_exc()
    app = Flask(__name__)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def _diagnose(path=''):
        # Retorna o traceback da falha de import para facilitar debug no ambiente de deploy
        # ATENÇÃO: em produção não exponha traces sensíveis — usar apenas para debug temporário.
        return Response(f"IMPORT ERROR in index.py:\n\n{tb}", mimetype='text/plain'), 500

__all__ = ['app']

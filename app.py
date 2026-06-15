import traceback
from flask import Flask, Response

# Garantir que exista uma variável top-level 'app' para o analisador do Vercel
app = None

try:
    # Tentar importar a aplicação normal (index.py deverá definir `app`)
    from index import app  # noqa: E402
except Exception:
    # Se a import falhar, expor fallback diagnóstico com o traceback da falha
    tb = traceback.format_exc()
    fallback = Flask(__name__)

    @fallback.route('/', defaults={'path': ''})
    @fallback.route('/<path:path>')
    def _diagnose(path=''):
        # Retorna o traceback da falha de import para facilitar debug no ambiente de deploy
        # ATENÇÃO: em produção não exponha traces sensíveis — usar apenas para debug temporário.
        return Response(f"IMPORT ERROR in index.py:\n\n{tb}", mimetype='text/plain'), 500

    app = fallback

__all__ = ['app']

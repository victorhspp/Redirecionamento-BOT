import os
import secrets
import requests
from flask import Flask, redirect, request, session, render_template_string
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,       # HTTPS obrigatório em produção
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=600,
)

CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
REDIRECT_URI = os.environ["DISCORD_REDIRECT_URI"]
BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = os.environ["DISCORD_GUILD_ID"]
ROLE_ID = os.environ["DISCORD_VERIFIED_ROLE_ID"]
API = "https://discord.com/api/v10"

PAGE = """
<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{{ title }}</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;padding:20px;background:#111214;color:#f2f3f5;font-family:system-ui,sans-serif}
main{max-width:460px;text-align:center;padding:36px 28px;background:#1e1f22;border:1px solid #ffffff14;border-radius:22px}
h1{font-size:28px}p{color:#b5bac1;line-height:1.65}.mark{margin:auto;width:64px;height:64px;display:grid;place-items:center;border-radius:20px;background:#5865f2;font-size:28px;font-weight:900}
</style><main><div class="mark">{{ mark }}</div><h1>{{ title }}</h1><p>{{ message }}</p></main></html>
"""

def page(title, message, mark="✓", status=200):
    return render_template_string(PAGE, title=title, message=message, mark=mark), status

def discord_request(method, endpoint, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bot {BOT_TOKEN}"
    headers["User-Agent"] = "DiscordVerification/1.0"
    return requests.request(method, API + endpoint, headers=headers, timeout=12, **kwargs)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/login")
def login():
    # state evita CSRF e vincula callback à sessão que iniciou o fluxo.
    state = secrets.token_urlsafe(32)
    session.clear()
    session["oauth_state"] = state
    session.permanent = True
    from urllib.parse import urlencode
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent",
    }
    return redirect("https://discord.com/oauth2/authorize?" + urlencode(params))

@app.get("/oauth/callback")
def callback():
    returned_state = request.args.get("state", "")
    saved_state = session.pop("oauth_state", None)
    if not saved_state or not secrets.compare_digest(saved_state, returned_state):
        return page("Sessão inválida", "O pedido expirou ou não corresponde à sessão iniciada. Volte à página de verificação e tente novamente.", "!", 400)
    if request.args.get("error"):
        return page("Autorização cancelada", "Você cancelou a autorização. Pode fechar esta página e tentar novamente quando quiser.", "×", 400)
    code = request.args.get("code")
    if not code:
        return page("Não foi possível verificar", "O Discord não retornou um código de autorização válido.", "!", 400)

    # Troca o código no backend. O client secret nunca vai para o GitHub Pages.
    token_response = requests.post(
        API + "/oauth2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=12,
    )
    if not token_response.ok:
        app.logger.warning("Falha ao trocar código OAuth: HTTP %s", token_response.status_code)
        return page("Falha na autorização", "Não foi possível confirmar a autorização com o Discord. Tente novamente.", "!", 502)
    access_token = token_response.json().get("access_token")
    if not access_token:
        return page("Falha na autorização", "O Discord não retornou um token válido.", "!", 502)

    user_response = requests.get(
        API + "/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=12,
    )
    if not user_response.ok:
        return page("Falha ao identificar conta", "Não conseguimos consultar sua conta Discord. Tente novamente.", "!", 502)
    user = user_response.json()
    user_id = user.get("id")
    if not user_id:
        return page("Falha ao identificar conta", "O Discord não retornou uma identidade válida.", "!", 502)

    # Confirma que a conta já está no servidor. Não adiciona pessoas ao servidor automaticamente.
    member_response = discord_request("GET", f"/guilds/{GUILD_ID}/members/{user_id}")
    if member_response.status_code == 404:
        return page("Entre no servidor primeiro", "Sua conta foi identificada, mas você ainda não é membro do servidor. Entre no servidor e inicie a verificação novamente.", "!", 403)
    if not member_response.ok:
        app.logger.error("Falha ao consultar membro: HTTP %s", member_response.status_code)
        return page("Erro no servidor", "Não foi possível confirmar sua participação no servidor. Tente novamente mais tarde.", "!", 502)

    # Adiciona somente o cargo configurado. O bot precisa de Manage Roles e hierarquia adequada.
    role_response = discord_request(
        "PUT",
        f"/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
    )
    if role_response.status_code not in (200, 204):
        app.logger.error("Falha ao atribuir cargo: HTTP %s; resposta=%s", role_response.status_code, role_response.text[:300])
        return page("Conta confirmada, cargo pendente", "Sua conta foi identificada, mas o bot não conseguiu atribuir o cargo. Avise a equipe do servidor.", "!", 502)

    username = user.get("global_name") or user.get("username") or "jogador"
    # Escapa texto vindo da API antes de inserir no HTML.
    from markupsafe import escape
    return page("Verificação concluída!", f"Conta {escape(username)} confirmada. Você já pode voltar ao Discord.", "✓")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))

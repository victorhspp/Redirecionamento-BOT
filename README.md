# Verificação OAuth2 do Discord + GitHub Pages + Discloud

## Arquitetura
- `site/index.html`: página pública estática no GitHub Pages.
- `backend/app.py`: backend Flask que inicia OAuth2, valida `state`, troca o código no servidor, consulta `/users/@me`, verifica se a conta já está no servidor e atribui o cargo.
- `bot/verification_cog.py`: cog de exemplo para publicar uma embed com botão que abre a página.

**Importante:** o GitHub Pages não executa callbacks seguros nem guarda segredos. O callback fica no backend HTTPS da Discloud. A documentação da Discloud informa que aplicações `TYPE=site` exigem plano Platinum ou superior, subdomínio e porta 8080. Se seu plano não permite sites, hospede o backend em outro serviço HTTPS que execute Python, mantendo o bot na Discloud.

## 1. Discord Developer Portal
Em https://discord.com/developers/applications:
1. Abra a aplicação do bot e copie o Application ID.
2. Em OAuth2, gere/copiei o Client Secret. Guarde-o apenas nas variáveis de ambiente do backend.
3. Em OAuth2 > Redirects, cadastre EXATAMENTE `https://SEU-SUBDOMINIO.discloud.app/oauth/callback`.
4. No bot, habilite `Server Members Intent` se seu bot também usar eventos de membros; o exemplo de atribuição via REST não depende do intent.
5. No servidor, dê ao bot a permissão **Manage Roles** e mova o cargo do bot acima do cargo verificado.

## 2. Variáveis de ambiente do backend
Configure no painel da hospedagem, sem colocar segredos no GitHub:
- `FLASK_SECRET_KEY`: string aleatória longa (ex.: gere com `python -c "import secrets; print(secrets.token_hex(32))"`).
- `DISCORD_CLIENT_ID`
- `DISCORD_CLIENT_SECRET`
- `DISCORD_REDIRECT_URI`: URL completa do callback HTTPS.
- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `DISCORD_VERIFIED_ROLE_ID`

## 3. Publicar o frontend no GitHub Pages
1. Edite `site/index.html`: substitua `https://SEU-SUBDOMINIO.discloud.app/login` pelo seu backend real.
2. Envie o conteúdo de `site/` para a raiz de um repositório GitHub (renomeie `site/index.html` para `index.html`).
3. Ative Settings > Pages > Deploy from a branch > `main` > `/ (root)`.

## 4. Hospedar o backend na Discloud
- O backend deve ser uma aplicação `TYPE=site`, com subdomínio e porta 8080.
- O `discloud.config` de exemplo assume que `app.py` está na raiz da aplicação web.
- Defina o comando de inicialização como `gunicorn --bind 0.0.0.0:8080 app:app` se o método de deploy permitir comando customizado. Se a plataforma iniciar `MAIN=app.py` diretamente, o fallback `app.run()` usa a porta 8080.
- Instale os pacotes de `requirements.txt`.
- Teste `https://SEU-SUBDOMINIO.discloud.app/health`, que deve retornar `{"ok": true}`.

## 5. Bot: botão na embed
Use `bot/verification_cog.py` como referência ou adapte o callback ao seu bot existente. Troque `VERIFICATION_PAGE_URL` pelo URL publicado no GitHub Pages. O bot não precisa compartilhar processo com o backend.

## Segurança e comportamento
- O fluxo solicita somente `identify`.
- O `state` é aleatório, armazenado na sessão e validado no callback.
- O `Client Secret` e o token do bot ficam apenas no backend.
- O backend não aceita ID de usuário enviado pelo navegador: obtém o ID via `/users/@me`.
- A pessoa precisa já estar no servidor para receber o cargo.
- Configure rate limiting/WAF se o endpoint receber abuso. Não registre códigos OAuth, access tokens, secrets ou tokens do bot em logs.
- Não use OAuth para solicitar senhas; o usuário autoriza apenas na página oficial `discord.com`.

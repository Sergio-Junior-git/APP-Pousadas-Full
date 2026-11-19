# Pousada Viva — aplicativo de gestão

Aplicativo React Native com Expo para a API FastAPI existente em `../back-end`.

## Executar

1. Suba a API na porta 8001, conforme o README do backend, e carregue os dados de demonstração com `python seed_all.py`.
2. Copie `.env.example` para `.env` e ajuste `EXPO_PUBLIC_API_URL`.
   - Android Emulator: `http://10.0.2.2:8001`
   - iOS Simulator: `http://localhost:8001`
   - Celular físico: `http://<IP-da-máquina-na-rede>:8001`
3. Instale as dependências e inicie:

```sh
npm.cmd install
npm.cmd start
```

Use `npx expo start --android`, `--ios` ou `--web` para abrir uma plataforma específica. O login padrão do seed é `admin` / `admin123`.

## Testar em um celular na rede local (Windows)

O arquivo `.env` deste projeto já aponta para `http://192.168.101.5:8001`, o IPv4 do computador encontrado agora. O celular precisa estar conectado ao Wi-Fi do mesmo roteador que liga o computador. Se o IP mudar, rode `ipconfig`, localize o IPv4 do adaptador ativo e atualize `EXPO_PUBLIC_API_URL` em `.env`. A API precisa escutar em `0.0.0.0` para aceitar conexões do celular.

1. Em um terminal, inicie a API local com SQLite:

```powershell
cd "C:\Faculdade\Projetos dionesio\back-end"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed_all.py
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Mantenha esse terminal aberto. Confirme no computador que `http://localhost:8001/health` mostra `{"status":"ok"}`. Se o Firewall do Windows perguntar, permita Python/Uvicorn na rede privada.

2. Em outro terminal, inicie o Expo:

```powershell
cd "C:\Faculdade\Projetos dionesio\front-end"
npm.cmd install
npm.cmd start
```

3. Instale o **Expo Go** no celular, conecte-o ao mesmo Wi-Fi, escaneie o QR exibido pelo Expo e abra o projeto. No Android, use o leitor de QR dentro do Expo Go; no iPhone, use a câmera. Se o QR não conectar, pare o Expo com `Ctrl+C` e tente `npx.cmd expo start --tunnel`.

O app está no SDK 58, compatível com o Expo Go que suporta essa versão. Se você alterar o endereço do `.env`, encerre o servidor Expo e rode `npm.cmd start` de novo para carregar a variável atualizada. O usuário seed padrão é `admin` e a senha padrão é `admin123`.

## Áreas incluídas

- Login JWT persistido no dispositivo e consulta do usuário autenticado.
- Painel com ocupação, disponibilidade, chegadas, saídas, alertas de governança e receita mensal.
- Reservas: listagem, pesquisa, criação com seleção de hóspede/quarto, check-in, check-out, cancelamento e registro de pagamento.
- Hóspedes: pesquisa e cadastro.
- Quartos: mapa visual de status, capacidade e diária.
- Operação: iniciar/concluir limpeza e abrir/resolver chamados de manutenção.
- Financeiro: pagamentos e consumos, com estorno para os perfis autorizados.
- Mais: páginas independentes de relatórios, tipos de quarto, equipe e configurações de conta.
- Navegação inferior simplificada, menu por módulos e suporte a safe areas do Android/iOS.

O backend aplica as permissões do usuário e valida datas, disponibilidade, saldo e transições de status. A mensagem de erro da API é apresentada no app.

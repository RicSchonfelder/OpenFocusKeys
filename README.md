# OpenFocusKeys

Exibe atalhos de teclado do programa em foco em um overlay na segunda tela (ou em modo widget). Fica ao fundo — não rouba o foco e outras janelas podem cobri-lo.

## Requisitos

- Windows + Python 3.10+ com tkinter (incluído no instalador padrão)
- Sem dependências externas (apenas stdlib: ctypes, tkinter, json)

## Como usar

1. Execute `start.vbs` (duplo clique, sem janela de terminal) ou `pythonw app.py`
2. Os atalhos mudam conforme o programa em foco (detecção por nome do .exe)
3. Detecta o opencode rodando dentro do terminal (cmd/PowerShell/Windows Terminal/wezterm/alacritty)
4. Fechar: menu ☰ → Fechar

## Janela

- **Mover**: arraste pela barra do topo (posição memorizada)
- **Redimensionar**: arraste o canto ◢ (tamanho memorizado)
- **Rolagem**: roda do mouse sobre o painel (requer "rolagem de janelas inativas" ativo — padrão do Windows 10/11)
- **Modos**: tela cheia (segundo monitor) ou widget compacto — via menu ☰ → Configurações
- Configurações: tema claro/escuro, esquemas de cores, opacidade, tamanho da fonte, sempre no topo
- Tooltip: passe o mouse no (i) de cada atalho para ver a explicação

## Atalhos mapeados

Edite `shortcuts.json`. A chave é o nome do `.exe` (minúsculo); `_default` é o fallback.

Incluídos: Chrome, Edge, Firefox, VS Code, Visual Studio, Explorer, Notepad, Notepad++, Windows Terminal, cmd, PowerShell, opencode (54 atalhos), Slack, Discord, Spotify, Excel, Word, PowerPoint, Photoshop.

## Arquivos

| Arquivo | Função |
|---|---|
| `app.py` | aplicação (ctypes + tkinter) |
| `shortcuts.json` | banco de atalhos por programa |
| `start.vbs` | launcher oculto (pythonw) |
| `settings.json` | preferências (gerado em runtime, fora do git) |

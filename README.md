# OpenFocusKeys

[![tests](https://github.com/RicSchonfelder/OpenFocusKeys/actions/workflows/tests.yml/badge.svg)](https://github.com/RicSchonfelder/OpenFocusKeys/actions/workflows/tests.yml)

Exibe atalhos de teclado do programa em foco em um overlay (segunda tela ou widget). Fica ao fundo — não rouba o foco e outras janelas podem cobri-lo.

Multiplataforma: **Windows, Linux (X11) e macOS**.

## Requisitos

- Python 3.10+ com tkinter
  - Windows: instalador do python.org (já inclui tkinter)
  - Linux: `sudo apt install python3 python3-tk x11-xserver-utils` (xprop/xrandr; ou o equivalente da sua distro)
  - macOS: `brew install python-tk`
- Sem dependências Python externas (apenas stdlib)

## Como usar

| Sistema | Comando |
|---|---|
| Windows | `start.vbs` (duplo clique, sem terminal) ou `pythonw app.py` |
| Linux / macOS | `./start.sh` ou `python3 app.py` |

1. Os atalhos mudam conforme o programa em foco
2. Detecta o opencode rodando dentro do terminal (cmd/PowerShell/Windows Terminal/wezterm/alacritty/tmux/kitty/gnome-terminal/iTerm2...)
3. Fechar: menu ☰ → Fechar

## Janela

- **Mover**: arraste pela barra do topo (posição memorizada)
- **Redimensionar**: arraste o canto ◢ (tamanho memorizado)
- **Rolagem**: roda do mouse sobre o painel (no Windows: requer "rolagem de janelas inativas" ativo — padrão 10/11)
- **Modos**: tela cheia (segundo monitor) ou widget compacto — menu ☰ → Configurações
- Configurações: tema claro/escuro, esquemas de cores, opacidade, tamanho da fonte, sempre no topo
- Tooltip: passe o mouse no (i) de cada atalho para ver a explicação

## Detecção por plataforma

| Plataforma | Mecanismo |
|---|---|
| Windows | janela em primeiro plano via Win32 (ctypes puro) |
| Linux (X11) | `xprop` (`_NET_ACTIVE_WINDOW`/`_NET_WM_PID`) + `/proc` |
| macOS | AppleScript (System Events) + `ps` |

Nomes de app no macOS/Linux (ex.: "Google Chrome", "gnome-terminal") são resolvidos para as seções do `shortcuts.json` via `APP_ALIASES` em `app.py` — adicione aliases lá se algum app não for reconhecido.

## Limitações conhecidas

- Linux: X11 apenas (Wayland não suportado — sem API global de janela ativa); "ficar ao fundo" é best-effort (`_NET_WM_STATE_BELOW`, depende do gerenciador de janelas)
- macOS: sem equivalente nativo de "ficar ao fundo" — a janela flutua; multi-monitor via CoreGraphics
- A suíte automatizada (sem GUI) cobre detecção de processos, monitores, lógica de teclas/clamp e integridade do `shortcuts.json`; o resto da interface é validado manualmente

## Atalhos mapeados

Edite `shortcuts.json`. A chave é o nome do `.exe` (minúsculo); `_default` é o fallback.

Incluídos: Chrome, Edge, Firefox, VS Code, Visual Studio, Explorer, Notepad, Notepad++, Windows Terminal, cmd, PowerShell, opencode (54 atalhos), Slack, Discord, Spotify, Excel, Word, PowerPoint, Photoshop.

## Testes

```
python -m unittest discover -s tests -v
```

O CI roda a suíte em **windows-latest, macos-latest e ubuntu-latest** a cada push (GitHub Actions).

## Arquivos

| Arquivo | Função |
|---|---|
| `app.py` | aplicação (ctypes + tkinter, camada por-OS) |
| `shortcuts.json` | banco de atalhos por programa |
| `start.vbs` / `start.sh` | launchers (Windows / Linux e macOS) |
| `tests/test_app.py` | suíte de testes (unittest, sem GUI) |
| `settings.json` | preferências (gerado em runtime, fora do git) |

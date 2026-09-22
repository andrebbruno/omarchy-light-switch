# Light Switch para o Omarchy

Um tema claro de dia e um escuro à noite, sozinho. É o
[PowerToys Light Switch](https://learn.microsoft.com/windows/powertoys/light-switch) portado
para o [Omarchy](https://omarchy.org) — pelo relógio ou pelo nascer do sol de onde você está.

*[Read in English](README.md)*

```bash
omarchy-light-switch setup      # escolhe os dois temas e o horário
omarchy-light-switch enable     # deixa rodando
omarchy-light-switch toggle     # troca agora, sem mexer no agendamento
```

## Como ele decide

**Pelo relógio** — dois horários que você escolhe. Um período claro que atravessa a
meia-noite também funciona, para quem quer o tema claro à noite.

**Pelo sol** — nascer e pôr do sol calculados para as suas coordenadas. Sem rede, sem chave
de API, sem serviço de localização: é a equação do nascer do sol da NOAA, com precisão de
cerca de um minuto, e ela reaproveita a localização que o Omarchy já tem para o painel do
clima, se você tiver definido uma. Um `offset_minutes` desloca os dois momentos, para quem
acorda antes do sol.

De qualquer forma, o `apply` é idempotente: ele pergunta qual tema deveria estar ativo e não
faz nada quando essa já é a resposta. É isso que o torna seguro para rodar em um timer.

## Quais temas são claros?

Os próprios temas dizem — o `colors.toml` de todo tema do Omarchy traz `mode = "light"` ou
`mode = "dark"`, então o menu de configuração oferece os certos sem uma lista que ficaria
desatualizada no instante em que você instalasse um tema novo.

## Instalação

### Arch / Omarchy

```bash
sudo pacman -U omarchy-light-switch-*-any.pkg.tar.zst   # dos Releases
omarchy-light-switch setup
omarchy-light-switch enable
```

O `enable` liga um timer de usuário que confere a cada 15 minutos e de novo depois de cada
retorno da suspensão — então um notebook que estava dormindo no pôr do sol acorda já certo.

Um atalho para a troca manual, no `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + ALT + T", "Claro/escuro", "omarchy-light-switch toggle")
```

### Em outras distros

`pipx install git+https://github.com/andrebbruno/omarchy-light-switch`. Ele aciona o
`omarchy-theme-set`, então quer o Omarchy; a matemática do nascer do sol serve em qualquer
lugar.

## Comandos

```
omarchy-light-switch                 o menu
omarchy-light-switch setup           escolhe os temas e o agendamento
omarchy-light-switch apply           troca para o tema certo para agora
omarchy-light-switch toggle          troca para o outro
omarchy-light-switch status          o que está ativo e quando muda
omarchy-light-switch enable|disable  o timer
omarchy-light-switch location "-23.55, -46.63"
```

`~/.config/omarchy-light-switch/config.json`:

```json
{
  "light": "Catppuccin Latte",
  "dark": "Tokyo Night",
  "mode": "sun",
  "latitude": -23.55,
  "longitude": -46.63,
  "offset_minutes": -30
}
```

## ⚠️ Um timer do systemd não herda nada da sua sessão

Isso não é uma nota de rodapé, é o bug em torno do qual esta ferramenta foi escrita: o
`OMARCHY_PATH` é definido pela sessão do Hyprland, um timer de usuário não o recebe, e o
`omarchy-theme-set` sem ele responde que **todos** os temas não existem. Aqui ele é preenchido
antes da troca do tema — é por isso que a troca agendada funciona, e não só a que você roda
no terminal.

## Desenvolvimento

```bash
python -m pytest tests -q     # 65 testes, sem precisar esperar o relógio
```

A equação do nascer do sol (`olightswitch/sun.py`) e a decisão de qual tema deve estar ativo
(`olightswitch/schedule.py`) são funções puras sobre um horário e um lugar, então os testes
conferem o nascer do sol do solstício em Londres ao minuto, os dias de doze horas no equador,
o dia polar, a noite polar e um período claro que atravessa a meia-noite.

## Licença

MIT © Andre Bruno

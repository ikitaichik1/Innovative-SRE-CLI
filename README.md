# Innovative-SRE-CLI
**I've used Python with Click instead of Argsparse to pass variables,<br>**
**Click comes with some nice features, eg. Automatically generated help messages**

This tool supports auto-complete by pressing tab, can be changed at line 46 in the code <br>
readline.parse_and_bind("tab: complete")

Requirements:
```bash
pip install -r requirements.txt
or
pip install click logging kubernetes readline
```
---
```bash
Usage: sre.py [OPTIONS] COMMAND [ARGS]...

  Home Assignment: Innovative SRE CLI

Options:
  --help  Show this message and exit.

Commands:
  diagnostic
  info
  list
  logs
  rollout
  scale
```




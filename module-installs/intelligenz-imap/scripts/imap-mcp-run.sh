#!/bin/sh
# Startet den IMAP/SMTP-MCP-Server (ai-zerolab/mcp-email-server) und gibt ihm die
# Zugangsdaten aus der .env mit.
#
# WARUM: Claude Code startet uvx aus seinem Cache-Verzeichnis, NICHT aus dem
# Projekt-Root. Der Server findet die .env darum nicht selbst. Dieser Wrapper
# exportiert NUR die MCP_EMAIL_SERVER_*-Zeilen aus der .env (nicht den Rest) und
# startet dann uvx.
#
# INSTALL: __WORKSPACE__ durch den absoluten Workspace-Pfad ersetzen, chmod +x,
# und in der .mcp.json "command" auf diese Datei zeigen lassen,
# "args" = ["mcp-email-server@latest","stdio"].
#
# Mehrere Konten: ueber die TOML-Config des Servers
# (~/.config/zerolib/mcp_email_server/config.toml) statt ueber Env.
ENV_FILE="__WORKSPACE__/.env"
if [ -f "$ENV_FILE" ]; then
  while IFS= read -r line; do
    case "$line" in
      MCP_EMAIL_SERVER_*=*) export "$line" ;;
    esac
  done < "$ENV_FILE"
fi
exec uvx "$@"

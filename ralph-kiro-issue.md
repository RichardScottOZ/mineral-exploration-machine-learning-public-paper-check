# Agent configs need to be JSON, not YAML

## Problem

The agent configurations in `.kiro/agents/` are YAML files (`.yaml` extension), but Kiro CLI expects JSON files (`.json` extension) with a specific schema. Running `kiro-cli chat --agent ralph-clarify` produces:

```
Error: no agent with name ralph-clarify found. Falling back to user specified default
```

Validating the YAML files confirms the issue:

```bash
$ kiro-cli agent validate --path .kiro/agents/ralph-clarify.yaml
Error: Json supplied at .kiro/agents/ralph-clarify.yaml is invalid: expected ident at line 1 column 2
```

## Expected Format

Kiro CLI expects `.json` files matching this schema (from `~/.kiro/agents/agent_config.json.example`):

```json
{
  "name": "ralph-clarify",
  "description": "Comprehensive requirements discovery via iterative questioning",
  "prompt": "You are the Ralph Clarify agent...",
  "mcpServers": {},
  "tools": ["*"],
  "toolAliases": {},
  "allowedTools": [],
  "resources": [
    "file://README.md",
    "file://clarify-session.md"
  ],
  "hooks": {},
  "toolsSettings": {},
  "useLegacyMcpJson": false,
  "model": null
}
```

Key differences from the current YAML configs:
- File extension must be `.json`
- The `instructions` field should be `prompt`
- `tools` is an array of tool names (e.g. `["*"]` for all tools), not the YAML list format
- `resources` uses `file://` URIs to reference context files
- Additional required fields: `mcpServers`, `toolAliases`, `allowedTools`, `hooks`, `toolsSettings`, `useLegacyMcpJson`, `model`

## Files Affected

- `.kiro/agents/ralph-clarify.yaml` → needs to become `.json`
- `.kiro/agents/ralph-plan.yaml` → needs to become `.json`
- `.kiro/agents/lisa-plan.yaml` → needs to become `.json`
- `setup-ralph.sh` → copies YAML files, needs updating
- `README.md` → references YAML configs in documentation

## Environment

```
$ kiro-cli --version
# (tested Feb 2026)
$ kiro-cli agent list
# Only discovers .json files in .kiro/agents/
```

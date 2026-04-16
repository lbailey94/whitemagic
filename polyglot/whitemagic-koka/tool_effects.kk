// Tool Effects - MCP Tool Operations (PSR-006)
module tool_effects

effect tools
  fun dispatch(tool-name: string, params: string): string
  fun validate-params(tool-name: string, params: string): bool

fun safe-dispatch(tool-name: string, params: string): <tools> maybe<string>
  if tools/validate-params(tool-name, params) then
    Just(tools/dispatch(tool-name, params))
  else
    Nothing

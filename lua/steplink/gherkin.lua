local M = {}

-- Case-insensitive on the keyword itself (Gherkin convention is Title-case, but we
-- tolerate lowercase defensively), case-sensitive elsewhere.
local KEYWORD_PATTERNS = {
  { name = "given", pattern = "^%s*[Gg]iven%s+(.*)$" },
  { name = "when", pattern = "^%s*[Ww]hen%s+(.*)$" },
  { name = "then", pattern = "^%s*[Tt]hen%s+(.*)$" },
  { name = "and", pattern = "^%s*[Aa]nd%s+(.*)$" },
  { name = "but", pattern = "^%s*[Bb]ut%s+(.*)$" },
}

local BOUNDARY_PATTERN =
  "^%s*[Ss]cenario%s+[Oo]utline%s*:" ..
  "\1" ..
  "^%s*[Ss]cenario%s+[Tt]emplate%s*:" ..
  "\1" ..
  "^%s*[Ss]cenario%s*:" ..
  "\1" ..
  "^%s*[Bb]ackground%s*:" ..
  "\1" ..
  "^%s*[Ff]eature%s*:"

local function get_line(bufnr, lnum)
  return (vim.api.nvim_buf_get_lines(bufnr, lnum - 1, lnum, false)[1]) or ""
end

local function match_keyword_line(line)
  for _, kw in ipairs(KEYWORD_PATTERNS) do
    local rest = line:match(kw.pattern)
    if rest then
      return kw.name, vim.trim(rest)
    end
  end
  return nil, nil
end

local function is_scenario_boundary(line)
  for pattern in vim.gsplit(BOUNDARY_PATTERN, "\1", { plain = true }) do
    if line:match(pattern) then
      return true
    end
  end
  return false
end

--- Resolve the Given/When/Then keyword and step text for the step at `lnum` (1-indexed),
--- following And/But upward to the nearest real keyword if needed.
--- Returns `{ keyword, text, line }, nil` on success, or `nil, error_message` on failure.
function M.resolve_step(bufnr, lnum)
  local line = get_line(bufnr, lnum)
  local keyword, text = match_keyword_line(line)
  if not keyword then
    return nil, "cursor is not on a Given/When/Then/And/But step line"
  end

  if keyword ~= "and" and keyword ~= "but" then
    return { keyword = keyword, text = text, line = lnum }, nil
  end

  local i = lnum - 1
  while i >= 1 do
    local candidate = get_line(bufnr, i)
    if is_scenario_boundary(candidate) then
      return nil, "reached a Scenario/Feature boundary before finding a Given/When/Then"
    end
    local candidate_kw = match_keyword_line(candidate)
    if candidate_kw == "given" or candidate_kw == "when" or candidate_kw == "then" then
      return { keyword = candidate_kw, text = text, line = lnum }, nil
    end
    i = i - 1
  end

  return nil, "reached the top of the buffer before finding a Given/When/Then"
end

return M

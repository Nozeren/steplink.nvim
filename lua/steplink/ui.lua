local M = {}

local config = require("steplink.config")

local function relpath(path, root)
  if root and path:sub(1, #root + 1) == root .. "/" then
    return path:sub(#root + 2)
  end
  return path
end

function M.jump_to(match)
  vim.cmd("normal! m'")
  local ok, err = pcall(vim.cmd.edit, vim.fn.fnameescape(match.file))
  if not ok then
    vim.notify("steplink: failed to open " .. match.file .. ": " .. err, vim.log.levels.ERROR)
    return
  end

  local line_count = vim.api.nvim_buf_line_count(0)
  local target_line = match.line
  if target_line < 1 or target_line > line_count then
    vim.notify(
      string.format(
        "steplink: %s only has %d lines, expected line %d - jumping to end of file instead (file may be stale)",
        match.file,
        line_count,
        target_line
      ),
      vim.log.levels.WARN
    )
    target_line = math.max(1, math.min(target_line, line_count))
  end

  vim.api.nvim_win_set_cursor(0, { target_line, 0 })
  vim.cmd("normal! zz")
end

-- default label for step-definition matches ({file, line, decorator, function}), used
-- by the forward (feature -> step) direction
local function step_label(m)
  return string.format("@%s %s(...)", m.decorator, m["function"])
end

-- label for scenario matches ({file, line, scenario, text}), used by the reverse
-- (step -> scenarios) direction
local function scenario_label(m)
  if m.scenario and m.scenario ~= "" then
    return m.scenario
  end
  return m.text
end

M.step_label = step_label
M.scenario_label = scenario_label

function M.to_quickfix(matches, ctx, label)
  label = label or step_label
  local qf = {}
  for _, m in ipairs(matches) do
    table.insert(qf, {
      filename = m.file,
      lnum = m.line,
      text = label(m),
    })
  end
  vim.fn.setqflist({}, "r", { title = "steplink matches", items = qf })
  vim.cmd("copen")
end

local function has_fzf_lua()
  return (pcall(require, "fzf-lua"))
end

function M.select_with_fzf(matches, ctx, label)
  label = label or step_label
  local fzf_lua = require("fzf-lua")
  local fzf_actions = require("fzf-lua.actions")

  local items = {}
  for _, m in ipairs(matches) do
    -- "path:line: text" - fzf-lua's own entry format (see providers/quickfix.lua),
    -- parsed back into file+line by fzf-lua.path.entry_to_file for both the builtin
    -- previewer and the default open action
    table.insert(items, string.format("%s:%d: %s", relpath(m.file, ctx.repo_root), m.line, label(m)))
  end

  fzf_lua.fzf_exec(items, {
    prompt = "steplink matches> ",
    cwd = ctx.repo_root,
    previewer = "builtin",
    actions = {
      ["default"] = fzf_actions.file_edit_or_qf,
    },
  })
end

function M.select_match(matches, ctx, label)
  label = label or step_label
  local mode = config.options.ambiguous_ui
  if mode == "auto" then
    mode = has_fzf_lua() and "fzf" or "select"
  end

  if mode == "fzf" and has_fzf_lua() then
    M.select_with_fzf(matches, ctx, label)
    return
  end

  if mode == "quickfix" or #matches > config.options.ambiguous_quickfix_threshold then
    M.to_quickfix(matches, ctx, label)
    return
  end

  local items = {}
  for _, m in ipairs(matches) do
    table.insert(items, string.format("%s:%d  (%s)", relpath(m.file, ctx.repo_root), m.line, label(m)))
  end

  vim.ui.select(items, { prompt = "Multiple matches:" }, function(_, idx)
    if idx then
      M.jump_to(matches[idx])
    end
  end)
end

function M.handle_result(result, ctx)
  if result.status == "match" then
    M.jump_to(result.match)
  elseif result.status == "ambiguous" then
    M.select_match(result.matches, ctx, step_label)
  elseif result.status == "no_match" then
    vim.notify(
      string.format(
        "steplink: no step definition found for %q (searched %d files)",
        result.resolved_step_text or "",
        #(result.searched_files or {})
      ),
      vim.log.levels.WARN
    )
  elseif result.status == "error" then
    vim.notify("steplink: " .. (result.message or "unknown error"), vim.log.levels.ERROR)
  else
    vim.notify("steplink: unrecognized resolver response", vim.log.levels.ERROR)
  end
end

function M.handle_scenario_result(result, ctx)
  if result.status == "found" then
    if #result.matches == 1 then
      M.jump_to(result.matches[1])
    else
      M.select_match(result.matches, ctx, scenario_label)
    end
  elseif result.status == "no_match" then
    vim.notify(
      string.format(
        "steplink: no scenario uses %s() (searched %d feature files)",
        result.step_function or "this step",
        result.searched_feature_file_count or 0
      ),
      vim.log.levels.WARN
    )
  elseif result.status == "error" then
    vim.notify("steplink: " .. (result.message or "unknown error"), vim.log.levels.ERROR)
  else
    vim.notify("steplink: unrecognized resolver response", vim.log.levels.ERROR)
  end
end

-- label for orphan candidates ({file, line, function, decorator, pattern}), used by the
-- repo-wide :StepLinkOrphans scan
local function orphan_label(m)
  return string.format("@%s %s(...)  %s", m.decorator, m["function"], m.pattern)
end

M.orphan_label = orphan_label

function M.handle_orphans_result(result, ctx)
  if result.status ~= "ok" then
    vim.notify("steplink: " .. (result.message or "unknown error"), vim.log.levels.ERROR)
    return
  end

  if #result.orphans == 0 then
    vim.notify(
      string.format("steplink: no orphaned steps found (checked %d step definitions)", result.checked),
      vim.log.levels.INFO
    )
    return
  end

  M.to_quickfix(result.orphans, ctx, orphan_label)
  vim.notify(
    string.format(
      "steplink: %d possibly orphaned step(s) out of %d checked - review before deleting anything",
      #result.orphans,
      result.checked
    ),
    vim.log.levels.WARN
  )
end

function M.notify_process_error(result)
  local msg = "steplink: python resolver failed (exit " .. tostring(result.code) .. ")"
  if result.stderr and result.stderr ~= "" then
    msg = msg .. "\n" .. result.stderr
  end
  vim.notify(msg, vim.log.levels.ERROR)
end

return M

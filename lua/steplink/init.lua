local M = {}

local function create_commands()
  vim.api.nvim_create_user_command("StepLinkGoto", function()
    M.goto_step(false)
  end, { desc = "Jump to the pytest-bdd step definition under the cursor" })

  vim.api.nvim_create_user_command("StepLinkGotoDebug", function()
    M.goto_step(true)
  end, { desc = "Like :StepLinkGoto, but prints the full resolver response" })

  vim.api.nvim_create_user_command("StepLinkScenarios", function()
    M.find_scenarios(false)
  end, { desc = "Find every scenario step that uses the step definition under the cursor" })

  vim.api.nvim_create_user_command("StepLinkScenariosDebug", function()
    M.find_scenarios(true)
  end, { desc = "Like :StepLinkScenarios, but prints the full resolver response" })

  vim.api.nvim_create_user_command("StepLinkOrphans", function()
    M.find_orphans()
  end, { desc = "Repo-wide scan for step definitions no scenario resolves to" })
end

function M.setup(opts)
  require("steplink.config").setup(opts)
  create_commands()
end

function M.goto_step(debug_mode)
  local gherkin = require("steplink.gherkin")
  local bridge = require("steplink.bridge")
  local ui = require("steplink.ui")
  local util = require("steplink.util")

  local bufnr = vim.api.nvim_get_current_buf()
  local lnum = vim.api.nvim_win_get_cursor(0)[1]

  local step, err = gherkin.resolve_step(bufnr, lnum)
  if not step then
    vim.notify("steplink: " .. err, vim.log.levels.WARN)
    return
  end

  local feature_file = vim.api.nvim_buf_get_name(bufnr)
  local repo_root = util.find_repo_root(feature_file)
  if not repo_root then
    vim.notify("steplink: could not detect repo root above " .. feature_file, vim.log.levels.ERROR)
    return
  end

  bridge.resolve({
    feature_file = feature_file,
    repo_root = repo_root,
    step_text = step.text,
    keyword = step.keyword,
    step_line = step.line,
  }, function(result)
    local ok, decoded = pcall(vim.json.decode, result.stdout or "")
    if not ok or type(decoded) ~= "table" then
      ui.notify_process_error(result)
      return
    end

    if debug_mode then
      vim.notify(vim.inspect(decoded), vim.log.levels.INFO)
    end

    ui.handle_result(decoded, { repo_root = repo_root })
  end)
end

function M.find_scenarios(debug_mode)
  local bridge = require("steplink.bridge")
  local ui = require("steplink.ui")
  local util = require("steplink.util")

  local bufnr = vim.api.nvim_get_current_buf()
  local lnum = vim.api.nvim_win_get_cursor(0)[1]
  local step_file = vim.api.nvim_buf_get_name(bufnr)

  local repo_root = util.find_repo_root(step_file)
  if not repo_root then
    vim.notify("steplink: could not detect repo root above " .. step_file, vim.log.levels.ERROR)
    return
  end

  bridge.find_scenarios({
    step_file = step_file,
    cursor_line = lnum,
    repo_root = repo_root,
  }, function(result)
    local ok, decoded = pcall(vim.json.decode, result.stdout or "")
    if not ok or type(decoded) ~= "table" then
      ui.notify_process_error(result)
      return
    end

    if debug_mode then
      vim.notify(vim.inspect(decoded), vim.log.levels.INFO)
    end

    ui.handle_scenario_result(decoded, { repo_root = repo_root })
  end)
end

function M.find_orphans()
  local bridge = require("steplink.bridge")
  local ui = require("steplink.ui")
  local util = require("steplink.util")

  local bufnr = vim.api.nvim_get_current_buf()
  local path = vim.api.nvim_buf_get_name(bufnr)

  local repo_root = util.find_repo_root(path)
  if not repo_root then
    vim.notify("steplink: could not detect repo root above " .. path, vim.log.levels.ERROR)
    return
  end

  vim.notify("steplink: scanning the repo for orphaned step definitions...", vim.log.levels.INFO)

  bridge.find_orphans({ repo_root = repo_root }, function(result)
    local ok, decoded = pcall(vim.json.decode, result.stdout or "")
    if not ok or type(decoded) ~= "table" then
      ui.notify_process_error(result)
      return
    end

    ui.handle_orphans_result(decoded, { repo_root = repo_root })
  end)
end

return M

if vim.b.did_bdd_find_scenarios_ftplugin then
  return
end
vim.b.did_bdd_find_scenarios_ftplugin = true

-- only in files that look like pytest-bdd step definitions - never in unrelated
-- Python files elsewhere on the machine
local path = vim.api.nvim_buf_get_name(0)
if not path:match("/steps/") then
  return
end

local config_ok, config = pcall(require, "steplink.config")
if not config_ok or not config.options.keymap then
  return
end

local util_ok, util = pcall(require, "steplink.util")
if not util_ok or not util.find_repo_root(path) then
  return
end

vim.keymap.set("n", config.options.keymap, "<cmd>StepLinkScenarios<cr>", {
  buffer = true,
  desc = "Find scenarios using the pytest-bdd step under the cursor",
})

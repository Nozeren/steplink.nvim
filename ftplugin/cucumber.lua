if vim.b.did_steplink_ftplugin then
  return
end
vim.b.did_steplink_ftplugin = true

local config = require("steplink.config")
if config.options.keymap then
  vim.keymap.set("n", config.options.keymap, "<cmd>StepLinkGoto<cr>", {
    buffer = true,
    desc = "Go to pytest-bdd step definition",
  })
end

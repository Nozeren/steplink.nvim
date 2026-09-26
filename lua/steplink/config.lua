local M = {}

M.defaults = {
  python_path = nil, -- nil = auto-resolve <repo_root>/.venv/bin/python3, falling back to "python3"
  repo_root_markers = { ".git", "pytest.ini" },
  -- one key, both directions: :StepLinkGoto in .feature buffers, :StepLinkScenarios in
  -- .py buffers whose path contains "/steps/" - a buffer is always exactly one
  -- filetype, so there's no real conflict in sharing the same key. false to disable.
  keymap = "<leader>ss",
  ambiguous_ui = "auto", -- "auto" (fzf-lua if installed, else "select") | "fzf" | "select" | "quickfix"
  ambiguous_quickfix_threshold = 4, -- only applies to the "select" fallback, not "fzf"
  debug = false,
}

M.options = vim.deepcopy(M.defaults)

function M.setup(opts)
  M.options = vim.tbl_deep_extend("force", vim.deepcopy(M.defaults), opts or {})
end

return M

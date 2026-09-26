local M = {}

function M.find_repo_root(start_path)
  -- reject virtual/scheme buffer names (health://, term://, ...): vim.fs.dirname()
  -- on those yields a bogus relative-looking path that upward search would silently
  -- resolve against cwd instead of failing
  if start_path == "" or start_path:match("^%a[%w+.-]*://") then
    return nil
  end
  local config = require("steplink.config")
  local found = vim.fs.find(config.options.repo_root_markers, {
    path = vim.fs.dirname(start_path),
    upward = true,
  })[1]
  if not found then
    return nil
  end
  return vim.fs.dirname(found)
end

function M.python_path(repo_root)
  local config = require("steplink.config")
  if config.options.python_path then
    return config.options.python_path
  end
  if repo_root then
    local venv_python = repo_root .. "/.venv/bin/python3"
    if vim.uv.fs_stat(venv_python) then
      return venv_python
    end
  end
  return "python3"
end

return M

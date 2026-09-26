local M = {}

local util = require("steplink.util")

--- Directory containing the `steplink` python package (<plugin_root>/python).
--- Passed as `-m`'s cwd so Python's own sys.path handling finds the package.
function M.plugin_python_dir()
  local source = debug.getinfo(1, "S").source:sub(2)
  local plugin_root = vim.fn.fnamemodify(source, ":h:h:h")
  return plugin_root .. "/python"
end

--- Run `python -m <module> <args...>`, cwd set to the plugin's python/ dir.
--- callback receives the raw vim.system() result (async).
function M.run(module, args, repo_root, callback)
  local python = util.python_path(repo_root)
  local cmd = { python, "-m", module }
  vim.list_extend(cmd, args)

  vim.system(cmd, { text = true, cwd = M.plugin_python_dir() }, function(result)
    vim.schedule(function()
      callback(result)
    end)
  end)
end

--- opts: { feature_file, repo_root, step_text, keyword, step_line }
function M.resolve(opts, callback)
  M.run("steplink.resolver", {
    "--feature-file",
    opts.feature_file,
    "--step-text",
    opts.step_text,
    "--keyword",
    opts.keyword,
    "--repo-root",
    opts.repo_root,
    "--step-line",
    tostring(opts.step_line),
  }, opts.repo_root, callback)
end

--- opts: { step_file, cursor_line, repo_root } - the reverse direction: from a step
--- definition, find the scenarios that use it.
function M.find_scenarios(opts, callback)
  M.run("steplink.find_scenarios", {
    "--step-file",
    opts.step_file,
    "--cursor-line",
    tostring(opts.cursor_line),
    "--repo-root",
    opts.repo_root,
  }, opts.repo_root, callback)
end

--- opts: { repo_root } - repo-wide scan for step definitions no scenario resolves to.
function M.find_orphans(opts, callback)
  M.run("steplink.find_orphans", {
    "--repo-root",
    opts.repo_root,
  }, opts.repo_root, callback)
end

return M

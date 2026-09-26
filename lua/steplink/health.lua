local M = {}

local config = require("steplink.config")
local util = require("steplink.util")
local bridge = require("steplink.bridge")

local function current_repo_root()
  local root = util.find_repo_root(vim.api.nvim_buf_get_name(0))
  if root then
    return root
  end
  return util.find_repo_root(vim.uv.cwd() .. "/.")
end

function M.check()
  vim.health.start("steplink")

  local repo_root = current_repo_root()
  if repo_root then
    vim.health.ok("repo root detected: " .. repo_root)
  else
    vim.health.error(
      "could not detect a repo root (looked upward for: " .. table.concat(config.options.repo_root_markers, ", ") .. ")"
    )
    return
  end

  local python = util.python_path(repo_root)
  if vim.fn.executable(python) == 1 then
    vim.health.ok("python interpreter found: " .. python)
  else
    vim.health.error("python interpreter not found/executable: " .. python)
    return
  end

  local function check_run(cmd, opts, ok_msg, err_msg)
    local result = vim.system(cmd, opts or { text = true }):wait()
    if result.code == 0 then
      vim.health.ok(ok_msg)
    else
      vim.health.error(err_msg, { result.stderr })
    end
  end

  check_run(
    { python, "-c", "import pytest_bdd" },
    { text = true },
    "`import pytest_bdd` succeeds",
    "`import pytest_bdd` failed"
  )

  check_run(
    { python, "-c", "from pytest_bdd.parsers import re" },
    { text = true },
    "`from pytest_bdd.parsers import re` succeeds",
    "`from pytest_bdd.parsers import re` failed"
  )

  check_run(
    { python, "-m", "steplink.resolver", "--help" },
    { text = true, cwd = bridge.plugin_python_dir() },
    "steplink.resolver is importable and runs",
    "steplink.resolver failed to run"
  )
end

return M

# Example workflow

Open your product's own repo in Codex and use `$reqmap` to initialize there.

Recommended requirements size: one cohesive user-observable capability, not a page, code file, sprint, or vague epic. If a user gives several independent capabilities, record several requirements and only link them where product behavior justifies it.

The generated `.reqmap/INDEX.md` is the reading entry point across Codex sessions. Do not hand-edit the generated index or feature pages. Product context is edited directly in `.reqmap/product.md`; requirement metadata is modified through the CLI.
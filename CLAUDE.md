# CLAUDE.md

This file provides guidance to AI assistants (Claude and others) working with this repository.

## Repository Overview

**Repository:** hyun0609kr-spec/henry
**Status:** Newly initialized repository — no source code has been committed yet.

This document will evolve as the project grows. Update it when new technologies, conventions, or workflows are introduced.

---

## Current Repository State

The repository is currently empty (no source files, no package.json, no CI configuration). When adding initial code, follow the conventions defined in this document.

---

## Installed Claude Code Skills

### NotebookLM (`notebooklm`)

Installed at `~/.claude/skills/notebooklm` (cloned from [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill)).

Enables querying Google NotebookLM notebooks directly from Claude Code for source-grounded, citation-backed answers. Uses browser automation via Patchright.

**Prerequisites:** Chrome installed (auto-installed on first use), Google account, NotebookLM notebooks with uploaded sources.

**Key commands:**
- `"Set up NotebookLM authentication"` — one-time Google login
- `"Query this notebook about its content and add it to my library: [link]"` — smart discovery + add
- `"Ask my [notebook name] about [topic]"` — query a saved notebook

---

## Development Workflow

### Branching Strategy

- `main` / `master` — stable, production-ready code; never push directly
- `claude/<description>-<session-id>` — branches used by AI assistants for automated changes
- Feature branches should be short-lived and merged via pull requests

### Commit Messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<optional scope>): <short description>

[optional body]

[optional footer]
```

**Types:**
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation changes only
- `refactor` — code change that neither fixes a bug nor adds a feature
- `test` — adding or correcting tests
- `chore` — maintenance tasks (dependency updates, config changes)
- `ci` — changes to CI/CD configuration

**Examples:**
```
feat(auth): add JWT refresh token support
fix(api): handle null response from user endpoint
docs: add CLAUDE.md with project conventions
```

### Pull Requests

- Keep PRs focused and small; one concern per PR
- Write a clear PR description explaining the *why*, not just the *what*
- Link to any related issues

---

## Code Conventions

These conventions apply once source code is added to the repository.

### General Principles

- **Simplicity first** — write the simplest code that solves the problem
- **Avoid premature abstraction** — don't generalize until there are at least 3 concrete use cases
- **No over-engineering** — don't add features, configuration options, or error handling for scenarios that don't exist yet
- **Self-documenting code** — prefer clear naming over comments; only comment non-obvious logic

### File and Directory Layout

When initializing the project, follow this general structure (adapt to the chosen framework):

```
henry/
├── CLAUDE.md          # This file
├── README.md          # Human-facing project documentation
├── .gitignore
├── src/               # Application source code
│   ├── index.*        # Entry point
│   └── ...
├── tests/             # Test files (mirror src/ structure)
└── docs/              # Additional documentation (if needed)
```

### Language-Specific Conventions

Update this section once the tech stack is chosen.

**If using TypeScript/JavaScript:**
- Use TypeScript with strict mode enabled
- ESLint + Prettier for linting and formatting
- Avoid `any`; use proper types or `unknown`
- Prefer `const` over `let`; never use `var`

**If using Python:**
- Use `ruff` for linting and formatting
- Type hints required for all public functions
- Follow PEP 8

---

## Testing

Once a testing framework is chosen, document:
- How to run the full test suite
- How to run a single test file
- Coverage requirements (if any)
- Where test files should live

**Placeholder commands (update when tests are configured):**
```bash
# Run all tests
npm test          # Node.js
pytest            # Python

# Run a single test
npm test -- path/to/test
pytest path/to/test.py
```

---

## Common Tasks

### Setting Up the Project

```bash
# Clone the repository
git clone <repo-url>
cd henry

# Install dependencies (update once package manager is chosen)
npm install    # Node.js
pip install -e ".[dev]"  # Python
```

### Running the Application

_To be documented once the application entry point is established._

### Adding Dependencies

- Prefer widely-used, well-maintained packages
- Avoid adding a dependency for functionality that can be implemented simply in a few lines
- Lock dependency versions in lockfiles; commit lockfiles to version control

---

## AI Assistant Guidelines

### What You Should Do

- Read this file at the start of every session to understand current conventions
- Update this file when you introduce new patterns, tools, or workflows
- Follow the branching strategy: develop on `claude/<description>-<session-id>` branches
- Write commit messages following Conventional Commits format
- Prefer editing existing files over creating new ones
- Keep changes minimal and focused on what was requested

### What You Should Avoid

- Pushing directly to `main`/`master`
- Creating files or abstractions that aren't immediately needed
- Adding comments, docstrings, or type annotations to code you didn't modify
- Introducing new dependencies without a clear justification
- Leaving `TODO` comments or incomplete implementations without noting them explicitly
- Running destructive git commands (`reset --hard`, `push --force`, `clean -f`) without explicit user permission

### Handling Ambiguity

If a task is unclear:
1. State your assumptions explicitly before proceeding
2. Ask for clarification on decisions with significant consequences
3. For small, reversible decisions, proceed with the most reasonable interpretation and note what was decided

---

## Security

- Never commit secrets, tokens, API keys, or passwords
- Use environment variables for sensitive configuration; document required variables in `.env.example`
- Do not disable security-related tooling (linters, pre-commit hooks) without explicit instruction

---

## Updating This File

This file should be kept current. Update it when:
- The tech stack is decided and initialized
- New tools or workflows are adopted
- Conventions change
- CI/CD is configured
- New team members or AI sessions need onboarding context

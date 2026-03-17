# Synthesis Skills

Reusable AI agent skills built on the [Agent Skills](https://agentskills.io) open standard. Install proven methodology directly into your AI coding assistant's workflow.

## What are Synthesis Skills?

Synthesis Skills are portable, shareable instruction packages that teach AI coding assistants *how* to do things well — content creation, code review, project management, quality assurance, and more. They encode the methodology behind [synthesis coding](https://synthesiscoding.org) and [synthesis engineering](https://rajiv.com) into a format that works across AI platforms.

Each skill follows the [Agent Skills open standard](https://agentskills.io), which means they work with Claude Code, Cursor, OpenAI Codex CLI, GitHub Copilot, and other compatible tools.

## Installation

### Claude Code (CLI, VS Code, or Desktop)

Install a single skill:

```bash
claude skill install rajivpant/synthesis-skills/[skill-name]
```

Or clone the repo and symlink skills you want:

```bash
git clone https://github.com/rajivpant/synthesis-skills.git
ln -s /path/to/synthesis-skills/[skill-name] ~/.claude/skills/[skill-name]
```

### Other platforms

Skills follow the Agent Skills standard (`SKILL.md` with YAML frontmatter). Most AI coding assistants that support the standard will auto-discover skills placed in their expected directories. Consult your tool's documentation for skill installation paths.

## Available skills

Skills are organized by domain. Each skill directory contains a `SKILL.md` with instructions and optional `references/`, `scripts/`, and `assets/` subdirectories.

*Skill directories will be populated as runbooks are converted. Check back or watch the repo for updates.*

### Engineering
- Code review, PR review, multi-contributor integration

### Content creation
- Thought leadership articles, social media, blog promotion, hyperlink research

### Content enhancement
- AI content quality (detection and improvement), fact-checking, blog revitalization

### Communication
- Message condensation (the "High-Five Habit")

### Project management
- Context lifecycle, synthesis project management

### System configuration
- LLM project setup, code generation patterns

## How skills work

Skills use progressive disclosure to minimize token cost:

1. **Tier 1** (always loaded): skill name + description (~50 tokens) — used for matching
2. **Tier 2** (loaded when triggered): `SKILL.md` body (<500 lines) — the actual instructions
3. **Tier 3** (loaded on demand): reference files, scripts, assets — detailed material

When you ask your AI assistant to do something that matches a skill's description, the skill loads automatically. You can also invoke skills explicitly.

### Defaults and overrides

Public skills are self-contained — they work without any personal configuration. Each skill that involves writing or style includes a `references/voice-defaults.md` with sensible defaults.

If you have personal preferences in your `CLAUDE.md` (or equivalent configuration), skills will respect those as overrides. Your identity configuration takes precedence over skill defaults.

## Licensing

This repository uses a dual-license structure:

- **[CC0 1.0 Universal](LICENSE-CC0)** — for methodology and content skills (the majority). Use them however you want, no attribution required.
- **[Apache License 2.0](LICENSE-APACHE)** — for skills containing executable scripts or code. Standard open-source terms apply.

Each skill directory contains a `LICENSE` file indicating which license applies.

## Part of the Synthesis Engineering ecosystem

Synthesis Skills are one component of a broader methodology:

- **[Synthesis coding](https://synthesiscoding.org)** — AI-assisted software development practices
- **[Synthesis engineering](https://rajiv.com)** — the broader methodology for human-AI collaboration
- **[Agent Skills standard](https://agentskills.io)** — the open format these skills use

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing skills.

## Author

[Rajiv Pant](https://rajiv.com) — technology executive, AI practitioner, and creator of synthesis coding methodology.

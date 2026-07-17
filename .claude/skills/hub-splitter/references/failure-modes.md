# Hub Splitter — Failure Modes and Gotchas

## YAML indentation

YAML frontmatter in concept files uses TWO leading spaces before list items:
```yaml
links:
  - "first-link"
  - "second-link"
```
NOT:
```yaml
links:
    - "first-link"   # Wrong — that's 4 spaces
  - "first-link"     # Wrong — that's 2 spaces but wrong alignment
```

Use `file_read` to verify whitespace before any `file_edit` call. The YAML will silently parse wrong or fail if indentation is off.

## Orphan detection

After splitting, the sub-hub must be linked from the main hub. Run this to detect orphans:
```bash
grep -rl "slug: <sub-hub-name>" /workspace/memory/concepts/
```

If only the sub-hub file itself references its slug, it's an orphan.

## Main hub must reference sub-hub as "(sub-hub)"

The suffix "(sub-hub)" in the link description is a convention that signals to future-you that this is a sub-page, not a terminal article. Always include it.

## Link counts

Target ~30-35 links in the main hub after extraction. If the main hub still has 45+, consider a second pass with a different grouping.

## Obsidian-style links in body text

The hub's frontmatter `links:` is separate from any Obsidian-style `[[link]]` references in the markdown body. Only frontmatter links count toward the ~25-35 cap. Do not try to rewrite body text links.
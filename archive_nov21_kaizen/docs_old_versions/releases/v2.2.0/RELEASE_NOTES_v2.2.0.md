# WhiteMagic v2.2.0 Release Notes

**Released**: November 15, 2025  
**Type**: Critical Bugfix Release  
**Package Size**: 136.7 KB wheel, 158.3 KB source

## 🔥 Critical Fixes

### Frontmatter Parser Rewrite
**IMPACT**: All memories with nested YAML structures (relationships, complex metadata) were broken in v2.1.7-2.1.8.

**Problem**: Custom line-by-line parser couldn't handle multi-line YAML:
```yaml
# This was parsed WRONG:
related_to:
- filename: target.md
  type: depends_on

# Became: {'related_to': '', '- filename': 'target.md', 'type': 'depends_on'}
# Should be: {'related_to': [{'filename': 'target.md', 'type': 'depends_on'}]}
```

**Solution**: Replaced 47-line custom parser with `yaml.safe_load()`:
- ✅ Handles all YAML structures correctly
- ✅ Relationships now work end-to-end
- ✅ Simpler, more maintainable (47 lines → 8 lines)
- ✅ Fail-safe: Returns `{}` on invalid YAML instead of corrupted data

### Enum Serialization (v2.1.8)
**Problem**: RelationType enums serialized as Python objects in YAML:
```yaml
type: !!python/object/apply:whitemagic.relationships.RelationType
  - depends_on
```

**Solution**: Convert enum to string value before storage:
```yaml
type: depends_on  # Clean!
```

## Version History

- **v2.1.7** (Nov 15): Smart features (templates, relationships, auto-tagging)
- **v2.1.8** (Nov 15): Fixed enum serialization
- **v2.1.9** (skipped): Found parser bug during testing
- **v2.2.0** (Nov 15): Fixed parser bug ← **YOU ARE HERE**

## What's Fixed

✅ `whitemagic relate` creates proper relationships  
✅ `whitemagic related` shows relationships correctly  
✅ YAML files are clean and human-readable  
✅ All memories with nested structures parse correctly  
✅ Templates with complex metadata work  

## Upgrade Path

```bash
pip install --upgrade whitemagic

# Verify version
whitemagic --version  # Should show 2.2.0

# Test relationships (no files needed, creates test memories)
echo "y" | whitemagic create --title "Source" --content "Test" --type short_term
echo "y" | whitemagic create --title "Target" --content "Test" --type short_term
whitemagic list --type short_term | tail -2  # Get filenames
whitemagic relate SOURCE.md TARGET.md --type depends_on --description "Test"
whitemagic related SOURCE.md  # Should show relationship!
```

## Testing Status

- **Core Tests**: 158/160 passing (98.8%)
- **Terminal Tests**: 15/15 passing (100%)
- **Manual Verification**: ✅ All relationship commands tested
- **Regression Tests**: ✅ Added for enum and parser bugs

## Breaking Changes

None for normal usage. Only affects memories with malformed YAML (now fails safe with `{}`).

## Known Issues

None critical. Minor Whop integration test failures (optional feature).

## Migration Notes

**Existing Memories**: Memories created in v2.1.7-2.1.8 with relationships will automatically parse correctly after upgrading. No migration needed!

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Full version history
- [README.md](README.md) - Updated to v2.2.0
- [Long-term Memory](memory/long_term/20251115_193908_critical_bug_chain_v217_to_v220_release_fixes.md) - Detailed debugging session

## Special Thanks

To the testing process that caught these bugs before they impacted production users!

## Links

- PyPI: https://pypi.org/project/whitemagic/2.2.0/
- GitHub: https://github.com/lbailey94/whitemagic
- npm (MCP): https://www.npmjs.com/package/whitemagic-mcp

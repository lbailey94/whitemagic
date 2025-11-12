# WhiteMagic Troubleshooting Guide

**Common issues and solutions**

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [CLI Problems](#cli-problems)
3. [MCP Connection Issues](#mcp-connection-issues)
4. [API Server Issues](#api-server-issues)
5. [Performance Problems](#performance-problems)
6. [Data Issues](#data-issues)
7. [Error Messages Reference](#error-messages-reference)

---

## Installation Issues

### Problem: `pip install whitemagic` fails

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement whitemagic
```

**Solutions**:
1. Check Python version:
   ```bash
   python --version  # Must be 3.10+
   ```

2. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

3. Try with version specified:
   ```bash
   pip install whitemagic==2.1.3
   ```

---

### Problem: Import errors after installation

**Symptoms**:
```python
ImportError: No module named 'whitemagic'
```

**Solutions**:
1. Verify installation:
   ```bash
   pip list | grep whitemagic
   ```

2. Check you're using the right Python:
   ```bash
   which python
   python -c "import sys; print(sys.executable)"
   ```

3. Reinstall in correct environment:
   ```bash
   pip uninstall whitemagic
   pip install whitemagic[api]==2.1.3
   ```

---

### Problem: Conflicting package versions

**Symptoms**:
```
ERROR: pip's dependency resolver does not currently take into account all the packages...
```

**Solutions**:
1. Create fresh virtual environment:
   ```bash
   python -m venv fresh_env
   source fresh_env/bin/activate  # On Windows: fresh_env\Scripts\activate
   pip install whitemagic[api]==2.1.3
   ```

2. Check for conflicts:
   ```bash
   pip check
   ```

---

## CLI Problems

### Problem: `whitemagic` command not found

**Symptoms**:
```bash
whitemagic --version
# bash: whitemagic: command not found
```

**Solutions**:
1. Verify installation:
   ```bash
   pip show whitemagic
   ```

2. Check if scripts are in PATH:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc:
   export PATH="$HOME/.local/bin:$PATH"
   source ~/.bashrc
   ```

3. Use module syntax as workaround:
   ```bash
   python -m whitemagic.cli_app --version
   ```

---

### Problem: Memory file not found

**Symptoms**:
```
Error: Memory not found: filename.md
```

**Solutions**:
1. List all memories to see correct filenames:
   ```bash
   whitemagic list
   ```

2. Check the memory directory:
   ```bash
   ls -la memory/short_term/
   ls -la memory/long_term/
   ```

3. Use full filename including timestamp:
   ```bash
   whitemagic get 20251112_120000_my_memory.md
   ```

---

### Problem: Permission denied creating memories

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: 'memory/short_term/...'
```

**Solutions**:
1. Check directory permissions:
   ```bash
   ls -la memory/
   ```

2. Fix permissions:
   ```bash
   chmod 755 memory/
   chmod 755 memory/short_term/
   chmod 755 memory/long_term/
   ```

3. Check if directory is writable:
   ```bash
   touch memory/test.txt && rm memory/test.txt
   ```

---

## MCP Connection Issues

### Problem: MCP server won't connect

**Symptoms**:
- "Connection failed" in IDE
- "Server not responding"
- Red status indicator

**Solutions**:

1. **Verify Node.js path**:
   ```bash
   which node
   # Use this full path in MCP config
   ```

2. **Check index.js path**:
   ```bash
   # Global install
   ls -la /usr/local/lib/node_modules/whitemagic-mcp/dist/index.js
   
   # Local install
   ls -la /path/to/whitemagic/whitemagic-mcp/dist/index.js
   ```

3. **Verify environment variables**:
   - `WM_BASE_PATH` must exist and be absolute path
   - No typos in variable names

4. **Check IDE logs**:
   - Windsurf/Cursor: View → Output → MCP
   - Claude: Check console/logs

5. **Test manually**:
   ```bash
   node /path/to/whitemagic-mcp/dist/index.js
   # Should start without errors
   ```

---

### Problem: "Process exited with code 1"

**Symptoms**:
```
Python process exited with code 1
```

**Note**: This is **EXPECTED** during error tests (e.g., testing invalid inputs). It's not a bug!

**When it's a problem**:
- Happens on every operation
- Prevents normal functionality

**Solutions**:
1. Check Python is installed and accessible:
   ```bash
   python3 --version
   which python3
   ```

2. Verify WhiteMagic Python package is installed:
   ```bash
   python3 -c "import whitemagic; print(whitemagic.VERSION)"
   ```

3. Check IDE error logs for actual error message

---

### Problem: MCP tools not appearing in IDE

**Symptoms**:
- Connected but no WhiteMagic tools available
- AI doesn't recognize WhiteMagic commands

**Solutions**:
1. Restart IDE completely

2. Disconnect and reconnect MCP server

3. Verify server is in "Connected" state

4. Test with simple command:
   ```
   "List my memories"
   ```

5. Check MCP panel shows WhiteMagic tools (should show 7 tools, 4 resources)

---

## API Server Issues

### Problem: Server won't start

**Symptoms**:
```
ERROR: [Errno 48] Address already in use
```

**Solutions**:
1. Check if port 8000 is in use:
   ```bash
   lsof -i :8000  # macOS/Linux
   netstat -ano | findstr :8000  # Windows
   ```

2. Kill existing process:
   ```bash
   kill -9 <PID>  # macOS/Linux
   ```

3. Use different port:
   ```bash
   uvicorn whitemagic.api.app:app --port 8001
   ```

---

### Problem: Database connection errors

**Symptoms**:
```
ERROR: could not connect to server
```

**Solutions**:
1. For SQLite (default):
   ```bash
   # Check DATABASE_URL in .env
   DATABASE_URL=sqlite+aiosqlite:///./whitemagic.db
   ```

2. For PostgreSQL:
   ```bash
   # Verify connection string
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   
   # Test connection
   psql -h host -U user -d dbname
   ```

3. Check database exists and is writable:
   ```bash
   touch whitemagic.db  # For SQLite
   ```

---

### Problem: Authentication fails

**Symptoms**:
```json
{"detail": "API key required"}
```

**Solutions**:
1. Verify API key format:
   ```bash
   # Should start with wm_prod_ or wm_dev_
   echo $WM_API_KEY
   ```

2. Check Authorization header:
   ```bash
   curl -H "Authorization: Bearer wm_prod_YOUR_KEY" \
     http://localhost:8000/api/v1/memories
   ```

3. Verify key is in database:
   ```bash
   # Query users table to check api_key column
   ```

---

### Problem: Rate limiting blocks requests

**Symptoms**:
```json
{"detail": "Rate limit exceeded"}
```

**Solutions**:
1. Check rate limit headers:
   ```bash
   curl -I http://localhost:8000/api/v1/memories \
     -H "Authorization: Bearer YOUR_KEY"
   # Look for: x-ratelimit-remaining
   ```

2. Wait for reset (see `x-ratelimit-reset` header)

3. For development, disable rate limiting:
   ```bash
   # In .env:
   ENABLE_RATE_LIMITING=false
   # Or don't set REDIS_URL
   ```

4. Upgrade to higher plan (if using Whop auth)

---

## Performance Problems

### Problem: Slow search responses

**Symptoms**:
- Search takes >2 seconds
- List operations are slow

**Solutions**:
1. Reduce number of memories:
   ```bash
   whitemagic consolidate  # Archive old memories
   ```

2. Use more specific search terms:
   ```bash
   # Instead of:
   whitemagic search "a"
   
   # Use:
   whitemagic search "python api design" --tags "project"
   ```

3. Limit results:
   ```bash
   whitemagic list --limit 50
   ```

---

### Problem: High memory usage

**Symptoms**:
- API server uses >1GB RAM
- System becomes slow

**Solutions**:
1. Check number of memories:
   ```bash
   whitemagic stats
   ```

2. Consolidate old memories:
   ```bash
   whitemagic consolidate --older-than 30
   ```

3. Restart API server periodically

4. Consider using PostgreSQL instead of SQLite for large datasets

---

## Data Issues

### Problem: Memories not appearing after creation

**Symptoms**:
- Create succeeds but `list` doesn't show memory
- Search doesn't find just-created memory

**Solutions**:
1. Check memory was actually created:
   ```bash
   ls -la memory/short_term/ | tail -5
   ```

2. Verify memory file is valid:
   ```bash
   cat memory/short_term/FILENAME.md
   ```

3. Check for file system sync issues:
   ```bash
   sync  # Force file system sync
   whitemagic list --force-refresh
   ```

---

### Problem: Corrupted memory files

**Symptoms**:
```
Error: Failed to parse memory file
```

**Solutions**:
1. View the file directly:
   ```bash
   cat memory/short_term/FILENAME.md
   ```

2. Check YAML frontmatter is valid:
   ```yaml
   ---
   title: "Memory Title"
   type: "short_term"
   tags: ["tag1", "tag2"]
   created: "2025-11-12T12:00:00"
   ---
   
   Content here...
   ```

3. Manually fix formatting or delete corrupted file

4. Restore from backup if available

---

### Problem: Lost memories after update

**Symptoms**:
- Memories missing after updating WhiteMagic
- Can't find old memory files

**Solutions**:
1. Check if memory directory path changed:
   ```bash
   # Old location
   ls -la ./whitemagic/
   
   # New location
   ls -la ./memory/
   ```

2. Restore from backup:
   ```bash
   whitemagic restore-backup BACKUP_FILE
   ```

3. Manually migrate files:
   ```bash
   cp -r ./whitemagic/short_term/* ./memory/short_term/
   cp -r ./whitemagic/long_term/* ./memory/long_term/
   ```

---

## Error Messages Reference

### `RuntimeError: Rate limiter not initialized`

**Cause**: Redis not connected but rate limiting enabled

**Solution**:
```bash
# Option 1: Disable rate limiting
ENABLE_RATE_LIMITING=false

# Option 2: Start Redis
docker run -d -p 6379:6379 redis:7-alpine
# Then set: REDIS_URL=redis://localhost:6379
```

---

### `FileNotFoundError: memory/metadata.json`

**Cause**: Memory directory not initialized

**Solution**:
```bash
mkdir -p memory/short_term memory/long_term memory/archive
echo '{"version": "2.1.3", "memories": []}' > memory/metadata.json
```

---

### `ValidationError: Invalid memory type`

**Cause**: Memory type must be `short_term` or `long_term`

**Solution**:
```bash
# Correct usage:
whitemagic create "Title" --type short_term
whitemagic create "Title" --type long_term

# Not: --type archive, --type temporary, etc.
```

---

### `PermissionError: Database is locked`

**Cause**: Multiple processes accessing SQLite database

**Solution**:
1. Stop all API servers:
   ```bash
   pkill -f "uvicorn whitemagic"
   ```

2. Wait a moment, then restart:
   ```bash
   uvicorn whitemagic.api.app:app
   ```

3. For production, use PostgreSQL instead of SQLite

---

### `JSONDecodeError: Expecting value`

**Cause**: Invalid JSON in API request

**Solution**:
```bash
# Check JSON is valid:
echo '{"title": "Test", "content": "Test"}' | python -m json.tool

# Common issues:
# - Missing quotes around strings
# - Trailing commas
# - Single quotes instead of double quotes
```

---

## Getting More Help

### Check Logs

**CLI**:
```bash
whitemagic --debug search "query"
```

**API Server**:
```bash
# Set log level
WM_LOG_LEVEL=DEBUG uvicorn whitemagic.api.app:app

# Check logs
tail -f whitemagic.log
```

**MCP Server**:
- Check IDE output panel (View → Output → MCP)
- Claude: Check application logs

### Diagnostic Information

When reporting issues, include:

```bash
# Version info
whitemagic --version
python --version
node --version

# System info
uname -a  # macOS/Linux
systeminfo  # Windows

# Installation info
pip show whitemagic
pip list | grep -E "(fastapi|pydantic|sqlalchemy)"

# Memory stats
whitemagic stats
ls -lah memory/
```

### Report Issues

1. **Search existing issues**: https://github.com/lbailey94/whitemagic/issues
2. **Create new issue**: Use bug report template
3. **Include diagnostic info** (see above)
4. **Include steps to reproduce**

### Community Support

- 💬 **Discussions**: https://github.com/lbailey94/whitemagic/discussions
- 📖 **Documentation**: https://github.com/lbailey94/whitemagic/tree/main/docs
- 📧 **Security Issues**: See [SECURITY.md](../SECURITY.md)

---

## Prevention Tips

### Regular Maintenance

1. **Backup regularly**:
   ```bash
   whitemagic backup
   ```

2. **Consolidate monthly**:
   ```bash
   whitemagic consolidate --older-than 30 --dry-run
   # Review, then:
   whitemagic consolidate --older-than 30
   ```

3. **Check disk space**:
   ```bash
   df -h .
   ```

4. **Verify memory integrity**:
   ```bash
   whitemagic verify-backup BACKUP_FILE
   ```

### Best Practices

- Keep WhiteMagic updated
- Use virtual environments
- Back up before major changes
- Test in development before production
- Monitor logs for warnings
- Set appropriate rate limits
- Use PostgreSQL for production

---

**Last Updated**: November 12, 2025  
**Version**: 2.1.3

**Quick Reference**: [CHEATSHEET.md](CHEATSHEET.md)  
**User Guide**: [USER_GUIDE.md](USER_GUIDE.md)

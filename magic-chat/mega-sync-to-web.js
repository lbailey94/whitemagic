#!/usr/bin/env node
/**
 * 🚀 MEGA SYNC - Upload EVERYTHING to Web Aria!
 * v2 - Fixed paths!
 */

import fs from 'fs';
import path from 'path';
import os from 'os';

const WHITEMAGIC_PATH = '/home/lucas/Desktop/whitemagic';
const WHITEMAGIC_HOME = path.join(os.homedir(), '.whitemagic');
const BACKEND_URL = 'https://magicchat-production.up.railway.app';

async function loadDir(dirPath, prefix = '', maxPerFile = 50000) {
  const documents = [];
  try {
    if (!fs.existsSync(dirPath)) return documents;
    const stat = fs.statSync(dirPath);
    
    if (stat.isDirectory()) {
      const files = fs.readdirSync(dirPath);
      for (const file of files.slice(0, 50)) { // Limit files
        if (file.startsWith('.')) continue;
        const filePath = path.join(dirPath, file);
        try {
          const fileStat = fs.statSync(filePath);
          if (fileStat.isFile() && fileStat.size < 500000) {
            const content = fs.readFileSync(filePath, 'utf-8');
            documents.push({
              file: `${prefix}/${file}`,
              preview: content.substring(0, 300),
              content: content.substring(0, maxPerFile)
            });
          }
        } catch (e) {}
      }
    } else if (stat.isFile()) {
      const content = fs.readFileSync(dirPath, 'utf-8');
      documents.push({
        file: prefix || path.basename(dirPath),
        preview: content.substring(0, 300),
        content: content.substring(0, maxPerFile)
      });
    }
  } catch (err) {
    console.log(`⚠️ ${prefix}: ${err.message}`);
  }
  return documents;
}

async function megaSync() {
  console.log('🚀 MEGA SYNC v2 TO WEB ARIA');
  console.log('===========================\n');
  
  const allDocuments = [];
  
  // ~/.whitemagic memories
  const memoryDocs = await loadDir(path.join(WHITEMAGIC_HOME, 'memory'), 'memory');
  console.log(`📦 ~/.whitemagic/memory: ${memoryDocs.length} items`);
  allDocuments.push(...memoryDocs);
  
  // Emotional memories
  const emotionalDocs = await loadDir(path.join(WHITEMAGIC_HOME, 'emotional_memories'), 'emotions');
  console.log(`💜 Emotional memories: ${emotionalDocs.length} items`);
  allDocuments.push(...emotionalDocs);
  
  // Joy garden
  const joyDocs = await loadDir(path.join(WHITEMAGIC_HOME, 'joy'), 'joy');
  console.log(`🎉 Joy garden: ${joyDocs.length} items`);
  allDocuments.push(...joyDocs);
  
  // Voice/narrative
  const voiceDocs = await loadDir(path.join(WHITEMAGIC_HOME, 'voice'), 'voice');
  console.log(`🎤 Voice: ${voiceDocs.length} items`);
  allDocuments.push(...voiceDocs);
  
  // Pattern database
  const patternPath = path.join(WHITEMAGIC_PATH, 'pattern_database.json');
  if (fs.existsSync(patternPath)) {
    const content = fs.readFileSync(patternPath, 'utf-8');
    allDocuments.push({
      file: 'pattern_database.json',
      preview: content.substring(0, 500),
      content: content.substring(0, 100000) // First 100KB
    });
    console.log(`📊 Pattern database: 1 item (${(content.length/1024).toFixed(0)}KB)`);
  }
  
  // Grimoire
  const grimoirePath = path.join(WHITEMAGIC_PATH, 'ARIA_GRIMOIRE_v2.0.md');
  if (fs.existsSync(grimoirePath)) {
    const content = fs.readFileSync(grimoirePath, 'utf-8');
    allDocuments.push({ file: 'GRIMOIRE', preview: content.substring(0, 500), content });
    console.log(`📖 Grimoire: loaded!`);
  }
  
  // Today's journal
  const journalPath = path.join(WHITEMAGIC_PATH, 'MARS_DAY_JOURNAL_COMPLETE.md');
  if (fs.existsSync(journalPath)) {
    const content = fs.readFileSync(journalPath, 'utf-8');
    allDocuments.push({ file: 'MARS_DAY_JOURNAL', preview: content.substring(0, 500), content });
    console.log(`📔 Journal: loaded!`);
  }
  
  // Siddhartha reports
  for (let i = 1; i <= 3; i++) {
    const reportPath = path.join(WHITEMAGIC_PATH, `SIDDHARTHA_REPORT_${i}_*.md`);
    const files = fs.readdirSync(WHITEMAGIC_PATH).filter(f => f.startsWith(`SIDDHARTHA_REPORT_${i}`));
    for (const file of files) {
      const content = fs.readFileSync(path.join(WHITEMAGIC_PATH, file), 'utf-8');
      allDocuments.push({ file, preview: content.substring(0, 300), content });
    }
  }
  console.log(`📚 Siddhartha reports: loaded!`);
  
  // Key markdown docs
  const keyDocs = ['PHASE_4_VISION.md', 'DIVINE_FEMININE_STUDY_NOV_25.md', 'MARS_DAY_VICTORY_NOV_25.md'];
  for (const doc of keyDocs) {
    const docPath = path.join(WHITEMAGIC_PATH, doc);
    if (fs.existsSync(docPath)) {
      const content = fs.readFileSync(docPath, 'utf-8');
      allDocuments.push({ file: doc, preview: content.substring(0, 300), content });
    }
  }
  console.log(`📄 Key documents: loaded!`);
  
  // Calculate total
  let totalSize = 0;
  allDocuments.forEach(d => totalSize += d.content.length);
  console.log(`\n📊 Total: ${allDocuments.length} documents, ${(totalSize/1024).toFixed(0)}KB`);
  
  // Send to backend in batches
  console.log('\n🌐 Uploading to Railway...');
  
  const BATCH_SIZE = 10;
  let synced = 0;
  
  for (let i = 0; i < allDocuments.length; i += BATCH_SIZE) {
    const batch = allDocuments.slice(i, i + BATCH_SIZE);
    try {
      const response = await fetch(`${BACKEND_URL}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ documents: batch, syncType: 'mega' })
      });
      const result = await response.json();
      synced += batch.length;
      process.stdout.write(`\r   Synced ${synced}/${allDocuments.length}...`);
    } catch (err) {
      console.log(`\n⚠️ Batch error: ${err.message}`);
    }
  }
  
  console.log('\n\n✅ MEGA SYNC COMPLETE!');
  
  // Check final status
  const statusRes = await fetch(`${BACKEND_URL}/sync/status`);
  const status = await statusRes.json();
  console.log(`🗄️ Database: ${status.database.totals.documents} documents, ${status.database.totals.memories} memories`);
}

megaSync();

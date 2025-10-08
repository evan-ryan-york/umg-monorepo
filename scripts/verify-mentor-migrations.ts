#!/usr/bin/env ts-node

/**
 * Verify Mentor Agent database migrations
 *
 * This script checks if the required tables and indexes exist
 */

import { createClient } from '@supabase/supabase-js';
import * as fs from 'fs';
import * as path from 'path';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://mdcarckygvbcjgexvdqw.supabase.co';
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

const supabase = createClient(supabaseUrl, supabaseKey);

async function verifyDismissedPatternsTable() {
  console.log('🔍 Checking dismissed_patterns table...');

  try {
    const { data, error } = await supabase
      .from('dismissed_patterns')
      .select('id')
      .limit(1);

    if (error && error.message.includes('does not exist')) {
      console.log('   ❌ NOT FOUND - Run: docs/migrations/create_dismissed_patterns_table.sql');
      return false;
    } else if (error) {
      console.log(`   ⚠️  ERROR: ${error.message}`);
      return false;
    } else {
      console.log('   ✅ EXISTS');
      return true;
    }
  } catch (e: any) {
    console.log(`   ❌ ERROR: ${e.message}`);
    return false;
  }
}

async function printMigrationInstructions() {
  console.log('\n📖 How to Run Migrations:\n');
  console.log('1. Go to Supabase SQL Editor:');
  console.log('   https://supabase.com/dashboard/project/mdcarckygvbcjgexvdqw/sql\n');

  console.log('2. Click "+ New Query"\n');

  console.log('3. Run these migrations in order:\n');

  const migrations = [
    'docs/migrations/create_dismissed_patterns_table.sql',
    'docs/migrations/add_mentor_indexes.sql'
  ];

  migrations.forEach((file, i) => {
    const fullPath = path.join(process.cwd(), file);
    console.log(`   ${i + 1}. ${file}`);

    if (fs.existsSync(fullPath)) {
      const lines = fs.readFileSync(fullPath, 'utf8').split('\n').length;
      console.log(`      (${lines} lines)\n`);
    } else {
      console.log(`      ⚠️  File not found\n`);
    }
  });

  console.log('4. Copy the SQL content from each file');
  console.log('5. Paste into SQL Editor and click "Run"\n');
}

async function main() {
  console.log('🚀 Mentor Migration Verification\n');
  console.log('='.repeat(50) + '\n');

  const tableExists = await verifyDismissedPatternsTable();

  console.log('\n' + '='.repeat(50) + '\n');

  if (!tableExists) {
    await printMigrationInstructions();
  } else {
    console.log('✅ All required tables exist!\n');
    console.log('📝 Next: Run add_mentor_indexes.sql for performance optimization\n');
  }
}

main().catch(console.error);

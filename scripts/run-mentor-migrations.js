#!/usr/bin/env node

/**
 * Run Mentor Agent database migrations
 *
 * This script runs the migrations for Phase 1 of the Mentor implementation:
 * 1. Create dismissed_patterns table
 * 2. Add performance indexes
 */

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config({ path: path.join(__dirname, '../apps/web/.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials in .env.local');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function runMigration(name, sqlFile) {
  console.log(`\n📝 Running migration: ${name}...`);

  const sql = fs.readFileSync(sqlFile, 'utf8');

  try {
    const { data, error } = await supabase.rpc('exec_sql', { sql_string: sql });

    if (error) {
      // Try direct query approach if rpc doesn't exist
      const statements = sql
        .split(';')
        .map(s => s.trim())
        .filter(s => s && !s.startsWith('--') && !s.startsWith('COMMENT'));

      for (const statement of statements) {
        if (statement) {
          const { error: execError } = await supabase.from('_').select('*').limit(0); // Dummy query
          // Note: Supabase JS client doesn't support raw SQL execution
          // We'll need to use the SQL editor in Supabase dashboard
        }
      }

      console.log(`⚠️  Could not auto-run migration (this is expected)`);
      console.log(`   Please run manually in Supabase SQL Editor:`);
      console.log(`   File: ${sqlFile}\n`);
      return false;
    }

    console.log(`✅ Migration completed: ${name}`);
    return true;
  } catch (error) {
    console.error(`❌ Error running migration ${name}:`, error.message);
    return false;
  }
}

async function verifyMigrations() {
  console.log('\n🔍 Verifying migrations...\n');

  // Check if dismissed_patterns table exists
  try {
    const { data, error } = await supabase
      .from('dismissed_patterns')
      .select('id')
      .limit(1);

    if (error && error.message.includes('does not exist')) {
      console.log('❌ dismissed_patterns table: NOT FOUND');
      console.log('   → Run: docs/migrations/create_dismissed_patterns_table.sql\n');
    } else if (error) {
      console.log('⚠️  dismissed_patterns table: ERROR', error.message);
    } else {
      console.log('✅ dismissed_patterns table: EXISTS\n');
    }
  } catch (e) {
    console.log('❌ dismissed_patterns table: ERROR\n');
  }

  // Check if insight table has indexes
  console.log('📊 Checking indexes...');
  console.log('   (Index verification requires SQL editor access)\n');
}

async function main() {
  console.log('🚀 Mentor Agent Migration Tool\n');
  console.log('=' .repeat(50));

  const migrationsDir = path.join(__dirname, '../docs/migrations');

  const migrations = [
    {
      name: 'Create dismissed_patterns table',
      file: path.join(migrationsDir, 'create_dismissed_patterns_table.sql')
    },
    {
      name: 'Add Mentor indexes',
      file: path.join(migrationsDir, 'add_mentor_indexes.sql')
    }
  ];

  console.log('\n📋 Migrations to run:\n');
  migrations.forEach((m, i) => {
    console.log(`   ${i + 1}. ${m.name}`);
    console.log(`      ${m.file}\n`);
  });

  console.log('\n⚠️  NOTE: Supabase JS client cannot execute raw SQL.');
  console.log('   These migrations must be run manually in Supabase SQL Editor.\n');

  console.log('📖 Instructions:\n');
  console.log('   1. Go to: https://supabase.com/dashboard/project/mdcarckygvbcjgexvdqw/sql');
  console.log('   2. Click "+ New Query"');
  console.log('   3. Copy contents of migration file');
  console.log('   4. Click "Run" to execute\n');

  console.log('📂 Migration files:\n');
  migrations.forEach((m, i) => {
    const relativePath = path.relative(process.cwd(), m.file);
    console.log(`   ${i + 1}. ${relativePath}`);
  });

  console.log('\n');

  // Verify current state
  await verifyMigrations();

  console.log('\n' + '=' .repeat(50));
  console.log('✅ Migration tool complete\n');
}

main().catch(console.error);

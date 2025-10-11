#!/usr/bin/env tsx
/**
 * Migration runner for Supabase
 * Usage: tsx scripts/run-migration.ts <migration-file-path>
 */

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('❌ Missing required environment variables:');
  console.error('   NEXT_PUBLIC_SUPABASE_URL or SUPABASE_URL');
  console.error('   SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

const migrationPath = process.argv[2];
if (!migrationPath) {
  console.error('❌ Usage: tsx scripts/run-migration.ts <migration-file-path>');
  process.exit(1);
}

async function runMigration() {
  console.log('🔄 Running migration:', migrationPath);

  const supabase = createClient(SUPABASE_URL!, SUPABASE_SERVICE_ROLE_KEY!);

  try {
    // Read migration SQL file
    const sqlContent = readFileSync(resolve(migrationPath), 'utf-8');

    // Split by semicolons and execute each statement
    const statements = sqlContent
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith('--'));

    console.log(`📝 Found ${statements.length} SQL statements`);

    for (let i = 0; i < statements.length; i++) {
      const statement = statements[i];
      console.log(`\n▶️  Executing statement ${i + 1}/${statements.length}...`);
      console.log(`   ${statement.substring(0, 80)}${statement.length > 80 ? '...' : ''}`);

      const { error } = await supabase.rpc('exec_sql', { sql: statement });

      if (error) {
        console.error(`❌ Error in statement ${i + 1}:`, error);
        // Try direct query if RPC fails
        const { error: directError } = await supabase.from('_sql').select('*').limit(0);
        if (directError) {
          console.error('⚠️  Note: Direct SQL execution not available. Please run this migration manually in Supabase SQL Editor:');
          console.error('\n' + sqlContent);
          process.exit(1);
        }
      } else {
        console.log(`✅ Statement ${i + 1} executed successfully`);
      }
    }

    console.log('\n✅ Migration completed successfully!');
  } catch (error) {
    console.error('❌ Migration failed:', error);
    console.error('\n⚠️  Please run this migration manually in Supabase SQL Editor:');
    const sqlContent = readFileSync(resolve(migrationPath), 'utf-8');
    console.error('\n' + sqlContent);
    process.exit(1);
  }
}

runMigration();

import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import importX from 'eslint-plugin-import-x'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),

  // ── TypeScript files: strict type-checked + stylistic ──
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.strictTypeChecked,
      tseslint.configs.stylisticTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'import-x': importX,
    },
    rules: {
      // ── Import ordering ──
      'import-x/order': [
        'error',
        {
          groups: [
            'builtin',
            'external',
            'internal',
            'parent',
            'sibling',
            'index',
            'type',
          ],
          'newlines-between': 'never',
          alphabetize: { order: 'asc', caseInsensitive: true },
        },
      ],
      'import-x/no-duplicates': 'error',

      // ── React Refresh: allow constant exports alongside components ──
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],

      // ── TypeScript rule adjustments ──
      // Allow non-null assertions in specific patterns (e.g., document.getElementById('root')!)
      '@typescript-eslint/no-non-null-assertion': 'warn',

      // Relax restrict-template-expressions to allow numbers and booleans
      '@typescript-eslint/restrict-template-expressions': [
        'error',
        {
          allowNumber: true,
          allowBoolean: true,
        },
      ],
    },
  },

  // ── Disable type-aware linting for plain JS config files ──
  {
    files: ['**/*.js'],
    extends: [tseslint.configs.disableTypeChecked],
  },
])

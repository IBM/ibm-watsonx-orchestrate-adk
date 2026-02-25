import eslint from '@eslint/js';
import tslint from 'typescript-eslint';
import tsplugin from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import prettierConfig from 'eslint-plugin-prettier/recommended';

export default tslint.config(
  {
    ignores: [
      'dist',
      'node_modules',
      'coverage',
      '.jest-cache',
      'jest.config.ts',
    ],
  },
  eslint.configs.recommended,
  ...tslint.configs.recommended,
  prettierConfig,
  {
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        project: 'tsconfig.lint.json',
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      /*========================================= eslint =========================================*/
      curly: 'error',
      'dot-notation': 'off', // Handled by @typescript-eslint
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      'guard-for-in': 'error',
      'no-array-constructor': 'off', // Handled by @typescript-eslint
      'no-bitwise': 'error',
      'no-caller': 'error',
      'no-console': 'warn',
      'no-empty-function': 'off', // Handled by @typescript-eslint
      'no-eval': 'error',
      'no-labels': 'error',
      'no-param-reassign': 'error',
      'no-shadow': 'off', // Handled by @typescript-eslint
      'no-throw-literal': 'off', // Handled by @typescript-eslint
      'no-undef-init': 'error',
      'no-unused-expression': 'off', // Handled by @typescript-eslint
      'no-unused-vars': 'off', // Handled by tsconfig
      'no-var': 'error',
      'object-shorthand': ['error', 'always'],
      'prefer-arrow-callback': 'error',
      'prefer-const': 'error',
      'prefer-template': 'warn',
      radix: 'error',
      'sort-imports': [
        'error',
        {
          allowSeparatedGroups: true,
          ignoreCase: true,
          ignoreDeclarationSort: true,
        },
      ],
      'sort-keys': 'off',
      /*=================================== @typescript-eslint ===================================*/
      '@typescript-eslint/consistent-type-definitions': 'off',
      '@typescript-eslint/dot-notation': 'error',
      '@typescript-eslint/explicit-module-boundary-types': 'warn',
      '@typescript-eslint/member-ordering': 'error',
      '@typescript-eslint/naming-convention': [
        'warn',
        {
          selector: 'class',
          format: ['PascalCase'],
        },
        {
          selector: 'variableLike',
          format: ['camelCase', 'PascalCase'],
        },
        {
          selector: 'variable',
          modifiers: ['const'],
          format: ['camelCase', 'PascalCase', 'UPPER_CASE'],
        },
        {
          selector: 'function',
          format: ['camelCase', 'PascalCase'],
        },
        {
          selector: 'parameter',
          format: ['camelCase', 'PascalCase'],
          leadingUnderscore: 'allow',
        },
        {
          selector: 'interface',
          format: ['PascalCase'],
        },
      ],
      '@typescript-eslint/no-array-constructor': 'error',
      '@typescript-eslint/no-empty-function': [
        'error',
        { allow: ['arrowFunctions'] },
      ],
      '@typescript-eslint/no-inferrable-types': [
        'error',
        { ignoreParameters: true },
      ],
      '@typescript-eslint/no-misused-new': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/no-shadow': [
        'error',
        { ignoreTypeValueShadow: true },
      ],
      '@typescript-eslint/no-unnecessary-boolean-literal-compare': 'error',
      '@typescript-eslint/no-unused-expressions': 'error',
      '@typescript-eslint/no-unused-vars': 'off', // Handled by tsconfig
      '@typescript-eslint/only-throw-error': 'error',
      '@typescript-eslint/prefer-function-type': 'error',
      '@typescript-eslint/prefer-includes': 'error',
      '@typescript-eslint/unified-signatures': 'error',
      '@typescript-eslint/strict-boolean-expressions': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-unsafe-optional-chaining': 'warn',
      '@typescript-eslint/ban-ts-comment': 'warn',
      'no-case-declarations': 'warn',
    },
    plugins: {
      '@typescript-eslint/eslint-plugin': tsplugin,
    },
  },
);

// Made with Bob

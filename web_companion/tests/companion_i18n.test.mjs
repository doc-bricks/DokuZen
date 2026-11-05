import test from 'node:test';
import assert from 'node:assert/strict';
import { TRANSLATIONS, DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, getTranslation } from '../app.js';

test('SUPPORTED_LANGUAGES declares all 6 Tier-2 languages', () => {
  const expected = ['de', 'en', 'es', 'zh', 'ja', 'ru'];
  assert.deepEqual([...SUPPORTED_LANGUAGES].sort(), expected.sort());
});

test('TRANSLATIONS object contains all 6 languages', () => {
  for (const lang of SUPPORTED_LANGUAGES) {
    assert.ok(TRANSLATIONS[lang], `Missing dictionary for language: ${lang}`);
  }
});

test('100% key parity across all 6 Tier-2 languages', () => {
  const baseKeys = Object.keys(TRANSLATIONS.de).sort();
  assert.ok(baseKeys.length >= 20, `Base keys count should be >= 20, found ${baseKeys.length}`);

  for (const lang of SUPPORTED_LANGUAGES) {
    const langKeys = Object.keys(TRANSLATIONS[lang]).sort();
    assert.deepEqual(langKeys, baseKeys, `Keys mismatch for language: ${lang}`);
    for (const k of langKeys) {
      const val = TRANSLATIONS[lang][k];
      assert.equal(typeof val, 'string', `${lang}.${k} must be string`);
      assert.ok(val.trim().length > 0, `${lang}.${k} must not be empty`);
    }
  }
});

test('getTranslation returns expected string and fallbacks gracefully', () => {
  assert.equal(getTranslation('import_btn', 'de'), 'JSON importieren');
  assert.equal(getTranslation('import_btn', 'en'), 'Import JSON');
  assert.equal(getTranslation('import_btn', 'es'), 'Importar JSON');
  assert.equal(getTranslation('import_btn', 'zh'), '导入JSON');
  assert.equal(getTranslation('import_btn', 'ja'), 'JSONをインポート');
  assert.equal(getTranslation('import_btn', 'ru'), 'Импорт JSON');

  // Fallback to default language (de) if unknown language provided
  assert.equal(getTranslation('import_btn', 'fr'), 'JSON importieren');

  // Fallback to key if unknown key
  assert.equal(getTranslation('unknown_key_xyz', 'en'), 'unknown_key_xyz');
});

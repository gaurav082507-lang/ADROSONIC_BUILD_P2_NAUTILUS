// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

// Words a claimant must never see (investigator-only / accusatory vocabulary), EN + HI.
const forbidden =
  /fraud|fake|ai-generated|deepfake|tampered|liveness|face match|duplicate|suspicious|risk score|heatmap|network|\bring\b|linked claims|synthetic|spoof|voice clone|cloned|फ्रॉड|धोखाधड़ी|फर्जी|नकली|जाली|डीपफेक|लाइवनेस/i;

const claimantDir = join(__dirname, '../src/features/claims');

/** User-visible text only: JSX text nodes and string literals containing a space. */
function visibleStrings(source: string): string[] {
  const out: string[] = [];
  for (const m of source.matchAll(/>([^<>{}]+)</g)) out.push(m[1].trim());
  for (const m of source.matchAll(/'([^'\n]{3,})'|"([^"\n]{3,})"|`([^`\n]{3,})`/g)) {
    const text = m[1] ?? m[2] ?? m[3] ?? '';
    if (text.includes(' ') && !text.includes('className')) out.push(text);
  }
  return out.filter(Boolean);
}

function stringValues(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (value && typeof value === 'object') return Object.values(value).flatMap(stringValues);
  return [];
}

describe('claimant safety', () => {
  it('claimant i18n strings (EN + HI) contain no investigator-only terms', () => {
    for (const lang of ['en', 'hi']) {
      const dict = JSON.parse(readFileSync(join(__dirname, `../src/i18n/${lang}.json`), 'utf8'));
      const hits = stringValues(dict).filter((s) => forbidden.test(s));
      expect(hits, `${lang}.json`).toEqual([]);
    }
  });

  it('claimant pages render no investigator-only terms', () => {
    for (const file of readdirSync(claimantDir).filter((f) => f.endsWith('.tsx'))) {
      const hits = visibleStrings(readFileSync(join(claimantDir, file), 'utf8')).filter((s) =>
        forbidden.test(s),
      );
      expect(hits, file).toEqual([]);
    }
  });
});

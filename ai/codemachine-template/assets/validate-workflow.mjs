#!/usr/bin/env node
/**
 * validate-workflow.mjs — CodeMachine workflow validator
 *
 * Faithful port of the real CodeMachine loader/validator behaviour, derived from
 * CodeMachine-CLI source:
 *   src/workflows/templates/validator.ts   (validateWorkflowTemplate)
 *   src/workflows/utils/resolvers/step.ts   (resolveStep — throws on unknown agent)
 *   src/workflows/utils/resolvers/module.ts (resolveModule — throws on unknown module)
 *   src/workflows/utils/config.ts           (registerImportedAgents: main.agents.js + modules.js)
 *   src/workflows/templates/loader.ts        (dynamic import + validate)
 *
 * Catches the failure modes that make a template silently disappear from the picker:
 *   • resolveStep('id') referencing an agent not in config/main.agents.js  → throw
 *   • resolveModule('id') referencing a module not in config/modules.js    → throw
 *   • step.type not 'module'/'separator', bad promptPath, bad reasoning effort, etc.
 *   • module behavior missing { type:'loop', action:'stepBack', steps>0 }
 *   • loopSteps that rewind past step 0
 *
 * Usage:
 *   node validate-workflow.mjs <workflow.js> [--config <packageConfigDir>]
 *
 * If --config is omitted, it auto-detects ../../config relative to the workflow
 * (i.e. the package root's config/ dir, matching CodeMachine package layout).
 */

import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import * as path from 'node:path';
import * as fs from 'node:fs';

const require = createRequire(import.meta.url);

// ── arg parsing ────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const wfPath = args.find(a => !a.startsWith('--'));
const cfgFlagIdx = args.indexOf('--config');
let configDir = cfgFlagIdx >= 0 ? args[cfgFlagIdx + 1] : null;

if (!wfPath) {
  console.error('Usage: node validate-workflow.mjs <workflow.js> [--config <packageConfigDir>]');
  process.exit(2);
}
const wfAbs = path.resolve(wfPath);
if (!fs.existsSync(wfAbs)) {
  console.error(`❌ Workflow file not found: ${wfAbs}`);
  process.exit(2);
}
// Auto-detect package config dir: <pkg>/templates/workflows/x.js → <pkg>/config
if (!configDir) {
  const guess = path.resolve(path.dirname(wfAbs), '..', '..', 'config');
  configDir = fs.existsSync(guess) ? guess : null;
}

// ── load package config (replicates registerImportedAgents) ─────────────────
let mainAgents = [];
let moduleCatalog = [];
if (configDir) {
  const mainPath = path.join(configDir, 'main.agents.js');
  const modsPath = path.join(configDir, 'modules.js');
  try {
    delete require.cache[require.resolve(mainPath)];
    const m = require(mainPath);
    if (Array.isArray(m)) mainAgents = m;
  } catch (e) { console.error(`⚠ could not load main.agents.js: ${e.message}`); }
  try {
    delete require.cache[require.resolve(modsPath)];
    const m = require(modsPath);
    if (Array.isArray(m)) moduleCatalog = m;
  } catch { /* modules.js optional */ }
}

// ── global helpers (replicate real resolver behaviour incl. throws) ─────────
function resolveStep(id, overrides = {}) {
  const agent = mainAgents.find(e => e?.id === id);
  if (!agent) throw new Error(`Unknown main agent: ${id}`);
  const agentName = overrides.agentName ?? agent.name;
  const promptPath = overrides.promptPath ?? agent.promptPath;
  const missing = Array.isArray(promptPath)
    ? promptPath.length === 0 || promptPath.some(p => typeof p !== 'string' || p.trim() === '')
    : typeof promptPath !== 'string' || promptPath.trim() === '';
  if (!agentName || missing) throw new Error(`Agent ${id} is missing required fields (name or promptPath)`);
  return {
    type: 'module', agentId: agent.id, agentName, promptPath,
    model: overrides.model ?? agent.model,
    modelReasoningEffort: overrides.modelReasoningEffort ?? agent.modelReasoningEffort,
    engine: overrides.engine ?? agent.engine,
    executeOnce: overrides.executeOnce, interactive: overrides.interactive,
    tracks: overrides.tracks ?? agent.tracks,
    conditions: overrides.conditions ?? agent.conditions,
    conditionsAny: overrides.conditionsAny ?? agent.conditionsAny,
  };
}

function resolveModule(id, overrides = {}) {
  const entry = moduleCatalog.find(e => e?.id === id);
  if (!entry) throw new Error(`Unknown workflow module: ${id}`);
  const promptPath = overrides.promptPath ?? entry.promptPath;
  const invalid = Array.isArray(promptPath)
    ? promptPath.length === 0 || promptPath.some(p => typeof p !== 'string' || p.trim() === '')
    : typeof promptPath !== 'string' || !promptPath.trim();
  if (invalid) throw new Error(`Module ${id} is missing a promptPath configuration.`);
  let behavior;
  const base = entry.behavior;
  if (base && base.type === 'loop' && base.action === 'stepBack') {
    const stepsCand = (typeof overrides.loopSteps === 'number' ? overrides.loopSteps : undefined)
      ?? (typeof base.steps === 'number' ? base.steps : undefined) ?? 1;
    behavior = {
      type: 'loop', action: 'stepBack',
      steps: stepsCand > 0 ? Math.floor(stepsCand) : 1,
      trigger: typeof base.trigger === 'string' ? base.trigger : undefined,
      maxIterations: (overrides.loopMaxIterations ?? base.maxIterations),
      skip: overrides.loopSkip ?? base.skip,
    };
  }
  return {
    type: 'module', agentId: entry.id, agentName: overrides.agentName ?? entry.name ?? entry.id,
    promptPath,
    model: overrides.model ?? entry.model,
    modelReasoningEffort: overrides.modelReasoningEffort ?? entry.modelReasoningEffort,
    engine: overrides.engine ?? entry.engine,
    executeOnce: overrides.executeOnce, interactive: overrides.interactive,
    tracks: overrides.tracks ?? entry.tracks,
    conditions: overrides.conditions ?? entry.conditions,
    conditionsAny: overrides.conditionsAny ?? entry.conditionsAny,
    module: { id: entry.id, behavior },
  };
}

function resolveFolder(_name, _opts = {}) { return []; } // folder steps not validated here
function separator(text) { return { type: 'separator', text }; }
function controller(id, opts = {}) { return { agentId: id, ...opts }; }

for (const [k, v] of Object.entries({ resolveStep, resolveModule, resolveFolder, separator, controller })) {
  Object.defineProperty(globalThis, k, { configurable: true, writable: false, value: v });
}

// ── validateWorkflowTemplate (faithful port of validator.ts) ────────────────
function isValidPromptPath(v) {
  if (typeof v === 'string') return v.trim().length > 0;
  if (Array.isArray(v)) return v.length > 0 && v.every(i => typeof i === 'string' && i.trim().length > 0);
  return false;
}
function validateWorkflowTemplate(value) {
  const errors = [];
  if (!value || typeof value !== 'object') return { valid: false, errors: ['Template is not an object'] };
  const obj = value;
  if (typeof obj.name !== 'string' || obj.name.trim().length === 0) errors.push('Template.name must be a non-empty string');
  if (!Array.isArray(obj.steps)) {
    errors.push('Template.steps must be an array');
  } else {
    obj.steps.forEach((step, i) => {
      if (!step || typeof step !== 'object') { errors.push(`Step[${i}] must be an object`); return; }
      const c = step;
      if (c.type !== 'module' && c.type !== 'separator') errors.push(`Step[${i}].type must be 'module' or 'separator' (got '${String(c.type)}')`);
      if (c.type === 'separator') {
        if (typeof c.text !== 'string' || c.text.trim().length === 0) errors.push(`Step[${i}].text must be a non-empty string`);
        return;
      }
      if (c.type === 'module') {
        if (typeof c.agentId !== 'string') errors.push(`Step[${i}].agentId must be a string`);
        if (typeof c.agentName !== 'string') errors.push(`Step[${i}].agentName must be a string`);
        if (!isValidPromptPath(c.promptPath)) errors.push(`Step[${i}] (${c.agentId}).promptPath must be a non-empty string or array of non-empty strings`);
        if (c.model !== undefined && typeof c.model !== 'string') errors.push(`Step[${i}].model must be a string`);
        if (c.modelReasoningEffort !== undefined && !['low','medium','high'].includes(c.modelReasoningEffort))
          errors.push(`Step[${i}] (${c.agentId}).modelReasoningEffort must be 'low'|'medium'|'high' (got '${String(c.modelReasoningEffort)}')`);
        if (c.executeOnce !== undefined && typeof c.executeOnce !== 'boolean') errors.push(`Step[${i}].executeOnce must be a boolean`);
        if (c.interactive !== undefined && typeof c.interactive !== 'boolean') errors.push(`Step[${i}].interactive must be a boolean`);
        if (c.module !== undefined) {
          if (!c.module || typeof c.module !== 'object') errors.push(`Step[${i}].module must be an object`);
          else {
            const mm = c.module;
            if (typeof mm.id !== 'string') errors.push(`Step[${i}].module.id must be a string`);
            if (mm.behavior !== undefined) {
              if (!mm.behavior || typeof mm.behavior !== 'object') errors.push(`Step[${i}].module.behavior must be an object`);
              else {
                const b = mm.behavior;
                if (b.type !== 'loop' || b.action !== 'stepBack') errors.push(`Step[${i}].module.behavior must be { type:'loop', action:'stepBack', ... }`);
                if (typeof b.steps !== 'number' || b.steps <= 0) errors.push(`Step[${i}].module.behavior.steps must be a positive number`);
                if (b.trigger !== undefined && typeof b.trigger !== 'string') errors.push(`Step[${i}].module.behavior.trigger must be a string`);
                if (b.maxIterations !== undefined && typeof b.maxIterations !== 'number') errors.push(`Step[${i}].module.behavior.maxIterations must be a number`);
              }
            }
          }
        }
      }
    });
  }
  // tracks
  const tracks = obj.tracks;
  if (tracks !== undefined) {
    if (!tracks || typeof tracks !== 'object' || Array.isArray(tracks)) errors.push('Template.tracks must be an object with question and options');
    else {
      if (typeof tracks.question !== 'string' || tracks.question.trim().length === 0) errors.push('Template.tracks.question must be a non-empty string');
      if (!tracks.options || typeof tracks.options !== 'object' || Array.isArray(tracks.options)) errors.push('Template.tracks.options must be an object');
      else Object.entries(tracks.options).forEach(([id, cfg]) => {
        if (!cfg || typeof cfg !== 'object') errors.push(`Template.tracks.options.${id} must be an object`);
        else if (typeof cfg.label !== 'string') errors.push(`Template.tracks.options.${id}.label must be a string`);
      });
    }
  }
  // conditionGroups
  const cg = obj.conditionGroups;
  if (cg !== undefined) {
    if (!Array.isArray(cg)) errors.push('Template.conditionGroups must be an array');
    else cg.forEach((g, gi) => {
      if (!g || typeof g !== 'object') { errors.push(`conditionGroups[${gi}] must be an object`); return; }
      if (typeof g.id !== 'string' || g.id.trim().length === 0) errors.push(`conditionGroups[${gi}].id must be a non-empty string`);
      if (typeof g.question !== 'string' || g.question.trim().length === 0) errors.push(`conditionGroups[${gi}].question must be a non-empty string`);
      if (g.multiSelect !== undefined && typeof g.multiSelect !== 'boolean') errors.push(`conditionGroups[${gi}].multiSelect must be a boolean`);
      if (g.tracks !== undefined && (!Array.isArray(g.tracks) || !g.tracks.every(t => typeof t === 'string'))) errors.push(`conditionGroups[${gi}].tracks must be an array of strings`);
      if (!g.conditions || typeof g.conditions !== 'object' || Array.isArray(g.conditions)) errors.push(`conditionGroups[${gi}].conditions must be an object`);
      else Object.entries(g.conditions).forEach(([cid, cfg]) => {
        if (!cfg || typeof cfg !== 'object') errors.push(`conditionGroups[${gi}].conditions.${cid} must be an object`);
        else if (typeof cfg.label !== 'string') errors.push(`conditionGroups[${gi}].conditions.${cid}.label must be a string`);
      });
    });
  }
  return { valid: errors.length === 0, errors };
}

// ── run ─────────────────────────────────────────────────────────────────────
console.log(`\n🔍 Validating: ${wfAbs}`);
console.log(`   config dir: ${configDir ?? '(none — resolveStep will throw on any agent)'}`);
console.log(`   agents: ${mainAgents.length}, modules: ${moduleCatalog.length}\n`);

let tpl;
try {
  const url = new URL(pathToFileURL(wfAbs).href);
  url.searchParams.set('ts', Date.now().toString());
  const mod = await import(url.href);
  tpl = mod?.default ?? mod;
} catch (e) {
  // This is the failure the CodeMachine picker hits silently — surface it loudly.
  console.error(`❌ MODULE EVALUATION THREW (this is why the template vanishes from the picker):\n`);
  console.error(`   ${e.message}\n`);
  if (e.stack) console.error(e.stack.split('\n').slice(1, 4).join('\n'));
  process.exit(1);
}

const res = validateWorkflowTemplate(tpl);
if (!res.valid) {
  console.error(`❌ VALIDATION FAILED (${res.errors.length} error${res.errors.length>1?'s':''}):\n`);
  res.errors.slice(0, 40).forEach(e => console.error(`   • ${e}`));
  if (res.errors.length > 40) console.error(`   … +${res.errors.length - 40} more`);
  process.exit(1);
}

// extra: loop-bounds sanity (loopSteps must not rewind past step 0)
const loopWarnings = [];
tpl.steps.forEach((s, i) => {
  const steps = s?.module?.behavior?.steps;
  if (typeof steps === 'number' && steps > i) {
    loopWarnings.push(`Step[${i}] (${s.agentId}) loopSteps=${steps} rewinds past step 0 (only ${i} steps precede it)`);
  }
});

// extra: unsatisfiable AND-conditions — a step whose `conditions` (AND logic) lists
// 2+ condition ids from the SAME multiSelect:false group can never all be selected,
// so the step NEVER runs (silent — schema is valid). This is what makes a supervisor
// step vanish and produces "No scope file". Use conditionsAny (OR) for mutually-
// exclusive selection modes instead.
const condWarnings = [];
const condToGroup = new Map();   // conditionId → { groupId, multiSelect }
(tpl.conditionGroups ?? []).forEach(g => {
  const single = g.multiSelect === false || g.multiSelect === undefined;
  Object.keys(g.conditions ?? {}).forEach(cid => condToGroup.set(cid, { groupId: g.id, single }));
  Object.values(g.children ?? {}).forEach(child =>
    Object.keys(child.conditions ?? {}).forEach(cid =>
      condToGroup.set(cid, { groupId: `${g.id}.children`, single: child.multiSelect === false || child.multiSelect === undefined })));
});
tpl.steps.forEach((s, i) => {
  if (!Array.isArray(s.conditions) || s.conditions.length < 2) return;
  const byGroup = {};
  for (const cid of s.conditions) {
    const info = condToGroup.get(cid);
    if (!info || !info.single) continue;
    (byGroup[info.groupId] ??= []).push(cid);
  }
  for (const [gid, cids] of Object.entries(byGroup)) {
    if (cids.length > 1)
      condWarnings.push(`Step[${i}] (${s.agentId}) requires ALL of [${cids.join(', ')}] from single-select group '${gid}' → unsatisfiable, step never runs. Use conditionsAny for OR logic.`);
  }
});

console.log(`✅ VALID — name: "${tpl.name}", steps: ${tpl.steps.length}, conditionGroups: ${tpl.conditionGroups?.length ?? 0}`);
if (condWarnings.length) {
  console.log(`\n⚠ unsatisfiable conditions (steps that will NEVER run — likely "No scope file" cause):`);
  condWarnings.forEach(w => console.log(`   • ${w}`));
}
if (loopWarnings.length) {
  console.log(`\n⚠ loop bounds warnings:`);
  loopWarnings.forEach(w => console.log(`   • ${w}`));
}
process.exit(0);

import type { WorldMapGenerateRequest } from "../../api/world";
import type { WorldMap } from "../../types/world";
import type { QuestLength } from "../../types/quest";
import type { CustomField } from "../../types/blueprint";
import type { DraftTemplate, DraftInstance } from "./draftTypes";

// ── Non-linear step model ───────────────────────────────────────────────────────
// 'character'/'statroll'/'equip'/'inventory'/'charactersummary' are AI-DM-only inline
// sub-steps of 'dmchoice' -- present in STEP_ORDER for natural forward progression,
// but skipped by nextStepId() when dmMode === 'human'. See goNext/jumpTo in AdventureWizard.tsx.

export type WizardStepId =
  | "basics" | "worldgen" | "worldbible" | "templates" | "instances" | "quest"
  | "dmchoice" | "character" | "statroll" | "equip" | "inventory" | "charactersummary"
  | "invite" | "review" | "launch";

export const STEP_ORDER: WizardStepId[] = [
  "basics", "worldgen", "worldbible", "templates", "instances", "quest",
  "dmchoice", "character", "statroll", "equip", "inventory", "charactersummary",
  "invite", "review", "launch",
];

export const STAGE_LABELS = ["Basics", "World", "Content", "Party", "Launch"];

export const STAGE_OF: Record<WizardStepId, number> = {
  basics: 0,
  worldgen: 1, worldbible: 1,
  templates: 2, instances: 2, quest: 2,
  dmchoice: 3, character: 3, statroll: 3, equip: 3, inventory: 3, charactersummary: 3,
  invite: 4, review: 4, launch: 4,
};

export function nextStepId(current: WizardStepId, dmMode: "ai" | "human"): WizardStepId {
  const idx = STEP_ORDER.indexOf(current);
  if (current === "dmchoice" && dmMode === "human") return "invite";
  return STEP_ORDER[Math.min(idx + 1, STEP_ORDER.length - 1)];
}

export function prevStepId(current: WizardStepId, dmMode: "ai" | "human"): WizardStepId {
  const idx = STEP_ORDER.indexOf(current);
  if (current === "invite" && dmMode === "human") return "dmchoice";
  return STEP_ORDER[Math.max(idx - 1, 0)];
}

// ── Biome family/tier config -- same shape the old wizard used, reused here for
// WorldGenStep's right-hand panel. ─────────────────────────────────────────────

export interface BioTierConfig {
  tier: 1 | 2 | 3;
  name: string;
  color: string;
}

export interface BioFamilyConfig {
  id: number;          // BiomeFamily.value from biomes.py
  familyKey: string;    // lowercase family name, matches theme.ts's biome_family_names keys
  familyName: string;  // display / custom name
  enabled: boolean;
  locked: boolean;      // can't be disabled (Ocean, Mountain)
  tiers: BioTierConfig[];
}

export const DEFAULT_BIOME_CONFIG: BioFamilyConfig[] = [
  { id: 0, familyKey: "arid", familyName: "Arid", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Savannah", color: "#c8a951" },
    { tier: 2, name: "Desert", color: "#d4a347" },
    { tier: 3, name: "Scorched Earth", color: "#8b4513" },
  ]},
  { id: 1, familyKey: "grassland", familyName: "Grassland", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Plains", color: "#7cbc5a" },
    { tier: 2, name: "Steppe", color: "#5a9444" },
    { tier: 3, name: "Barren Fields", color: "#4a7c34" },
  ]},
  { id: 2, familyKey: "woodland", familyName: "Woodland", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Forest", color: "#2d6e2d" },
    { tier: 2, name: "Wild Forest", color: "#1e5c1e" },
    { tier: 3, name: "Ancient Forest", color: "#0f4f14" },
  ]},
  { id: 3, familyKey: "tropical", familyName: "Tropical", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Rainforest", color: "#1a9a2a" },
    { tier: 2, name: "Jungle", color: "#0d7a1e" },
    { tier: 3, name: "Overgrown Jungle", color: "#055a14" },
  ]},
  { id: 4, familyKey: "wetland", familyName: "Wetland", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Floodplains", color: "#4a7c5c" },
    { tier: 2, name: "Swamp", color: "#3b6b48" },
    { tier: 3, name: "Blighted Swamp", color: "#2a4a35" },
  ]},
  { id: 5, familyKey: "arctic", familyName: "Arctic", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Taiga", color: "#a8c4a8" },
    { tier: 2, name: "Frozen Tundra", color: "#c8d8d8" },
    { tier: 3, name: "Frozen Wastes", color: "#e8f0f0" },
  ]},
  { id: 6, familyKey: "ocean", familyName: "Ocean", enabled: true, locked: true, tiers: [
    { tier: 1, name: "Coast", color: "#2a6a9a" },
    { tier: 2, name: "Storm Sea", color: "#1a5080" },
    { tier: 3, name: "Abyssal Depths", color: "#0a3060" },
  ]},
  { id: 7, familyKey: "mountain", familyName: "Mountain", enabled: true, locked: true, tiers: [
    { tier: 1, name: "Foothills", color: "#78716c" },
    { tier: 2, name: "Broken Mountains", color: "#57534e" },
    { tier: 3, name: "Jagged Peaks", color: "#a89890" },
  ]},
  { id: 8, familyKey: "volcanic", familyName: "Volcanic", enabled: true, locked: false, tiers: [
    { tier: 1, name: "Ash Foothills", color: "#6b5a4a" },
    { tier: 2, name: "Cinder Mountains", color: "#3d2b1f" },
    { tier: 3, name: "Infernal Cauldron", color: "#8b0000" },
  ]},
];

// ── Wizard data ──────────────────────────────────────────────────────────────────

export type ThemeMode = "preset" | "custom" | "blank";

export interface WizardData {
  // Basics
  campaignName: string;
  themeMode: ThemeMode;
  themePresetId: string | null;
  themePitch: string;
  worldName: string;
  attributeNames: Record<string, string>;
  currencyName: string;

  // World gen
  worldGenParams: WorldMapGenerateRequest;
  previewedMap: WorldMap | null;
  biomeConfig: BioFamilyConfig[];

  // Content
  draftTemplates: DraftTemplate[];
  draftInstances: DraftInstance[];

  // Quest
  questEnabled: boolean;
  questLength: QuestLength;
  questContextHint: string;

  // DM choice + (if AI) character
  dmMode: "ai" | "human";
  characterName: string;
  characterDescription: string;
  characterTone: string;
  raceTemplateTempId: string | null;
  classTemplateTempId: string | null;
  rolledStats: number[];
  statAssignments: Record<string, number>;
  characterCustomFields: CustomField[];        // values for the adventure's character
                                                 // template's non-canonical fields, if any
  equippedWearableTempIds: string[];            // draftInstances tempIds, subset of the below
  inventoryTempIds: string[];                   // draftInstances tempIds

  // Invite
  inviteCode: string;
}

const DEFAULT_ATTRIBUTE_NAMES: Record<string, string> = {
  strength: "Strength", dexterity: "Dexterity", intelligence: "Intelligence",
  fortitude: "Fortitude", charisma: "Charisma", reflex: "Reflex",
};

export function makeInitialWizardData(adventureId: string): WizardData {
  return {
    campaignName: "",
    themeMode: "blank",
    themePresetId: null,
    themePitch: "",
    worldName: "",
    attributeNames: { ...DEFAULT_ATTRIBUTE_NAMES },
    currencyName: "Gold",

    worldGenParams: {
      adventure_id: adventureId,
      seed: Math.floor(Math.random() * 2_147_483_647),
      width: 64,
      height: 64,
      percent_ocean: 0.30,
      percent_mountain: 0.15,
      volcano_chance: 0.35,
      num_elevation_seeds: 2,
      num_land_biomes: 6,
    },
    previewedMap: null,
    biomeConfig: DEFAULT_BIOME_CONFIG,

    draftTemplates: [],
    draftInstances: [],

    questEnabled: false,
    questLength: "medium",
    questContextHint: "",

    dmMode: "ai",
    characterName: "",
    characterDescription: "",
    characterTone: "",
    raceTemplateTempId: null,
    classTemplateTempId: null,
    characterCustomFields: [],
    equippedWearableTempIds: [],
    inventoryTempIds: [],
    rolledStats: [],
    statAssignments: {},

    inviteCode: "",
  };
}

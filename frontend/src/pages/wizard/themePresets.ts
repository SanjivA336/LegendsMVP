// Static preset bundle per theme card in BasicInfoStep -- no backend call needed, unlike
// the "custom" path which hits POST /theme/expand. Shape mirrors ThemeExpansion
// (frontend/src/api/theme.ts) so both paths can feed the same downstream code.

export interface ThemePreset {
  id: string;
  label: string;
  blurb: string;
  worldName: string;
  attributeNames: Record<string, string>;
  currencyName: string;
  biomeFamilyNames: Record<string, string>;
}

const STANDARD_BIOMES: Record<string, string> = {
  arid: "Arid", grassland: "Grassland", woodland: "Woodland", tropical: "Tropical",
  wetland: "Wetland", arctic: "Arctic", ocean: "Ocean", mountain: "Mountain", volcanic: "Volcanic",
};

const STANDARD_ATTRS: Record<string, string> = {
  strength: "Strength", dexterity: "Dexterity", intelligence: "Intelligence",
  fortitude: "Fortitude", charisma: "Charisma", reflex: "Reflex",
};

export const THEME_PRESETS: ThemePreset[] = [
  {
    id: "middle-earth", label: "Middle-earth", blurb: "High fantasy, ancient evils, sweeping journeys",
    worldName: "Vaelmarrow", currencyName: "Gold Pieces",
    attributeNames: { ...STANDARD_ATTRS },
    biomeFamilyNames: {
      arid: "Wastes", grassland: "Shire-lands", woodland: "Old Forest", tropical: "Southern Vales",
      wetland: "Marshes", arctic: "Frost Reach", ocean: "Sundering Sea", mountain: "Misty Peaks", volcanic: "Doom-fires",
    },
  },
  {
    id: "wild-west", label: "Wild West", blurb: "Frontier towns, outlaws, dusty trails",
    worldName: "Dustwater Territory", currencyName: "Dollars",
    attributeNames: { strength: "Grit", dexterity: "Quickdraw", intelligence: "Savvy", fortitude: "Hardiness", charisma: "Nerve", reflex: "Reflex" },
    biomeFamilyNames: {
      arid: "Desert Flats", grassland: "Prairie", woodland: "Timberland", tropical: "Bayou",
      wetland: "Marshland", arctic: "High Plains Snow", ocean: "Coast", mountain: "Badlands", volcanic: "Cinder Ridge",
    },
  },
  {
    id: "steampunk", label: "Steampunk", blurb: "Clockwork machines, airships, industry",
    worldName: "Gearford", currencyName: "Crowns",
    attributeNames: { strength: "Might", dexterity: "Precision", intelligence: "Ingenuity", fortitude: "Vigor", charisma: "Repute", reflex: "Reflex" },
    biomeFamilyNames: { ...STANDARD_BIOMES, mountain: "Smokestack Peaks", volcanic: "Forge Fields" },
  },
  {
    id: "cyberpunk", label: "Cyberpunk", blurb: "Neon megacities, corporations, augments",
    worldName: "Neon Meridian", currencyName: "Credits",
    attributeNames: { strength: "Muscle", dexterity: "Reflex", intelligence: "Netrunning", fortitude: "Wetware", charisma: "Cred", reflex: "Reflex" },
    biomeFamilyNames: {
      arid: "Wastelot", grassland: "Greenbelt", woodland: "Park Sector", tropical: "Underbloc",
      wetland: "Sprawl Sump", arctic: "Cold Sector", ocean: "Harbor District", mountain: "Uptower", volcanic: "Reactor Zone",
    },
  },
  {
    id: "space-opera", label: "Space Opera", blurb: "Star systems, ancient empires, alien frontiers",
    worldName: "The Verge", currencyName: "Credits",
    attributeNames: { strength: "Might", dexterity: "Piloting", intelligence: "Tech", fortitude: "Endurance", charisma: "Presence", reflex: "Reflex" },
    biomeFamilyNames: {
      arid: "Dune Belt", grassland: "Terraformed Plains", woodland: "Bioforest", tropical: "Hothouse Biome",
      wetland: "Swamp World", arctic: "Ice Moon", ocean: "Ocean World", mountain: "Highlands", volcanic: "Volcanic Belt",
    },
  },
  {
    id: "post-apocalyptic", label: "Post-Apocalyptic", blurb: "Ruined cities, scavengers, survival",
    worldName: "The Ashlands", currencyName: "Caps",
    attributeNames: { strength: "Brawn", dexterity: "Agility", intelligence: "Know-how", fortitude: "Endurance", charisma: "Sway", reflex: "Reflex" },
    biomeFamilyNames: {
      arid: "Dead Zone", grassland: "Overgrowth", woodland: "Feral Woods", tropical: "Hot Zone",
      wetland: "Toxic Bog", arctic: "Frostbite Reach", ocean: "Dead Sea", mountain: "Rubble Peaks", volcanic: "Blast Crater",
    },
  },
  {
    id: "classic-fantasy", label: "Classic Fantasy", blurb: "Kingdoms, knights, dragons -- the standard toolkit",
    worldName: "Aeloria", currencyName: "Gold",
    attributeNames: { ...STANDARD_ATTRS },
    biomeFamilyNames: { ...STANDARD_BIOMES },
  },
  {
    id: "pirates", label: "High Seas", blurb: "Pirates, cursed islands, naval battles",
    worldName: "The Drowned Reaches", currencyName: "Doubloons",
    attributeNames: { strength: "Brawn", dexterity: "Seamanship", intelligence: "Cunning", fortitude: "Sea Legs", charisma: "Bravado", reflex: "Reflex" },
    biomeFamilyNames: {
      arid: "Sunbleached Cays", grassland: "Coastal Grasses", woodland: "Jungle Isle", tropical: "Lagoon",
      wetland: "Mangrove", arctic: "Frozen Straits", ocean: "The Deep", mountain: "Crag Isle", volcanic: "Firehearth Isle",
    },
  },
];

export function findThemePreset(id: string): ThemePreset | undefined {
  return THEME_PRESETS.find((p) => p.id === id);
}

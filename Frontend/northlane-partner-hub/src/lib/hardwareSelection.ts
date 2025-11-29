export type HardwareItem = {
  hardware_id: string;
  kind: string;
  vendor: string;
  model_name: string;
  spec: Record<string, unknown>;
  url?: string | null;
  price?: string | null;
  source?: string | null;
  discovered_at?: string | null;
};

export type HardwareSelection = {
  selectedIds: string[];
  customHardware: HardwareItem[];
};

const STORAGE_KEY = 'hardware-selection';
const isBrowser = typeof window !== 'undefined';

export const emptySelection: HardwareSelection = { selectedIds: [], customHardware: [] };

export const loadHardwareSelection = (): HardwareSelection => {
  if (!isBrowser) return emptySelection;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return emptySelection;
    const parsed = JSON.parse(stored) as Partial<HardwareSelection>;
    return {
      selectedIds: Array.isArray(parsed.selectedIds) ? parsed.selectedIds : [],
      customHardware: Array.isArray(parsed.customHardware) ? parsed.customHardware : [],
    };
  } catch {
    return emptySelection;
  }
};

export const saveHardwareSelection = (selection: HardwareSelection) => {
  if (!isBrowser) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
};

export const clearHardwareSelection = () => {
  if (!isBrowser) return;
  localStorage.removeItem(STORAGE_KEY);
};

export const applySelectionToInventory = (
  inventory: HardwareItem[],
  selection?: HardwareSelection,
): HardwareItem[] => {
  const safeSelection = selection ?? emptySelection;
  const merged: HardwareItem[] = [...inventory];

  // Append custom hardware if it is not already present
  for (const custom of safeSelection.customHardware) {
    if (!merged.some((item) => item.hardware_id === custom.hardware_id)) {
      merged.push(custom);
    }
  }

  if (!safeSelection.selectedIds.length) return merged;
  const allowed = new Set(safeSelection.selectedIds);
  return merged.filter((item) => allowed.has(item.hardware_id));
};

export const hasActiveSelection = (selection?: HardwareSelection): boolean =>
  Boolean(selection && selection.selectedIds && selection.selectedIds.length > 0);

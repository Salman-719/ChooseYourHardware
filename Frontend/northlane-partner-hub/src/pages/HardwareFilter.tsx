import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Filter, Loader2, Plus, RotateCcw, Save, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  HardwareItem,
  HardwareSelection,
  applySelectionToInventory,
  clearHardwareSelection,
  hasActiveSelection,
  loadHardwareSelection,
  saveHardwareSelection,
} from '@/lib/hardwareSelection';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const HARDWARE_ENDPOINT = `${API_BASE_URL}/hardware`;
const clampSelection = (selection: HardwareSelection): HardwareSelection => ({
  ...selection,
  selectedIds: (selection.selectedIds || []).slice(0, 10),
});

type NewHardwareForm = {
  hardware_id: string;
  kind: 'gpu' | 'cpu' | 'tpu';
  vendor: string;
  model_name: string;
  vram_capacity_gb: string;
  vram_bandwidth_gbps: string;
  peak_fp32_tflops: string;
  power_consumption_w: string;
  dram_latency_ns: string;
  cache_latency_ns: string;
};

const sendCustomHardwareToBackend = async (hardware: HardwareItem) => {
  // Assumes a backend endpoint exists to accept custom hardware payloads.
  try {
    await fetch(`${HARDWARE_ENDPOINT}/custom`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(hardware),
    });
  } catch (err) {
    // Non-fatal: continue even if the call fails.
    console.warn('Failed to send custom hardware to backend:', err);
  }
};

const fetchHardwareInventory = async (): Promise<HardwareItem[]> => {
  const response = await fetch(HARDWARE_ENDPOINT, {
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Backend returned an error while fetching hardware.');
  }

  const data = await response.json();
  if (Array.isArray(data)) return data as HardwareItem[];
  if (Array.isArray(data?.items)) return data.items as HardwareItem[];
  return [];
};

const HardwareFilter = () => {
  const navigate = useNavigate();
  const [inventory, setInventory] = useState<HardwareItem[]>([]);
  const [selection, setSelection] = useState<HardwareSelection>(() => clampSelection(loadHardwareSelection()));
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [newHardware, setNewHardware] = useState<NewHardwareForm>({
    hardware_id: '',
    kind: 'gpu',
    vendor: '',
    model_name: '',
    vram_capacity_gb: '',
    vram_bandwidth_gbps: '',
    peak_fp32_tflops: '',
    power_consumption_w: '',
    dram_latency_ns: '',
    cache_latency_ns: '',
  });

  const refreshInventory = async () => {
    try {
      setLoading(true);
      const items = await fetchHardwareInventory();
      setInventory(items);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load hardware.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshInventory();
  }, []);

  const inventoryWithCustom = useMemo(
    () => applySelectionToInventory(inventory, { ...selection, selectedIds: [] }),
    [inventory, selection],
  );

  const filteredInventory = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return inventoryWithCustom;
    return inventoryWithCustom.filter((item) => {
      const text = `${item.vendor} ${item.model_name} ${item.hardware_id}`.toLowerCase();
      return text.includes(term);
    });
  }, [inventoryWithCustom, search]);

  const toggleSelection = (id: string, checked: boolean) => {
    setSelectionError(null);
    setSelection((prev) => {
      if (checked && prev.selectedIds.length >= 10) {
        setSelectionError('You can select up to 10 hardware items.');
        return prev;
      }
      const selectedIds = checked
        ? Array.from(new Set([...prev.selectedIds, id]))
        : prev.selectedIds.filter((existing) => existing !== id);
      const next = { ...prev, selectedIds };
      saveHardwareSelection(next);
      return next;
    });
  };

  const selectFiltered = () => {
    setSelectionError(null);
    setSelection((prev) => {
      const ids = filteredInventory.map((item) => item.hardware_id);
      const available = 10 - prev.selectedIds.length;
      if (available <= 0) {
        setSelectionError('You can select up to 10 hardware items.');
        return prev;
      }
      const newIds = ids.filter((id) => !prev.selectedIds.includes(id)).slice(0, available);
      const selectedIds = Array.from(new Set([...prev.selectedIds, ...newIds]));
      const next = { ...prev, selectedIds };
      saveHardwareSelection(next);
      return next;
    });
  };

  const deselectAll = () => {
    setSelection((prev) => {
      const next = { ...prev, selectedIds: [] };
      saveHardwareSelection(next);
      return next;
    });
  };

  const resetEverything = () => {
    clearHardwareSelection();
    const next: HardwareSelection = { selectedIds: [], customHardware: [] };
    setSelection(next);
  };

  const handleSaveAndReturn = () => {
    setSaving(true);
    saveHardwareSelection(selection);
    setTimeout(() => {
      setSaving(false);
      navigate('/chatbot', { state: { initialMessage: 'Use my hardware filter for the next recommendation.' } });
    }, 200);
  };

  const handleRemoveCustom = (hardwareId: string) => {
    setSelection((prev) => {
      const customHardware = prev.customHardware.filter((item) => item.hardware_id !== hardwareId);
      const selectedIds = prev.selectedIds.filter((id) => id !== hardwareId);
      const next = { ...prev, customHardware, selectedIds };
      saveHardwareSelection(next);
      return next;
    });
  };

  const handleAddCustom = () => {
    setFormError(null);
    setSelectionError(null);
    const requiredFields: Array<keyof NewHardwareForm> = [
      'hardware_id',
      'kind',
      'vendor',
      'model_name',
      'vram_capacity_gb',
      'vram_bandwidth_gbps',
      'peak_fp32_tflops',
      'power_consumption_w',
      'dram_latency_ns',
      'cache_latency_ns',
    ];

    const missing = requiredFields.filter((field) => !newHardware[field].toString().trim());
    if (missing.length) {
      setFormError('Please fill every field before adding custom hardware.');
      return;
    }
    if (selection.selectedIds.length >= 10) {
      setSelectionError('You can select up to 10 hardware items.');
      return;
    }

    const specNumbers = [
      'vram_capacity_gb',
      'vram_bandwidth_gbps',
      'peak_fp32_tflops',
      'power_consumption_w',
      'dram_latency_ns',
      'cache_latency_ns',
    ] as const;

    const spec: Record<string, number> = {};
    for (const key of specNumbers) {
      const value = parseFloat(newHardware[key]);
      if (!Number.isFinite(value) || value < 0) {
        setFormError('All spec fields must be valid non-negative numbers.');
        return;
      }
      spec[key] = value;
    }

    const customHardware: HardwareItem = {
      hardware_id: newHardware.hardware_id.trim(),
      kind: newHardware.kind.trim(),
      vendor: newHardware.vendor.trim(),
      model_name: newHardware.model_name.trim(),
      spec,
      url: null,
      price: null,
      discovered_at: null,
    };

    setSelection((prev) => {
      const existingWithoutCurrent = prev.customHardware.filter(
        (item) => item.hardware_id !== customHardware.hardware_id,
      );
      const customHardwareList = [...existingWithoutCurrent, customHardware];
      const selectedIds = Array.from(new Set([...prev.selectedIds, customHardware.hardware_id]));
      if (selectedIds.length > 10) {
        setSelectionError('You can select up to 10 hardware items.');
        return prev;
      }
      const next = { ...prev, customHardware: customHardwareList, selectedIds };
      saveHardwareSelection(next);
      return next;
    });

    void sendCustomHardwareToBackend(customHardware);
    void refreshInventory();

    setNewHardware({
      hardware_id: '',
      kind: 'gpu',
      vendor: '',
      model_name: '',
      vram_capacity_gb: '',
      vram_bandwidth_gbps: '',
      peak_fp32_tflops: '',
      power_consumption_w: '',
      dram_latency_ns: '',
      cache_latency_ns: '',
    });
  };

  const activeFilterCount = selection.selectedIds.length;
  const customCount = selection.customHardware.length;

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border/40 backdrop-blur-sm sticky top-0 z-20 bg-background/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate('/chatbot')} className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to chat
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={deselectAll} disabled={!activeFilterCount}>
              Clear selection
            </Button>
            <Button variant="outline" onClick={resetEverything} disabled={!activeFilterCount && !customCount}>
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset all
            </Button>
            <Button onClick={handleSaveAndReturn} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save & return
                </>
              )}
            </Button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-primary/10 p-3 text-primary">
            <Filter className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-3xl md:text-4xl font-bold">Choose hardware to include</h1>
            <p className="text-muted-foreground">
              Pick up to 10 hardware items for the model to consider. You can also add a new device if it is missing.
            </p>
          </div>
        </div>

        <Card className="p-6 bg-card/80 backdrop-blur-sm border-2">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <p className="text-lg font-semibold">
                {hasActiveSelection(selection)
                  ? `Filtering on ${activeFilterCount} item${activeFilterCount === 1 ? '' : 's'}`
                  : 'No hardware filter applied'}
              </p>
              <p className="text-sm text-muted-foreground">
                {customCount
                  ? `${customCount} custom item${customCount === 1 ? '' : 's'} stored locally.`
                  : 'You can create custom hardware entries below.'}
              </p>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Search vendor, model, or ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-64"
              />
              <Button variant="secondary" onClick={selectFiltered} disabled={!filteredInventory.length}>
                Select shown
              </Button>
            </div>
          </div>

          <Separator className="my-4" />

          {error ? (
            <div className="text-destructive text-sm">{error}</div>
          ) : (
            <>
              {selectionError && <div className="text-destructive text-sm mb-2">{selectionError}</div>}
              <ScrollArea className="h-[340px] pr-4">
                <div className="grid md:grid-cols-2 gap-3">
                  {loading && (
                    <div className="col-span-2 flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading hardware...
                    </div>
                  )}
                  {!loading && filteredInventory.length === 0 && (
                    <div className="col-span-2 text-sm text-muted-foreground">No hardware matches your search.</div>
                  )}
                  {filteredInventory.map((item) => {
                    const checked = selection.selectedIds.includes(item.hardware_id);
                    return (
                      <label
                        key={item.hardware_id}
                        className="flex items-start gap-3 p-3 rounded-lg border bg-background/60 hover:border-primary/40 transition"
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(isChecked) => toggleSelection(item.hardware_id, Boolean(isChecked))}
                          className="mt-1"
                        />
                        <div>
                          <div className="font-semibold leading-tight">
                            {item.vendor} {item.model_name}
                          </div>
                          <div className="text-xs text-muted-foreground">{item.hardware_id}</div>
                          <div className="text-xs text-muted-foreground mt-1">Kind: {item.kind}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </ScrollArea>
            </>
          )}
        </Card>

        <Card className="p-6 bg-card/80 backdrop-blur-sm border-2 space-y-4">
          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            <h2 className="text-xl font-semibold">Add new hardware</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Fill every field except URL, price, and discovered_at. The device will be stored locally, sent to the backend,
            and selected by default.
          </p>

          {formError && <div className="text-destructive text-sm">{formError}</div>}

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="hardware_id">Hardware ID</Label>
              <Input
                id="hardware_id"
                placeholder="amd-radeon-rx-9090-xt-gpu"
                value={newHardware.hardware_id}
                onChange={(e) => setNewHardware((prev) => ({ ...prev, hardware_id: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="kind">Kind</Label>
              <select
                id="kind"
                value={newHardware.kind}
                onChange={(e) =>
                  setNewHardware((prev) => ({ ...prev, kind: e.target.value as NewHardwareForm['kind'] }))
                }
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="gpu">GPU</option>
                <option value="cpu">CPU</option>
                <option value="tpu">TPU</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="vendor">Vendor</Label>
              <Input
                id="vendor"
                placeholder="AMD"
                value={newHardware.vendor}
                onChange={(e) => setNewHardware((prev) => ({ ...prev, vendor: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="model_name">Model name</Label>
              <Input
                id="model_name"
                placeholder="Radeon RX 9090 XT"
                value={newHardware.model_name}
                onChange={(e) => setNewHardware((prev) => ({ ...prev, model_name: e.target.value }))}
              />
            </div>
          </div>

          <Separator />

          <div className="grid md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="vram_capacity_gb">VRAM capacity (GB)</Label>
            <Input
              id="vram_capacity_gb"
              type="number"
              inputMode="decimal"
              min={0}
              value={newHardware.vram_capacity_gb}
              onChange={(e) => setNewHardware((prev) => ({ ...prev, vram_capacity_gb: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="vram_bandwidth_gbps">VRAM bandwidth (GB/s)</Label>
            <Input
              id="vram_bandwidth_gbps"
              type="number"
              inputMode="decimal"
              min={0}
              value={newHardware.vram_bandwidth_gbps}
              onChange={(e) => setNewHardware((prev) => ({ ...prev, vram_bandwidth_gbps: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="peak_fp32_tflops">Peak FP32 TFLOPS</Label>
            <Input
              id="peak_fp32_tflops"
              type="number"
              inputMode="decimal"
              min={0}
              value={newHardware.peak_fp32_tflops}
              onChange={(e) => setNewHardware((prev) => ({ ...prev, peak_fp32_tflops: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="power_consumption_w">Power consumption (W)</Label>
            <Input
              id="power_consumption_w"
              type="number"
              inputMode="decimal"
              min={0}
              value={newHardware.power_consumption_w}
              onChange={(e) => setNewHardware((prev) => ({ ...prev, power_consumption_w: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="dram_latency_ns">DRAM latency (ns)</Label>
            <Input
              id="dram_latency_ns"
              type="number"
              inputMode="decimal"
              min={0}
              value={newHardware.dram_latency_ns}
              onChange={(e) => setNewHardware((prev) => ({ ...prev, dram_latency_ns: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="cache_latency_ns">Cache latency (ns)</Label>
            <Input
              id="cache_latency_ns"
              type="number"
              inputMode="decimal"
              min={0}
              value={newHardware.cache_latency_ns}
              onChange={(e) => setNewHardware((prev) => ({ ...prev, cache_latency_ns: e.target.value }))}
            />
          </div>
          </div>

          <div className="flex items-center justify-between">
            <Button onClick={handleAddCustom} variant="secondary" className="gap-2">
              <Plus className="w-4 h-4" />
              Add custom hardware
            </Button>
            {customCount > 0 && (
              <div className="flex gap-2 items-center text-sm text-muted-foreground">
                <span>{customCount} custom item{customCount === 1 ? '' : 's'} saved.</span>
              </div>
            )}
          </div>
        </Card>

        {selection.customHardware.length > 0 && (
          <Card className="p-6 bg-card/80 backdrop-blur-sm border-2 space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold">Custom hardware</h2>
              <span className="text-sm text-muted-foreground">(stored locally)</span>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
            {selection.customHardware.map((item) => (
              <div key={item.hardware_id} className="p-3 rounded-lg border bg-background/60 space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold leading-tight">
                      {item.vendor} {item.model_name}
                    </div>
                    <div className="text-xs text-muted-foreground">{item.hardware_id}</div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handleRemoveCustom(item.hardware_id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <div className="text-xs text-muted-foreground">Kind: {item.kind}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
      </div>
    </div>
  );
};

export default HardwareFilter;

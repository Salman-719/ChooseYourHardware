import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';

type ChatMessage = { role: 'user' | 'assistant'; content: string };

type HardwareItem = {
  hardware_id: string;
  kind: string;
  vendor: string;
  model_name: string;
  spec: Record<string, unknown>;
  url?: string | null;
  price?: string | null;
  source?: string | null;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const METADATA_ENDPOINT = `${API_BASE_URL}/metadata/extract`;

const numericValue = (value: unknown): number | null => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const cleaned = value.replace(/[^0-9.]/g, '');
    const parsed = parseFloat(cleaned);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const parsePrice = (price?: string | null): number | null => (price ? numericValue(price) : null);

const getPowerDraw = (spec: Record<string, unknown>): number | null => {
  const candidates = [
    spec['power_limit_w'],
    spec['power_watts'],
    spec['power_consumption_w'],
    spec['tdp_w'],
    spec['tdp_watts'],
    spec['tdp'],
  ];
  for (const candidate of candidates) {
    const parsed = numericValue(candidate);
    if (parsed !== null) return parsed;
  }
  return null;
};

const filterGpusForPreferences = (
  items: HardwareItem[],
  budget?: number,
  powerLimit?: number,
  isEdgeDevice?: boolean,
): HardwareItem[] =>
  items
    .filter((item) => item.kind === 'gpu')
    .filter((item) => {
      const price = parsePrice(item.price);
      if (!budget || price === null) return true;
      return price <= budget;
    })
    .filter((item) => {
      const power = getPowerDraw(item.spec || {});
      if (!powerLimit || power === null) return true;
      return power <= powerLimit;
    })
    .filter((item) => {
      if (!isEdgeDevice) return true;
      const power = getPowerDraw(item.spec || {});
      if (power !== null) return power <= (powerLimit || 200);
      // If we do not know the power draw, allow it so the list is not empty.
      return true;
    });

const formatGpuSummary = (gpu: HardwareItem): string => {
  const power = getPowerDraw(gpu.spec || {});
  const spec = (gpu.spec || {}) as Record<string, unknown>;
  const vram = numericValue(spec['vram_capacity_gb']) ?? spec['vram_capacity_gb'];
  const tflops = numericValue(spec['peak_fp32_tflops']) ?? spec['peak_fp32_tflops'];
  const bandwidth = numericValue(spec['vram_bandwidth_gbps']) ?? spec['vram_bandwidth_gbps'];

  const parts = [gpu.vendor, gpu.model_name, gpu.price ? `(Price: ${gpu.price})` : null].filter(Boolean);

  const specParts = [
    vram !== null && vram !== undefined ? `${vram}GB VRAM` : null,
    tflops !== null && tflops !== undefined ? `${tflops} TFLOPS FP32` : null,
    bandwidth !== null && bandwidth !== undefined ? `${bandwidth} GB/s VRAM BW` : null,
    power ? `${power}W est. power` : null,
  ].filter(Boolean);

  const lines = [`${parts.join(' ')}`];
  if (specParts.length) {
    lines.push(`Specs: ${specParts.join(' | ')}`);
  }
  if (gpu.url) {
    lines.push(`Details: ${gpu.url}`);
  }
  return lines.join('\n');
};

const fetchGpuInventory = async (): Promise<HardwareItem[]> => {
  const response = await fetch(`${API_BASE_URL}/hardware`, {
    headers: {
      'Content-Type': 'application/json',
      ...(false ? { Authorization: `Bearer ${null}`, 'x-api-key': null } : {}),
    },
  });

  if (!response.ok) {
    throw new Error('Backend returned an error while fetching hardware.');
  }

  const data = await response.json();
  if (Array.isArray(data)) return data as HardwareItem[];
  if (Array.isArray(data?.items)) return data.items as HardwareItem[];
  return [];
};

const pickBestGpuIndex = async (_gpus: HardwareItem[]): Promise<number> => {
  // Placeholder for the backend ranking endpoint: always returns the first GPU.
  return 0;
};

const getAssistantResponse = async (
  userPrompt: string,
  _chatHistory: ChatMessage[],
  recommendation: HardwareItem | null,
  sessionId: string,
  lastQuestion: string | null,
): Promise<{ reply: string; nextQuestion: string | null }> => {
  const payload = {
    model_type: 'cnn',
    session_id: sessionId,
    user_input: userPrompt,
    last_question: lastQuestion,
    current_state: null,
    reset: false,
  };

  // Debug: log outbound payload
  // eslint-disable-next-line no-console
  console.log('Sending metadata request:', payload);

  const response = await fetch(METADATA_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to reach the metadata service: ${errorText || response.statusText}`);
  }

  const data = await response.json();
  // Debug: log inbound response
  // eslint-disable-next-line no-console
  console.log('Received metadata response:', data);
  const metadata = data?.metadata ?? {};
  const nextQuestion = data?.next_question ?? null;

  if (nextQuestion) {
    return { reply: nextQuestion, nextQuestion };
  }

  const recommendationLine = recommendation
    ? `Current recommendation: ${recommendation.vendor} ${recommendation.model_name}.`
    : 'No GPU has been selected yet.';
  const summary = `Metadata extraction result:\n${JSON.stringify(metadata, null, 2)}\n${recommendationLine}`;
  return { reply: summary, nextQuestion: null };
};
 
const Chatbot = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [finding, setFinding] = useState(false);
  const [budget, setBudget] = useState('');
  const [powerLimit, setPowerLimit] = useState('');
  const [isEdgeDevice, setIsEdgeDevice] = useState(false);
  const [recommendation, setRecommendation] = useState<HardwareItem | null>(null);
  const sessionIdRef = useRef<string>(crypto.randomUUID());
  const lastQuestionRef = useRef<string | null>(null);

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content:
          'Tell me your budget, acceptable power consumption, and whether you need something edge/portable. I will pull GPUs from the backend, filter them, and recommend the best match.',
      },
    ]);
  }, []);

  useEffect(() => {
    const initialMessage = location.state?.initialMessage;
    if (initialMessage) {
      setMessage(initialMessage);
    }
  }, [location.state]);

  const preferencesSummary = useMemo(() => {
    const budgetText = budget ? `$${budget}` : 'not specified';
    const powerText = powerLimit ? `${powerLimit}W max` : 'not specified';
    const mobilityText = isEdgeDevice ? 'Edge/portable' : 'Desktop/No';
    return `Budget: ${budgetText}, Power: ${powerText}, Mobility: ${mobilityText}`;
  }, [budget, powerLimit, isEdgeDevice]);

  const handleFindGpu = async () => {
    const budgetValue = parseFloat(budget);
    const powerValue = parseFloat(powerLimit);

    if (finding) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: preferencesSummary },
      { role: 'assistant', content: 'Checking the GPU inventory against your constraints...' },
    ]);

    setFinding(true);

    try {
      const hardwareItems = await fetchGpuInventory();
      const filtered = filterGpusForPreferences(
        hardwareItems,
        Number.isFinite(budgetValue) ? budgetValue : undefined,
        Number.isFinite(powerValue) ? powerValue : undefined,
        isEdgeDevice,
      );

      if (!filtered.length) {
        setRecommendation(null);
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'No GPUs matched those filters. Try relaxing the budget or power limits.' },
        ]);
        return;
      }

      const bestIndex = await pickBestGpuIndex(filtered);
      const chosen = filtered[Math.min(Math.max(bestIndex, 0), filtered.length - 1)];
      setRecommendation(chosen);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `I found ${filtered.length} GPUs that fit. The current best pick is:\n${formatGpuSummary(chosen)}`,
        },
      ]);
    } catch (error) {
      const description = error instanceof Error ? error.message : 'Unknown error';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `I could not reach the hardware service. ${description}`,
        },
      ]);
    } finally {
      setFinding(false);
    }
  };

  const handleSend = async () => {
    if (!message.trim()) return;
    const userMessage = message.trim();
    const chatHistory: ChatMessage[] = [...messages, { role: 'user', content: userMessage }];

    setMessages(chatHistory);
    setMessage('');
    setLoading(true);

    try {
      const assistantMessage = await getAssistantResponse(
        userMessage,
        chatHistory,
        recommendation,
        sessionIdRef.current,
        lastQuestionRef.current,
      );
      lastQuestionRef.current = assistantMessage.nextQuestion;
      setMessages((prev) => [...prev, { role: 'assistant', content: assistantMessage.reply }]);
    } catch (error) {
      const description = error instanceof Error ? error.message : 'Please try again.';
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `I could not answer that right now. ${description}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="relative z-10">
        <nav className="border-b border-border/40 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <Button variant="ghost" onClick={() => navigate('/')} className="gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back to Home
            </Button>
          </div>
        </nav>

        <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
          <h1 className="text-4xl md:text-5xl font-bold">Hardware Assistant</h1>

          <Card className="p-6 bg-card/80 backdrop-blur-sm border-2">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="budget">Budget ($)</Label>
                <Input
                  id="budget"
                  type="number"
                  inputMode="decimal"
                  placeholder="e.g. 1200"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="power">Power consumption (W)</Label>
                <Input
                  id="power"
                  type="number"
                  inputMode="decimal"
                  placeholder="e.g. 200"
                  value={powerLimit}
                  onChange={(e) => setPowerLimit(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Edge device?</Label>
                    <p className="text-sm text-muted-foreground">Prioritize low-power/mobile options</p>
                  </div>
                  <Switch checked={isEdgeDevice} onCheckedChange={setIsEdgeDevice} />
                </div>
              </div>
            </div>
            <div className="flex flex-col md:flex-row gap-3 mt-6">
              <div className="flex-1 text-sm text-muted-foreground">
                {recommendation
                  ? `Current pick: ${recommendation.vendor} ${recommendation.model_name}`
                  : 'Set your constraints and I will filter GPUs from the backend dataset.'}
              </div>
              <Button onClick={handleFindGpu} disabled={finding} className="md:w-auto w-full">
                {finding ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  'Find the best GPU'
                )}
              </Button>
            </div>
          </Card>

          <div className="space-y-4 mb-8 min-h-[400px]">
            {messages.length === 0 && (
              <Card className="p-8 bg-card/80 backdrop-blur-sm border-2">
                <p className="text-muted-foreground text-center">
                  Share your constraints to start a GPU recommendation.
                </p>
              </Card>
            )}

            {messages.map((msg, idx) => (
              <Card
                key={`${msg.role}-${idx}-${msg.content.slice(0, 10)}`}
                className={`p-6 ${
                  msg.role === 'user'
                    ? 'bg-primary/10 border-primary/20 ml-auto max-w-[80%]'
                    : 'bg-card border-2 mr-auto max-w-[80%]'
                }`}
              >
                <div className="text-sm font-medium mb-2">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                <div className="whitespace-pre-line">{msg.content}</div>
              </Card>
            ))}

            {(loading || finding) && (
              <Card className="p-6 bg-card border-2 mr-auto max-w-[80%]">
                <div className="text-sm font-medium mb-2">Assistant</div>
                <div className="text-muted-foreground">Analyzing...</div>
              </Card>
            )}
          </div>

          <Card className="p-6 bg-card/80 backdrop-blur-sm border-2 sticky bottom-6">
            <div className="space-y-4">
              <Textarea
                placeholder={
                  recommendation
                    ? 'Ask me anything about this GPU or compare with others...'
                    : 'Share constraints above first, then ask follow-up questions here...'
                }
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                className="min-h-[100px] text-base"
              />
              <Button onClick={handleSend} disabled={loading || !message.trim()} size="lg" className="w-full md:w-auto">
                {loading ? 'Sending...' : 'Send Message →'}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;

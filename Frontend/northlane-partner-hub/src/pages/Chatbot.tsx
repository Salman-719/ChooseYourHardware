import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
type ChatMessage = { role: 'user' | 'assistant'; content: string };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const METADATA_ENDPOINT = `${API_BASE_URL}/metadata/extract`;
const MATCHER_ENDPOINT = `${API_BASE_URL}/matcher/best`;
const DEVICE_DIR = import.meta.env.VITE_DEVICE_DIR || undefined;

const getAssistantResponse = async (
  userPrompt: string,
  _chatHistory: ChatMessage[],
  sessionId: string,
  lastQuestion: string | null,
  hardwareFilter: number | string[],
): Promise<{ reply: string; nextQuestion: string | null; metadata?: Record<string, unknown> }> => {
  const payload = {
    model_type: 'cnn',
    session_id: sessionId,
    user_input: userPrompt,
    last_question: lastQuestion,
    current_state: null,
    reset: false,
    hardware_filter: hardwareFilter,
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
  const isComplete = data?.is_complete ?? false;

  if (nextQuestion) {
    return { reply: nextQuestion, nextQuestion, metadata };
  }

  const summary = `Metadata extraction result:\n${JSON.stringify(metadata, null, 2)}`;
  return { reply: summary, nextQuestion: null, metadata: isComplete ? metadata : undefined };
};
 
const Chatbot = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const sessionIdRef = useRef<string>(crypto.randomUUID());
  const lastQuestionRef = useRef<string | null>(null);
  const [modelMetadata, setModelMetadata] = useState<Record<string, unknown> | null>(null);
  const [matcherResult, setMatcherResult] = useState<string | null>(null);
  const [matcherLoading, setMatcherLoading] = useState(false);
  const hardwareFilterPayload = -1;

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: 'Tell me about your model and constraints. I will analyze and match suitable hardware.',
      },
    ]);
  }, []);

  useEffect(() => {
    const initialMessage = location.state?.initialMessage;
    if (initialMessage) {
      setMessage(initialMessage);
    }
  }, [location.state]);

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
        sessionIdRef.current,
        lastQuestionRef.current,
        hardwareFilterPayload,
      );
      lastQuestionRef.current = assistantMessage.nextQuestion;
      if (assistantMessage.metadata) {
        setModelMetadata(assistantMessage.metadata);
        // Call matcher when extraction is complete
        try {
          setMatcherLoading(true);
          // eslint-disable-next-line no-console
          console.log('Calling matcher with metadata:', assistantMessage.metadata);
          const matchResponse = await fetch(MATCHER_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              model: assistantMessage.metadata,
              device_dir: DEVICE_DIR,
              hardware_filter: hardwareFilterPayload,
            }),
          });
          if (!matchResponse.ok) {
            const errText = await matchResponse.text();
            // eslint-disable-next-line no-console
            console.error('Matcher error response:', errText || matchResponse.statusText);
            setMatcherResult(`Matcher error: ${errText || matchResponse.statusText}`);
          } else {
            const matchData = await matchResponse.json();
            // eslint-disable-next-line no-console
            console.log('Matcher success response:', matchData);
            setMatcherResult(JSON.stringify(matchData, null, 2));
          }
        } catch (err) {
          const desc = err instanceof Error ? err.message : String(err);
          // eslint-disable-next-line no-console
          console.error('Matcher request failed:', desc);
          setMatcherResult(`Matcher request failed: ${desc}`);
        } finally {
          setMatcherLoading(false);
        }
      }
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

            {(loading || matcherLoading) && (
              <Card className="p-6 bg-card border-2 mr-auto max-w-[80%]">
                <div className="text-sm font-medium mb-2">Assistant</div>
                <div className="text-muted-foreground">
                  {matcherLoading ? 'Matching best device...' : 'Analyzing...'}
                </div>
              </Card>
            )}

            {matcherResult && (
              <Card className="p-6 bg-card/80 backdrop-blur-sm border-2">
                <div className="text-sm font-medium mb-2">Matcher Result</div>
                <pre className="text-xs whitespace-pre-wrap break-words">{matcherResult}</pre>
              </Card>
            )}
          </div>

          <Card className="p-6 bg-card/80 backdrop-blur-sm border-2 sticky bottom-6">
            <div className="space-y-4">
              <Textarea
                placeholder="Share constraints and questions here..."
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

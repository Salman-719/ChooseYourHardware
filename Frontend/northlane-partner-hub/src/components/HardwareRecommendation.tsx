import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Card } from './ui/card';

export const HardwareRecommendation = () => {
  const navigate = useNavigate();
  const [model, setModel] = useState('');

  const handleSubmit = () => {
    if (!model.trim()) return;
    navigate('/chatbot', { state: { initialMessage: model } });
  };

  return (
    <section className="relative z-10 max-w-4xl mx-auto px-6 py-20">
      <div className="space-y-8">
        <div>
          <h2 className="text-4xl md:text-6xl font-bold mb-6 leading-tight">
            Get your perfect
            <br />
            hardware setup.
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl">
            Tell us about your system, and our AI will recommend the optimal hardware upgrades tailored to your needs.
          </p>
        </div>

        <Card className="p-8 bg-card/80 backdrop-blur-sm border-2">
          <div className="space-y-6">
            <div>
              <label htmlFor="model" className="text-sm font-medium mb-2 block">
                Describe your current system or requirements
              </label>
              <Textarea
                id="model"
                placeholder="e.g., I have an old gaming PC from 2018 with a GTX 1060, looking to upgrade for 4K gaming..."
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="min-h-[120px] text-base"
              />
            </div>
            
            <Button 
              onClick={handleSubmit}
              disabled={!model.trim()}
              size="lg"
              className="w-full md:w-auto"
            >
              Get Recommendations →
            </Button>
          </div>
        </Card>
      </div>
    </section>
  );
};
